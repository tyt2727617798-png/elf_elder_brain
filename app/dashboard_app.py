import PySimpleGUI as sg
import requests
import time
import threading
import os

API_BASE = "http://127.0.0.1:8500"
STATUS_FILE = "/tmp/voice_status.txt"

latest_data = {
    "bpm": 0,
    "spo2": 0,
    "steps": 0,
    "fallen": False,
    "sedentary": False,
    "advice": ""
}

def fetch_data():
    """后台线程，定时拉取API数据"""
    global latest_data
    while True:
        try:
            hr = requests.get(f"{API_BASE}/heart_status", timeout=3).json()
            sf = requests.get(f"{API_BASE}/safety_status", timeout=3).json()
            try:
                adv = requests.get(f"{API_BASE}/health_advice", timeout=3).json()
                advice = adv.get("advice", "")
            except:
                advice = ""
            latest_data.update(
                bpm=hr.get("bpm", 0),
                spo2=hr.get("spo2", 0),
                steps=sf.get("steps", 0),
                fallen=sf.get("fallen", False),
                sedentary=sf.get("sedentary", False),
                advice=advice
            )
        except Exception as e:
            print(f"数据拉取失败: {e}")
        time.sleep(1)

threading.Thread(target=fetch_data, daemon=True).start()

def read_voice_status():
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except:
        return "🎤 小雅在线，说“小雅”唤醒"

# ===== GUI =====
sg.theme('DarkBlack')
sg.set_options(font=("Microsoft YaHei", 16))

def card(label, value_key, unit):
    return sg.Frame(label, [[
        sg.Text("0", key=value_key, font=("Microsoft YaHei", 48, "bold"), text_color="#00d4aa"),
        sg.Text(unit, font=("Microsoft YaHei", 18), text_color="#a0b9ce")
    ]], element_justification='center', size=(250, 150), relief=sg.RELIEF_GROOVE)

layout = [
    [sg.Text("小雅 · 健康守护", font=("Microsoft YaHei", 36, "bold"), text_color="#00d4aa", justification='center', expand_x=True)],
    [sg.HorizontalSeparator()],
    [
        card("❤️ 心率", "-BPM-", "BPM"),
        card("🩸 血氧", "-SPO2-", "%"),
        card("👣 今日步数", "-STEPS-", "步")
    ],
    [
        sg.Frame("⚠️ 安全状态", [[
            sg.Text("跌倒: 安全", key="-FALL-", font=("Microsoft YaHei", 24), text_color="#00d4aa"),
            sg.Text("   "),
            sg.Text("久坐: 正常", key="-SED-", font=("Microsoft YaHei", 24), text_color="#00d4aa")
        ]], element_justification='center', expand_x=True, relief=sg.RELIEF_GROOVE)
    ],
    [
        sg.Frame("💬 健康建议", [[
            sg.Text("", key="-ADVICE-", font=("Microsoft YaHei", 18), text_color="#e0e0e0", size=(60, 3), justification='center')
        ]], expand_x=True, relief=sg.RELIEF_GROOVE)
    ],
    [sg.Text("", key="-VOICE-", font=("Microsoft YaHei", 20), text_color="#ffaa00", justification='center', expand_x=True)],
    [sg.Button("退出", size=(10, 1), button_color=('white', '#333333'))]
]

window = sg.Window("小雅 · 老人陪护仪表盘", layout, size=(1024, 600), element_justification='center', finalize=True, keep_on_top=True)

while True:
    event, values = window.read(timeout=500)
    if event in (sg.WIN_CLOSED, "退出"):
        break

    window["-BPM-"].update(f"{latest_data['bpm']:.0f}")
    window["-SPO2-"].update(f"{latest_data['spo2']:.0f}")
    window["-STEPS-"].update(f"{latest_data['steps']}")

    if latest_data["fallen"]:
        window["-FALL-"].update("跌倒: ⚠️ 是", text_color="#ff4d4d")
    else:
        window["-FALL-"].update("跌倒: 安全", text_color="#00d4aa")

    if latest_data["sedentary"]:
        window["-SED-"].update("久坐: ⚠️ 请活动", text_color="#ff4d4d")
    else:
        window["-SED-"].update("久坐: 正常", text_color="#00d4aa")

    window["-ADVICE-"].update(latest_data["advice"])
    window["-VOICE-"].update(read_voice_status())

window.close()

