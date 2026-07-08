import time
import math
import threading
import numpy as np
from scipy.signal import find_peaks
import sys
sys.path.insert(0, "/home/elf/Desktop/project/modules")

# 使用安全的 i2c_base 模块（不会在导入时占用 GPIO）
from i2c_base import init_gpio, init_max30102, read_fifo, write_reg
import mpu6050

# 新增：导入华为云上传模块
from huaweiyun import get_huawei_client

# 共享数据
heart_data = {"bpm": 0.0, "spo2": 0.0, "signal_quality": "NO_SIGNAL", "timestamp": 0}
safety_data = {"step_count": 0, "fall_detected": False, "pitch": 0.0, "roll": 0.0,
               "magnitude": 0.0, "sedentary_alert": False, "timestamp": 0}
data_lock = threading.Lock()

def heart_rate_loop():
    """心率采集线程"""
    init_max30102()
    buf, red_buf = [], []
    last_valid_bpm, last_valid_spo2 = 75, 98
    last_calc = time.time()
    while True:
        try:
            red, ir = read_fifo()
            if ir < 10000:
                time.sleep(0.01)
                continue
            buf.append(ir); red_buf.append(red)
            if len(buf) > 500: buf.pop(0)
            if len(red_buf) > 500: red_buf.pop(0)

            if len(buf) >= 300 and time.time() - last_calc >= 5:
                last_calc = time.time()
                data = np.array(buf) - np.mean(buf)
                data = np.convolve(data, np.ones(5)/5, mode='same')
                amp = np.max(data) - np.min(data)
                if amp < 50:
                    with data_lock:
                        heart_data.update(bpm=last_valid_bpm, spo2=last_valid_spo2,
                                          signal_quality="WEAK", timestamp=time.time())
                    continue
                peaks, _ = find_peaks(data, distance=int(100*0.45), prominence=amp*0.12)
                if len(peaks) < 2:
                    with data_lock:
                        heart_data.update(bpm=last_valid_bpm, spo2=last_valid_spo2,
                                          signal_quality="WEAK", timestamp=time.time())
                    continue
                intervals = np.diff(peaks)
                bpm = 60.0 * 100 / np.mean(intervals)
                red_arr = np.array(red_buf)
                red_dc, ir_dc = np.mean(red_arr), np.mean(data + np.mean(buf))
                red_ac, ir_ac = np.std(red_arr), np.std(data)
                spo2 = last_valid_spo2
                if red_dc > 0 and ir_dc > 0 and ir_ac > 0:
                    R = (red_ac/red_dc) / (ir_ac/ir_dc)
                    spo2 = 110 - 25*R
                    spo2 = max(80, min(100, spo2))
                if 40 <= bpm <= 180:
                    last_valid_bpm = bpm
                last_valid_spo2 = spo2
                with data_lock:
                    heart_data.update(bpm=last_valid_bpm, spo2=spo2,
                                      signal_quality="GOOD", timestamp=time.time())
        except Exception as e:
            print(f"心率错误: {e}")
            time.sleep(0.1)

def safety_loop():
    """姿态/安全采集线程"""
    while not mpu6050.init_mpu6050():
        print("MPU6050 未找到，10秒后重试...")
        time.sleep(10)
    step_count, last_mag, last_step_time = 0, 0, 0
    impact_time, still_start, last_step = 0, time.time(), 0
    while True:
        try:
            ax = mpu6050.read16(0x3B)
            ay = mpu6050.read16(0x3D)
            az = mpu6050.read16(0x3F)
            mag = math.sqrt(ax*ax + ay*ay + az*az)
            pitch = math.atan2(ax, math.sqrt(ay*ay + az*az)) * 57.3
            roll = math.atan2(ay, math.sqrt(ax*ax + az*az)) * 57.3

            if mag > 18000 and last_mag <= 18000:
                if time.time() - last_step_time > 0.3:
                    step_count += 1
                    last_step_time = time.time()
            last_mag = mag

            fall = False
            if mag > 30000:
                impact_time = time.time()
            if impact_time and time.time() - impact_time < 3:
                if abs(pitch) > 60 or abs(roll) > 60:
                    fall = True
                    impact_time = 0

            sedentary = False
            if step_count != last_step:
                last_step = step_count
                still_start = time.time()
            elif time.time() - still_start > 30:
                sedentary = True
                still_start = time.time()

            with data_lock:
                safety_data.update(step_count=step_count, fall_detected=fall,
                                   pitch=round(pitch,1), roll=round(roll,1),
                                   magnitude=round(mag,0), sedentary_alert=sedentary,
                                   timestamp=time.time())
            time.sleep(0.05)
        except Exception as e:
            print(f"姿态错误: {e}")
            time.sleep(0.1)

def upload_loop():
    """华为云定时上传线程"""
    print("华为云上传线程已启动，正在连接...")
    hw_client = get_huawei_client()
    # 等待连接建立
    time.sleep(3)
    if not hw_client._connected:
        print("华为云连接失败，上传线程退出。请检查网络和凭证。")
        return
    print("华为云连接成功，开始定时上传")
    while True:
        time.sleep(5)
        try:
            with data_lock:
                bpm = heart_data.get("bpm", 0)
                spo2 = heart_data.get("spo2", 0)
                steps = safety_data.get("step_count", 0)
                fallen = 1 if safety_data.get("fall_detected") else 0
                person = "unknown"
            print(f"准备上传: 心率={int(bpm)}, 血氧={int(spo2)}, 跌倒={fallen}, 步数={steps}")
            hw_client.upload(
                temp=25,
                heart_rate=int(bpm),
                spo2=int(spo2),
                fall=fallen,
                person=person,
                step=steps
            )
        except Exception as e:
            print(f"华为云上传异常: {e}")

def start_monitoring():
    threading.Thread(target=heart_rate_loop, daemon=True).start()
    threading.Thread(target=safety_loop, daemon=True).start()
    threading.Thread(target=upload_loop, daemon=True).start()   # 新增上传线程
    print("健康监测线程已启动")
