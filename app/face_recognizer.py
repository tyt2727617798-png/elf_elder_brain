import cv2
import numpy as np

# 模型与特征库路径（绝对路径）
YUNET_MODEL = "/home/elf/Desktop/people2/models/face_detection_yunet_2023mar.onnx"
SFACE_MODEL = "/home/elf/Desktop/people2/models/face_recognition_sface_2021dec.onnx"
FEATURES_PATH = "/home/elf/Desktop/people2/face_features.npz"

# 匹配阈值
THRESHOLD = 0.45

# 身份映射表
NAME_MAP = {
    "elder": "老人",
    "family": "家属",
    "nurse": "护工",
    "unknown": "陌生人"
}

class FaceRecognizer:
    def __init__(self):
        # 加载特征库
        data = np.load(FEATURES_PATH, allow_pickle=True)
        self.database = data["features"]      # shape: (N, 128)
        self.labels = data["labels"]          # 对应的标签列表

        # 创建人脸检测器
        self.detector = cv2.FaceDetectorYN.create(
            YUNET_MODEL,
            "",
            (320, 320),           # 模型输入尺寸
            score_threshold=0.8,
            nms_threshold=0.3,
            top_k=5000
        )

        # 创建人脸特征提取器
        self.recognizer = cv2.FaceRecognizerSF.create(SFACE_MODEL, "")

    def recognize(self, image_path: str) -> list:
        """
        对给定图片进行人脸识别，返回识别结果列表。
        每个元素为 dict: {"name": 显示名称, "score": 匹配分数, "box": [x,y,w,h]}
        若未检测到人脸，返回空列表。
        """
        frame = cv2.imread(image_path)
        if frame is None:
            return []

        h, w = frame.shape[:2]
        # 设置检测器输入尺寸为图片实际尺寸
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(frame)

        results = []
        if faces is None:
            return results

        for face in faces:
            x, y, fw, fh = face[:4].astype(int)
            # 对齐裁剪人脸
            aligned = self.recognizer.alignCrop(frame, face)
            # 提取特征
            feature = self.recognizer.feature(aligned)

            best_score = 0
            best_name = "unknown"

            # 与特征库比对
            for db_feat, label in zip(self.database, self.labels):
                db_feat = db_feat.reshape(1, -1)
                score = self.recognizer.match(feature, db_feat, cv2.FaceRecognizerSF_FR_COSINE)
                if score > best_score:
                    best_score = score
                    best_name = str(label)

            if best_score < THRESHOLD:
                best_name = "unknown"

            display_name = NAME_MAP.get(best_name, best_name)

            results.append({
                "name": display_name,
                "score": float(best_score),
                "box": [int(x), int(y), int(fw), int(fh)]
            })

        return results

# 测试用
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        fr = FaceRecognizer()
        res = fr.recognize(sys.argv[1])
        if res:
            for r in res:
                print(f"{r['name']} ({r['score']:.2f}) at {r['box']}")
        else:
            print("未检测到人脸")
