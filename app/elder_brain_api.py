import sys
import time
import os
import random
import asyncio
import json
import threading

sys.path.append("/home/elf/demo")

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager

from rknn_inference import RknnInference
from face_recognizer import FaceRecognizer
from health_monitor import start_monitoring, heart_data, safety_data, data_lock
from tts_service import get_tts

model = None
fr = None

# 确保静态文件目录存在
STATIC_DIR = "/home/elf/app/static"
os.makedirs(STATIC_DIR, exist_ok=True)

def generate_health_advice():
    """根据最新健康数据生成专业且人性的建议文本"""
    with data_lock:
        bpm = heart_data.get("bpm", 0)
        spo2 = heart_data.get("spo2", 0)
        quality = heart_data.get("signal_quality", "NO_SIGNAL")
        steps = safety_data.get("step_count", 0)
        fallen = safety_data.get("fall_detected", False)
        sedentary = safety_data.get("sedentary_alert", False)

    advice_parts = []

    # 心率分析
    if quality == "NO_SIGNAL":
        advice_parts.append("暂时没有检测到手指，请把手指轻轻放在圆形传感器上。")
    elif bpm > 100:
        advice_parts.append(f"您的心率现在是每分钟 {bpm:.0f} 次，稍微偏快，建议您坐下来休息一会儿，深呼吸放松。")
    elif bpm < 60:
        advice_parts.append(f"您的心率现在是每分钟 {bpm:.0f} 次，比平时慢一点，如果没有不舒服就没关系，但如果感到头晕要及时告诉我哦。")
    else:
        advice_parts.append(f"心率每分钟 {bpm:.0f} 次，非常正常。")

    # 血氧分析
    if quality != "NO_SIGNAL":
        if spo2 < 95:
            advice_parts.append(f"血氧是 {spo2:.0f}%，稍微偏低，建议打开窗户通通风，或者试试腹式呼吸。")
        else:
            advice_parts.append(f"血氧 {spo2:.0f}%，状态很好。")

    # 跌倒检测
    if fallen:
        advice_parts.append("系统检测到您可能摔倒了！请不要慌张，试着慢慢活动一下手脚，我已经通知了您的家人。如果身体疼痛请不要勉强起身。")
    else:
        advice_parts.append("今天没有检测到跌倒，一切安全。")

    # 久坐提醒
    if sedentary:
        advice_parts.append("您已经坐了很久了，起来走动一下，接杯水喝吧，对身体好。")

    # 步数鼓励
    if steps < 500:
        advice_parts.append(f"今天走了 {steps} 步，还不到500步哦，天气好的时候可以去客厅溜达几圈，活动活动筋骨。")
    elif steps < 2000:
        advice_parts.append(f"走了 {steps} 步，还不错，继续加油！")
    else:
        advice_parts.append(f"太棒了，今天已经走了 {steps} 步，运动量达标啦！")

    # 结尾关怀
    endings = [
        "小雅会一直陪着您的，有需要随时叫我。",
        "记得按时吃饭，保持好心情。",
        "您今天的健康状态整体不错，继续保持！",
        "有任何不舒服就喊我，我马上帮您检查。"
    ]
    closing = random.choice(endings)

    advice_text = "爷爷，" + "。".join(advice_parts) + "。" + closing
    return advice_text


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, fr
    print("加载物品识别模型...")
    model = RknnInference("/home/elf/rknn_yolov8_demo0/model/yolov8.rknn", TPEs=3)
    print("加载人脸识别模型...")
    fr = FaceRecognizer()
    print("启动健康监测线程...")
    start_monitoring()
    get_tts()
    print("所有服务就绪。")
    yield
    if model:
        model.release()
    print("服务关闭")

app = FastAPI(title="外挂大脑", version="4.0.0", lifespan=lifespan)

# 静态文件挂载
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class ImageRequest(BaseModel):
    image_path: str

class TTSRequest(BaseModel):
    text: str

# ==================== 原有接口 ====================
@app.post("/recognize_face", tags=["认知辅助"])
def api_recognize_face(req: ImageRequest):
    if not fr:
        raise HTTPException(503, "人脸识别未就绪")
    res = fr.recognize(req.image_path)
    if res:
        return {"name": res[0]["name"], "status": "success"}
    return {"name": "未看到人", "status": "success"}

@app.post("/identify_object", tags=["生活向导"])
def api_identify_object(req: ImageRequest):
    if not model:
        raise HTTPException(503, "物品识别未就绪")
    labels = model.infer(req.image_path)
    if labels:
        return {"item": str(labels[0]), "status": "success"}
    return {"item": "未识别出物品", "status": "success"}

@app.get("/heart_status", tags=["健康监测"])
def api_heart():
    with data_lock:
        return {"bpm": heart_data["bpm"], "spo2": heart_data["spo2"],
                "quality": heart_data["signal_quality"], "status": "success"}

@app.get("/safety_status", tags=["安全守护"])
def api_safety():
    with data_lock:
        return {"fallen": safety_data["fall_detected"],
                "steps": safety_data["step_count"],
                "pitch": safety_data["pitch"], "roll": safety_data["roll"],
                "sedentary": safety_data["sedentary_alert"], "status": "success"}

@app.post("/tts_speak", tags=["语音交互"])
def api_tts(req: TTSRequest):
    try:
        get_tts().speak(req.text)
        return {"message": "播报成功", "status": "success"}
    except Exception as e:
        raise HTTPException(500, f"TTS失败: {e}")

@app.get("/fall_status", tags=["安全守护"])
def api_fall():
    with data_lock:
        return {"fallen": safety_data["fall_detected"], "status": "success"}

# ==================== 新增接口 ====================
@app.get("/health_advice", summary="健康建议", tags=["健康监测"])
def api_health_advice():
    """返回包含专业建议和人性化关怀的文本"""
    advice = generate_health_advice()
    return {"advice": advice, "status": "success"}

@app.get("/voice_status", summary="语音状态", tags=["语音交互"])
def api_voice_status():
    """读取当前语音助手状态"""
    try:
        with open("/tmp/voice_status.txt", "r", encoding="utf-8") as f:
            status = f.read().strip()
    except:
        status = "🎤 小雅在线，说“小雅”唤醒"
    return {"status": status, "status_code": "success"}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """返回仪表盘页面"""
    dashboard_file = os.path.join(STATIC_DIR, "dashboard.html")
    if os.path.exists(dashboard_file):
        with open(dashboard_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>仪表盘页面未找到</h1>", status_code=404)

# ==================== WebSocket 实时推送 ====================
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            with data_lock:
                heart = {
                    "bpm": heart_data["bpm"],
                    "spo2": heart_data["spo2"],
                    "quality": heart_data["signal_quality"]
                }
                safety = {
                    "steps": safety_data["step_count"],
                    "fallen": safety_data["fall_detected"],
                    "sedentary": safety_data["sedentary_alert"],
                    "pitch": safety_data["pitch"],
                    "roll": safety_data["roll"]
                }
                advice = generate_health_advice()
            try:
                with open("/tmp/voice_status.txt", "r", encoding="utf-8") as f:
                    voice_status = f.read().strip()
            except:
                voice_status = "🎤 小雅在线，说“小雅”唤醒"
            data = {
                "heart": heart,
                "safety": safety,
                "advice": advice,
                "voice_status": voice_status,
                "timestamp": time.time()
            }
            await websocket.send_json(data)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("WebSocket 连接断开")

@app.get("/")
def root():
    return {"message": "外挂大脑全功能运行中", "version": "4.0.0"}
    
