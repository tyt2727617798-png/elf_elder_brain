#!/usr/bin/env python3
import cv2
import time
import sys

# 配置
CAMERA_DEVICE = "/dev/video11"           # 你的摄像头设备路径
SAVE_PATH = "/tmp/camera_capture.jpg"    # 固定保存路径
CAPTURE_INTERVAL = 0.5                   # 抓帧间隔（秒），可根据需要调整

def main():
    cap = cv2.VideoCapture(CAMERA_DEVICE)
    if not cap.isOpened():
        print(f"错误：无法打开摄像头 {CAMERA_DEVICE}", file=sys.stderr)
        sys.exit(1)

    print(f"摄像头已打开，开始持续抓帧至 {SAVE_PATH}，间隔 {CAPTURE_INTERVAL} 秒...")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("警告：读取帧失败，将重试...", file=sys.stderr)
                time.sleep(1)
                continue

            # 写入固定路径，覆盖旧文件
            cv2.imwrite(SAVE_PATH, frame)
            time.sleep(CAPTURE_INTERVAL)

    except KeyboardInterrupt:
        print("\n抓帧服务已停止。")
    finally:
        cap.release()

if __name__ == "__main__":
    main()
