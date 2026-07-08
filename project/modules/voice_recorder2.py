import wave
import numpy as np
import pyaudio
import webrtcvad
import audioop
from collections import deque
import gc
import ctypes
import time


class VoiceRecorder:
    WAITING = 0
    RECORDING = 1

    def __init__(
        self,
        device_index=1,
        rate=44100,
        target_rate=16000,
        channels=2,
        frame_ms=30,
        vad_level=2,
        start_frames=10,
        stop_frames=20,
        max_record_sec=10,
        energy_threshold=9000,   # 固定阈值，不再自动校准
    ):
        self.device_index = device_index
        self.rate = rate
        self.target_rate = target_rate
        self.channels = channels
        self.frame_ms = frame_ms

        self.chunk = int(rate * frame_ms / 1000)

        self.state = self.WAITING
        self.frames = []
        self.speech_frames = 0
        self.silence_frames = 0

        self.start_frames = start_frames
        self.stop_frames = stop_frames
        self.max_record_sec = max_record_sec
        self.record_start_time = None

        self.ring = deque(maxlen=10)

        self.vad = webrtcvad.Vad(vad_level)

        self.energy_threshold = energy_threshold
        self.cooldown_until = 0   # 冷却截止时间戳

        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=self.chunk,
        )

        # 仅输出信息，不做动态校准
        print(f"能量阈值已固定为: {self.energy_threshold}")
        print("VoiceRecorder init OK")

    def _get_mono_right(self, data):
        audio = np.frombuffer(data, dtype=np.int16).reshape(-1, 2)
        right = audio[:, 1]
        return right.tobytes()

    def _to_16k(self, pcm_bytes):
        return audioop.ratecv(pcm_bytes, 2, 1, self.rate, self.target_rate, None)[0]

    def _vad(self, pcm_16k):
        return self.vad.is_speech(pcm_16k, self.target_rate)

    def read(self):
        # 冷却期内：清空计数，直接返回
        if time.time() < self.cooldown_until:
            if self.state == self.WAITING:
                self.speech_frames = 0
            return None

        data = self.stream.read(self.chunk, exception_on_overflow=False)
        mono = self._get_mono_right(data)
        self.ring.append(mono)

        rms = np.sqrt(np.mean(np.frombuffer(mono, dtype=np.int16).astype(np.float32)**2))

        if rms < self.energy_threshold:
            speech = False
        else:
            pcm16k = self._to_16k(mono)
            speech = self._vad(pcm16k)

        # ========== WAITING ==========
        if self.state == self.WAITING:
            self.speech_frames = self.speech_frames + 1 if speech else 0
            print(f"\rWAIT RMS={rms:.0f} speech={speech} buf={self.speech_frames}", end="")
            if self.speech_frames >= self.start_frames:
                print("\n开始录音")
                self.state = self.RECORDING
                self.frames = list(self.ring)
                self.silence_frames = 0
                self.record_start_time = time.time()
            return None

        # ========== RECORDING ==========
        if self.record_start_time and (time.time() - self.record_start_time) > self.max_record_sec:
            print("\n录音超时，丢弃")
            self.state = self.WAITING
            self.frames = []
            self.speech_frames = 0
            self.silence_frames = 0
            self.record_start_time = None
            self.cooldown_until = time.time() + 2   # 冷却2秒
            return None

        self.frames.append(mono)
        if speech:
            self.silence_frames = 0
        else:
            self.silence_frames += 1
        print(f"\rREC RMS={rms:.0f} speech={speech} silence={self.silence_frames}", end="")

        if self.silence_frames >= self.stop_frames:
            for _ in range(5):
                d = self.stream.read(self.chunk, exception_on_overflow=False)
                self.frames.append(self._get_mono_right(d))
            path = "temp.wav"
            self.save(path)
            self.state = self.WAITING
            self.frames = []
            self.speech_frames = 0
            self.silence_frames = 0
            self.record_start_time = None
            self.cooldown_until = time.time() + 1   # 正常录音后冷却1秒
            print("\n录音结束")
            return path

        return None

    def save(self, filename):
        wf = wave.open(filename, "wb")
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(self.rate)
        wf.writeframes(audioop.ratecv(b"".join(self.frames), 2, 1, self.rate, self.rate, None)[0])
        wf.close()
        self.frames.clear()
        gc.collect()
        ctypes.CDLL("libc.so.6").malloc_trim(0)

    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
