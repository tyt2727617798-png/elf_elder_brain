import os
import cv2
import sys

person_name = sys.argv[1]

SAVE_DIR = os.path.join("face_db", person_name)

os.makedirs(SAVE_DIR, exist_ok=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

YUNET_MODEL = os.path.join(
    BASE_DIR,
    "models",
    "face_detection_yunet_2023mar.onnx"
)

SAVE_DIR = os.path.join(
    BASE_DIR,
    "face_db"
)

os.makedirs(SAVE_DIR, exist_ok=True)

detector = cv2.FaceDetectorYN.create(
    YUNET_MODEL,
    "",
    (320, 320),
    score_threshold=0.8,
    nms_threshold=0.3,
    top_k=5000
)

cap = cv2.VideoCapture("/dev/video11")

if not cap.isOpened():
    print("摄像头打开失败")
    exit()

# 设置摄像头分辨率
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

save_count = len([
    f for f in os.listdir(SAVE_DIR)
    if f.endswith(".jpg")
])

print("按 s 保存人脸")
print("按 q 退出")

while True:

    ret, frame = cap.read()

    if not ret:
        print("读取摄像头失败")
        break

    frame = cv2.resize(frame, (640, 480))

    h, w = frame.shape[:2]

    detector.setInputSize((w, h))

    _, faces = detector.detect(frame)

    current_face = None

    if faces is not None:

        # 选择面积最大的人脸
        areas = faces[:, 2] * faces[:, 3]
        face = faces[areas.argmax()]

        x, y, fw, fh = face[:4].astype(int)

        score = face[-1]

        cv2.rectangle(
            frame,
            (x, y),
            (x + fw, y + fh),
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            f"{score:.2f}",
            (x, y - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )

        # 留一点边缘，避免裁切过紧
        margin = 20

        x1 = max(0, x - margin)
        y1 = max(0, y - margin)

        x2 = min(w, x + fw + margin)
        y2 = min(h, y + fh + margin)

        current_face = frame[y1:y2, x1:x2]

    cv2.putText(
        frame,
        f"Saved: {save_count}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 0, 0),
        2
    )

    cv2.imshow("Collect Face", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord('s'):

        if current_face is not None:

            filename = os.path.join(
                SAVE_DIR,
                f"chenzhengrong_{save_count:03d}.jpg"
            )

            cv2.imwrite(filename, current_face)

            save_count += 1

            print(f"保存成功：{filename}")

        else:
            print("未检测到人脸")

    elif key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
