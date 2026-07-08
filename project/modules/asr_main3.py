import os
import subprocess
import re
import gc
import psutil
import ctypes
import time
from funasr import AutoModel
from tts_test import tts_play
from voice_recorder2 import VoiceRecorder

process = psutil.Process(os.getpid())

REPLY_FILE = "/tmp/reply.txt"
STATUS_FILE = "/tmp/voice_status.txt"


def set_voice_status(status):
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            f.write(status)
    except:
        pass


def release_memory():
    gc.collect()
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except:
        pass


print("加载模型中...")
model = AutoModel(
    model="paraformer-zh",
    disable_update=True
)
print("模型加载完成")

print("初始化录音器...")
recorder = VoiceRecorder(
    device_index=1,
    vad_level=0,
    start_frames=3      # 只需要连续 3 帧语音就触发录音
)
print("录音器初始化完成")
print(">>>>>>>>>>>> MAIN START <<<<<<<<<")

set_voice_status("🎤 小雅在线，说“小雅”唤醒")

while True:
    print("\n====================")
    print("等待唤醒...")

    if os.path.exists(REPLY_FILE):
        os.remove(REPLY_FILE)

    print("等待说出唤醒词...")
    wav_path = None
    while wav_path is None:
        wav_path = recorder.read()

    print("识别唤醒词...")
    res = model.inference(wav_path)

    if len(res) == 0:
        print("没有识别到内容")
        release_memory()
        continue

    text = res[0]["text"].replace(" ", "")
    del res
    gc.collect()
    print("识别：", text)

    if "小雅" not in text:
        release_memory()
        continue

    print("已唤醒")
    set_voice_status("👂 正在听您说话...")
    tts_play("你好，我在")
    print("等待用户提问...")

    wav_path = None
    while wav_path is None:
        wav_path = recorder.read()

    print("识别问题...")
    res = model.inference(wav_path)

    if len(res) == 0:
        print("没有识别到问题")
        set_voice_status("🎤 小雅在线，说“小雅”唤醒")
        release_memory()
        continue

    question = res[0]["text"].replace(" ", "")
    del res
    gc.collect()
    print("问题：", question)

    if question == "":
        set_voice_status("🎤 小雅在线，说“小雅”唤醒")
        release_memory()
        continue

    print("问题：", question)
    try:
        os.remove(wav_path)
    except:
        pass

    set_voice_status("🤔 正在思考...")
    subprocess.run(
        [
            "python3",
            "openclaw_client.py",
            question
        ]
    )

    if not os.path.exists(REPLY_FILE):
        set_voice_status("🎤 小雅在线，说“小雅”唤醒")
        release_memory()
        continue

    with open(REPLY_FILE, "r", encoding="utf-8") as f:
        reply = f.read().strip()

    print("reply长度：", len(reply))
    print("reply内容：", repr(reply))
    print("OpenClaw：", reply)

    reply = re.sub(r"\*\*", "", reply)
    reply = re.sub(r"`", "", reply)
    reply = re.sub(r"\(.*?\)", "", reply)
    reply = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9，。！？；：、,.!? ]", "", reply)

    if reply != "":
        print("tts start")
        set_voice_status("🔊 正在回复...")
        tts_play(reply)
    else:
        print("tts failed")

    set_voice_status("🎤 小雅在线，说“小雅”唤醒")
    release_memory()
