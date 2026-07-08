import os,subprocess,gc,json,time,serial
from funasr import AutoModel

model = AutoModel(
    model="paraformer-zh",
    disable_update=True
)

def tts_play(text):

    ser = serial.Serial(
        "/dev/ttyS9",
        115200,
        timeout=1
    )

    time.sleep(0.2)

    text_data = text.encode("gbk")

    length = len(text_data) + 2

    frame = bytearray()

    frame.append(0xFD)

    frame.append((length >> 8) & 0xFF)
    frame.append(length & 0xFF)

    frame.append(0x01)

    frame.append(0x00)

    frame.extend(text_data)

    ser.write(frame)

    print("发送成功:", text)

    time.sleep(0.5)

    ser.close()


while True:

    print("开始录音...")

    os.system(
        "arecord -D hw:rockchipnau8822,0 "
        "-f cd "
        "-d 2 "
        "-t wav test.wav"
    )

    print("识别中...")

    res = model.inference("test.wav")

    text = res[0]["text"].replace(" ","")
    print("识别结果：", text)
    if "小雅" in text:
        print("已唤醒,请说")
        os.system(
        "arecord -D hw:rockchipnau8822,0 "
        "-f cd "
        "-d 3 "
        "-t wav test.wav"
        )
        question_res = model.inference("test.wav")
        question = question_res[0]["text"].replace(" ","")
        del question_res
        gc.collect()
        print("问题:",question)
        print("调用OpenClaw...")

        result = subprocess.run(
            [
                "python3",
                "openclaw_client.py",
                question
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True
            )

        reply = result.stdout.strip()

        print("OpenClaw回复:", reply)

        tts_play(reply)
        print("OpenClaw回复:")
        print(reply)
        tts_play(reply)
