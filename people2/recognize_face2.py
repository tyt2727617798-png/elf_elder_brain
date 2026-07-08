import os
import cv2
import numpy as np

YUNET_MODEL = "models/face_detection_yunet_2023mar.onnx"
SFACE_MODEL = "models/face_recognition_sface_2021dec.onnx"

ROOT_DIR = "face_db"

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
labels = []

for person_name in os.listdir(ROOT_DIR):

    person_dir = os.path.join(ROOT_DIR, person_name)

    if not os.path.isdir(person_dir):
        continue

    for filename in os.listdir(person_dir):

        path = os.path.join(person_dir, filename)

        img = cv2.imread(path)

        if img is None:
            continue

        h, w = img.shape[:2]

        detector.setInputSize((w, h))

        _, faces = detector.detect(img)

        if faces is None:
            continue

        face = faces[0]

        aligned = recognizer.alignCrop(img, face)

        feature = recognizer.feature(aligned)

        features.append(feature.flatten())
        labels.append(person_name)

        print(f"{person_name}: {filename} 注册成功")

features = np.array(features, dtype=np.float32)
labels = np.array(labels)

np.savez(
    "face_features.npz",
    features=features,
    labels=labels
)

print("保存完成")
