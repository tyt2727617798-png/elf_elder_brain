import cv2
import numpy as np
from rknnpool.rknnpool_ld import rknnPoolExecutor
from func.func_yolov8_optimize import myFunc

class RknnInference:
    def __init__(self, model_path, TPEs=3):
        print(f"正在加载模型: {model_path}")
        self.pool = rknnPoolExecutor(
            rknnModel=model_path,
            TPEs=TPEs,
            func=myFunc
        )
        dummy = np.zeros((480, 640, 3), dtype=np.uint8)
        for _ in range(TPEs + 1):
            self.pool.put(dummy)
        for _ in range(TPEs + 1):
            self.pool.get()
        print("模型加载完毕。")

    def infer(self, image_path):
        frame = cv2.imread(image_path)
        if frame is None:
            return []
        self.pool.put(frame)
        out = self.pool.get()
        # out: ((img, labels), flag)
        if isinstance(out, tuple) and len(out) == 2:
            first, flag = out
            if isinstance(first, tuple) and len(first) == 2:
                img, labels = first
                if flag and labels:
                    return list(labels)
        return []

    def release(self):
        self.pool.release()
