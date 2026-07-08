import re
import serial
import time

def tts_play(text):

    text = re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9，。！？；：、,.!? ]", "", text)

    ser = serial.Serial(
        "/dev/ttyS9",
        115200,
        timeout=1
    )

    time.sleep(0.2)

    text_data = text.encode("gbk", errors="ignore")

    length = len(text_data) + 2

    frame = bytearray()

    frame.append(0xFD)

    frame.append((length >> 8) & 0xFF)
    frame.append(length & 0xFF)

    frame.append(0x01)
    frame.append(0x00)

    frame.extend(text_data)

    ser.write(frame)

    print("发送成功：", text)

    time.sleep(0.5)

    ser.close()

#tts_play("星期六")
