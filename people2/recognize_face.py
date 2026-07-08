import cv2
import numpy as np
import time

# ==========================
# 模型路径
# ==========================
YUNET_MODEL = "models/face_detection_yunet_2023mar.onnx"
SFACE_MODEL = "models/face_recognition_sface_2021dec.onnx"

# ==========================
# 身份数据库
# ==========================
data = np.load("face_features.npz", allow_pickle=True)

database = data["features"]
labels = data["labels"]

print("加载身份库成功")
print("特征数量:", len(database))

# ==========================
# 身份名称映射
# ==========================
NAME_MAP = {
    "elder": "老人",
    "family": "家属",
    "nurse": "护工",
    "unknown": "陌生人"
}

# ==========================
# 初始化 YuNet
# ==========================
detector = cv2.FaceDetectorYN.create(
    YUNET_MODEL,
    "",
    (320, 320),
    score_threshold=0.8,
    nms_threshold=0.3,
    top_k=5000
)

# ==========================
# 初始化 SFace
# ==========================
recognizer = cv2.FaceRecognizerSF.create(
    SFACE_MODEL,
    ""
)

# ==========================
# 摄像头
# ==========================
#cap = cv2.VideoCapture("/dev/video11")

if not cap.isOpened():
    print("摄像头打开失败")
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

# ==========================
# 参数
# ==========================
THRESHOLD = 0.45

prev_time = time.time()

# ==========================
# 主循环
# ==========================
while True:

    ret, frame = cap.read()

    if not ret:
        print("读取失败")
        break

    # 提高速度
    frame = cv2.resize(frame, (640, 480))

    h, w = frame.shape[:2]

    detector.setInputSize((w, h))

    _, faces = detector.detect(frame)

    if faces is not None:

        for face in faces:

            x, y, fw, fh = face[:4].astype(int)

            # ==========================
            # 人脸对齐
            # ==========================
            aligned = recognizer.alignCrop(frame, face)

            # ==========================
            # 提取特征
            # ==========================
            feature = recognizer.feature(aligned)

            best_score = 0
            best_name = "unknown"

            # ==========================
            # 遍历数据库
            # ==========================
            for db_feature, label in zip(database, labels):

                db_feature = db_feature.reshape(1, -1)

                score = recognizer.match(
                    feature,
                    db_feature,
                    cv2.FaceRecognizerSF_FR_COSINE
                )

                if score > best_score:
                    best_score = score
                    best_name = str(label)

            # ==========================
            # 阈值判断
            # ==========================
            if best_score < THRESHOLD:
                best_name = "unknown"

            show_name = NAME_MAP.get(
                best_name,
                best_name
            )

            # ==========================
            # 颜色
            # ==========================
            if best_name == "unknown":
                color = (0, 0, 255)
            else:
                color = (0, 255, 0)

            # ==========================
            # 画框
            # ==========================
            cv2.rectangle(
                frame,
                (x, y),
                (x + fw, y + fh),
                color,
                2
            )

            # ==========================
            # 显示身份
            # ==========================
            cv2.putText(
                frame,
                f"{show_name}",
                (x, y - 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                color,
                2
            )

            # ==========================
            # 显示相似度
            # ==========================
            cv2.putText(
                frame,
                f"{best_score:.2f}",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2
            )

            # ==========================
            # 关键点
            # ==========================
            for i in range(4, 14, 2):

                px = int(face[i])
                py = int(face[i + 1])

                cv2.circle(
                    frame,
                    (px, py),
                    2,
                    (255, 0, 0),
                    -1
                )

    # ==========================
    # FPS
    # ==========================
    now = time.time()

    fps = 1.0 / (now - prev_time)

    prev_time = now

    cv2.putText(
        frame,
        f"FPS: {fps:.1f}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 0, 0),
        2
    )

    cv2.imshow(
        "Face Recognition",
        frame
    )

    key = cv2.waitKey(1) & 0xFF

    if key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
