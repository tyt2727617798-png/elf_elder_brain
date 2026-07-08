import cv2
import time
# 图像处理函数，实际应用过程中需要自行修改
from rknnpool.rknnpool_ld import rknnPoolExecutor
from func.func_yolov8_optimize import myFunc
import numpy as np
out_win = "output_style_full_screen"
# ==========================
# Face模型
# ==========================
YUNET_MODEL = "models/face_detection_yunet_2023mar.onnx"
SFACE_MODEL = "models/face_recognition_sface_2021dec.onnx"

THRESHOLD = 0.45

data = np.load(
    "face_features.npz",
    allow_pickle=True
)

database = data["features"]
labels = data["labels"]

NAME_MAP = {
    "elder": "老人",
    "family": "家属",
    "nurse": "护工",
    "unknown": "陌生人"
}

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
cap = cv2.VideoCapture("/dev/video11")
print("camera open =", cap.isOpened())
# cap = cv2.VideoCapture(
# 0)
modelPath = "/home/elf/rknn_yolov8_demo0/model/best.rknn"
# 线程数, 增大可提高帧率
TPEs = 8

def face_recognize(frame):

    results = []

    h, w = frame.shape[:2]

    detector.setInputSize((w, h))

    _, faces = detector.detect(frame)

    if faces is None:
        return results

    for face in faces:

        x, y, fw, fh = face[:4].astype(int)

        aligned = recognizer.alignCrop(
            frame,
            face
        )

        feature = recognizer.feature(
            aligned
        )

        best_score = 0
        best_name = "unknown"

        for db_feature, label in zip(
            database,
            labels
        ):

            db_feature = db_feature.reshape(
                1,
                -1
            )

            score = recognizer.match(
                feature,
                db_feature,
                cv2.FaceRecognizerSF_FR_COSINE
            )

            if score > best_score:

                best_score = score

                best_name = str(label)

        if best_score < THRESHOLD:

            best_name = "unknown"

        show_name = NAME_MAP.get(
            best_name,
            best_name
        )

        results.append({

            "name": show_name,

            "score": float(best_score),

            "box": [
                int(x),
                int(y),
                int(fw),
                int(fh)
            ]
        })

    return results

def draw_faces(frame, results):

    for face in results:

        x, y, w, h = face["box"]

        name = face["name"]

        score = face["score"]

        if name == "陌生人":
            color = (0, 0, 255)
        else:
            color = (0, 255, 0)

        cv2.rectangle(
            frame,
            (x, y),
            (x + w, y + h),
            color,
            2
        )

        cv2.putText(
            frame,
            f"{name}",
            (x, y - 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2
        )

        cv2.putText(
            frame,
            f"{score:.2f}",
            (x, y - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2
        )

# 初始化rknn池
pool = rknnPoolExecutor(
    rknnModel=modelPath,
    TPEs=TPEs,
    func=myFunc
)

# 初始化异步所需要的帧
print("camera =", cap.isOpened())

if cap.isOpened():
    for i in range(TPEs + 1):

        ret, frame = cap.read()

        print("init", i, ret)

        if not ret:
            print("初始化读取失败")
            exit(-1)

        pool.put(frame)

last_face_time = 0
face_result = []

frames, loopTime, initTime = 0, time.time(), time.time()
while (cap.isOpened()):
    frames += 1
    ret, frame = cap.read()
    if not ret:
        break
    now = time.time()
    # 每秒识别一次人脸
    if now - last_face_time > 1:

        face_result = face_recognize(frame)

        last_face_time = now

    pool.put(frame)
    frame, flag = pool.get()
    if flag == False:
        break
    draw_faces(
            frame,
            face_result
            )
    cv2.namedWindow(out_win, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(out_win, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    frame = cv2.resize(frame, (1420, 800))
    cv2.imshow(out_win, frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    if frames % 30 == 0:
        print("30帧平均帧率:\t", 30 / (time.time() - loopTime), "帧")
        loopTime = time.time()

print("总平均帧率\t", frames / (time.time() - initTime))
# 释放cap和rknn线程池
cap.release()
cv2.destroyAllWindows()
pool.release()
