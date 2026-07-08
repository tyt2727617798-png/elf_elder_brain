import requests
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("外挂大脑")

@mcp.tool()
def recognize_face() -> str:
    """识别摄像头最新画面中的人脸，返回亲友身份。"""
    r = requests.post("http://127.0.0.1:8500/recognize_face",
                      json={"image_path":"/tmp/camera_capture.jpg"}, timeout=10)
    return r.json().get("name", "未识别")

@mcp.tool()
def identify_object() -> str:
    """识别摄像头最新画面中的物品，返回物品名称。"""
    r = requests.post("http://127.0.0.1:8500/identify_object",
                      json={"image_path":"/tmp/camera_capture.jpg"}, timeout=10)
    return r.json().get("item", "未识别")

@mcp.tool()
def check_fall() -> str:
    """查询老人是否跌倒。"""
    r = requests.get("http://127.0.0.1:8500/fall_status", timeout=10)
    return "摔倒" if r.json().get("fallen") else "安全"

@mcp.tool()
def query_heart() -> str:
    """查询老人心率、血氧。"""
    r = requests.get("http://127.0.0.1:8500/heart_status", timeout=10)
    d = r.json()
    return f"心率{d['bpm']:.0f}，血氧{d['spo2']:.0f}%"

@mcp.tool()
def query_safety() -> str:
    """查询老人跌倒、步数、久坐情况。"""
    r = requests.get("http://127.0.0.1:8500/safety_status", timeout=10)
    d = r.json()
    if d["fallen"]: return "检测到跌倒！"
    if d["sedentary"]: return f"安全，但久坐了。已走{d['steps']}步。"
    return f"安全，已走{d['steps']}步。"

@mcp.tool()
def speak(text: str) -> str:
    """用语音播报文字给老人。"""
    requests.post("http://127.0.0.1:8500/tts_speak", json={"text": text}, timeout=10)
    return f"已播报：{text}"

if __name__ == "__main__":
    mcp.run()
