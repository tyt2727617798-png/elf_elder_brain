import os
import cv2
import numpy as np

YUNET_MODEL = "models/face_detection_yunet_2023mar.onnx"
SFACE_MODEL = "models/face_recognition_sface_2021dec.onnx"

FACE_DIR = "face_db"
OUTPUT_FILE = "elder_features.npy"

detector = cv2.FaceDetectorYN.create(
    YUNET_MODEL,
    "",
    (320, 320),
    score_threshold=0.8,
    nms_threshold=0.3,
    top_k=5000
)

recognizer = cv2.FaceRecognizerSF.create(
    SFACE_MODEL,
    ""
)

features = []

for filename in os.listdir(FACE_DIR):

    path = os.path.join(FACE_DIR, filename)

    img = cv2.imread(path)

    if img is None:
        continue

    h, w = img.shape[:2]

    detector.setInputSize((w, h))

    _, faces = detector.detect(img)

    if faces is None:
        print(f"{filename}: 未检测到人脸")
        continue

    face = faces[0]

    aligned = recognizer.alignCrop(img, face)

    feature = recognizer.feature(aligned)

    features.append(feature)

    print(f"{filename}: 注册成功")

features = np.array(features,axis=0)

np.save("elder_features.npy", features)

print(f"\n保存完成，共 {len(features)} 条特征")
