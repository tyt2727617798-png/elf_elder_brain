import serial
import time

class TTSService:
    def __init__(self, port="/dev/ttyS9", baudrate=115200):
        self.ser = serial.Serial(port, baudrate, timeout=1)
        time.sleep(1)

    def speak(self, text: str):
        data = text.encode('gbk')
        length = len(data) + 2
        frame = bytearray([0xFD, (length >> 8) & 0xFF, length & 0xFF, 0x01, 0x00])
        frame.extend(data)
        self.ser.write(frame)
        print(f"TTS播报: {text}")

    def close(self):
        self.ser.close()

_tts = None
def get_tts():
    global _tts
    if _tts is None:
        _tts = TTSService()
    return _tts
