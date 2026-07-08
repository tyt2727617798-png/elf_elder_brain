import time
import gpiod
import numpy as np
from scipy.signal import find_peaks
# =========================
# GPIO配置（RK3588）
# =========================
SDA_GPIO = 6
SCL_GPIO = 1

chip = gpiod.Chip("/dev/gpiochip3")

sda = chip.get_line(SDA_GPIO)
scl = chip.get_line(SCL_GPIO)

# 固定输出模式（关键：不要反复request）
sda.request("sda", gpiod.LINE_REQ_DIR_OUT, default_vals=[1])
scl.request("scl", gpiod.LINE_REQ_DIR_OUT, default_vals=[1])

MAX30102_ADDR = 0x57

ir_buffer = []
red_buffer = []

buf = []

last_calc_time = time.time()

FS = 100          # MAX30102配置0x6F对应100Hz
CALC_INTERVAL = 5 # 每5秒计算一次

# =========================
# 基础延时
# =========================
def delay():
    time.sleep(0.00001)  # 10us 稳定RK3588

# =========================
# GPIO控制
# =========================
def sda_high(): sda.set_value(1)
def sda_low():  sda.set_value(0)
def scl_high(): scl.set_value(1)
def scl_low():  scl.set_value(0)

# =========================
# I2C总线恢复（核心）
# =========================
def i2c_recover():
    try:
        sda.request("rec", gpiod.LINE_REQ_DIR_OUT)
        scl.request("rec", gpiod.LINE_REQ_DIR_OUT)

        sda_high()
        scl_high()
        delay()

        for _ in range(9):
            scl_high()
            delay()
            scl_low()
            delay()

        sda_low()
        scl_high()
        delay()
        sda_high()
        delay()

        # 恢复正常模式
        sda.request("sda", gpiod.LINE_REQ_DIR_OUT, default_vals=[1])
        scl.request("scl", gpiod.LINE_REQ_DIR_OUT, default_vals=[1])

    except:
        pass

# =========================
# START / STOP
# =========================
def start():
    sda_high(); scl_high(); delay()
    sda_low(); delay()
    scl_low(); delay()

def stop():
    sda_low(); delay()
    scl_high(); delay()
    sda_high(); delay()

# =========================
# ACK读取（带超时）
# =========================
def read_ack(timeout=0.002):
    start_t = time.time()

    sda.release()
    sda.request("ack", gpiod.LINE_REQ_DIR_IN)

    scl_low()
    delay()

    scl_high()

    while True:
        if sda.get_value() == 0:
            break
        if time.time() - start_t > timeout:
            scl_low()
            return False

    scl_low()

    sda.release()
    sda.request("sda", gpiod.LINE_REQ_DIR_OUT)

    return True

# =========================
# 写bit
# =========================
def write_bit(bit):
    if bit:
        sda_high()
    else:
        sda_low()

    delay()

    scl_high()
    delay()
    scl_low()

# =========================
# 写byte
# =========================
def write_byte(data):
    for i in range(8):
        write_bit(data & 0x80)
        data <<= 1

    return read_ack()

# =========================
# 读bit
# =========================
def read_bit():
    sda.release()
    sda.request("rx", gpiod.LINE_REQ_DIR_IN)

    scl_high()
    delay()

    bit = sda.get_value()

    scl_low()

    sda.release()
    sda.request("sda", gpiod.LINE_REQ_DIR_OUT)

    return bit

# =========================
# 读byte
# =========================
def read_byte(ack=True):
    val = 0

    sda.release()
    sda.request("rx", gpiod.LINE_REQ_DIR_IN)

    for _ in range(8):
        val <<= 1

        scl_high()
        delay()

        if sda.get_value():
            val |= 1

        scl_low()
        delay()

    sda.release()
    sda.request("sda", gpiod.LINE_REQ_DIR_OUT)

    # ACK/NACK
    if ack:
        sda_low()
    else:
        sda_high()

    scl_high()
    delay()
    scl_low()

    sda_high()

    return val

# =========================
# 写寄存器
# =========================
def write_reg(reg, val):
    start()

    if not write_byte(MAX30102_ADDR << 1):
        i2c_recover()
        return False

    if not write_byte(reg):
        i2c_recover()
        return False

    if not write_byte(val):
        i2c_recover()
        return False

    stop()
    return True

# =========================
# 读寄存器
# =========================
def read_reg(reg):
    start()

    if not write_byte(MAX30102_ADDR << 1):
        i2c_recover()
        return 0

    if not write_byte(reg):
        i2c_recover()
        return 0

    start()

    if not write_byte((MAX30102_ADDR << 1) | 1):
        i2c_recover()
        return 0

    val = read_byte(False)

    stop()

    return val

# =========================
# 读FIFO
# =========================
def read_fifo():
    start()

    if not write_byte(MAX30102_ADDR << 1):
        i2c_recover()

    if not write_byte(0x07):
        i2c_recover()

    stop()
    start()

    if not write_byte((MAX30102_ADDR << 1) | 1):
        i2c_recover()

    b1 = read_byte(True)
    b2 = read_byte(True)
    b3 = read_byte(True)
    b4 = read_byte(True)
    b5 = read_byte(True)
    b6 = read_byte(False)

    stop()

    red = ((b1 << 16) | (b2 << 8) | b3) & 0x3FFFF
    ir  = ((b4 << 16) | (b5 << 8) | b6) & 0x3FFFF

    return red, ir

# =========================
# 初始化MAX30102
# =========================
i2c_recover()

part = read_reg(0xFF)
print("PART ID =", hex(part), flush=True)

write_reg(0x09, 0x40)
time.sleep(1)

write_reg(0x08, 0x0F)
write_reg(0x09, 0x03)
write_reg(0x0A, 0x6F)
write_reg(0x0C, 0x24)
write_reg(0x0D, 0x24)

time.sleep(1)

# =========================
# 主循环（稳定版）
# ========================

buf = []
red_buf = []
bpm_history = []
last_valid_bpm = 75
last_valid_spo2 = 98
while True:

    red, ir = read_fifo()
    if ir < 10000:
        continue
    buf.append(ir)
    red_buf.append(red)

    if len(red_buf) > 500:
        red_buf.pop(0)

    if len(buf) > 500:
        buf.pop(0)

    if len(buf) >= 300:

        if time.time() - last_calc_time >= CALC_INTERVAL:
        
            last_calc_time = time.time()
    
            data = np.array(buf)
    
            # 去直流分量
            data = data - np.mean(data)
            data = np.convolve(
                data,
                np.ones(5)/5,
                mode='same'
            )
            signal_amp = np.max(data) - np.min(data)
    
            print(
                "\nIR_MIN =", int(np.min(buf)),
                "IR_MAX =", int(np.max(buf)),
                "DELTA =", int(signal_amp)
            )
    
            # 没检测到手指
            if signal_amp < 200:
                print("WEAK SIGNAL")
            
            try:
            
                peaks, properties = find_peaks(
                    data,
                    distance=int(FS * 0.45),       # 最大150BPM
                    prominence=signal_amp * 0.12
                )
    
                if len(peaks) < 2:
                    print("NO PULSE")
                    print(
                        "BPM = %.1f (HOLD)" %last_valid_bpm,
                        "SpO2 = %.1f%%" % last_valid_spo2
                    )
                    continue
                
                intervals = np.diff(peaks)
    
                avg_interval = np.mean(intervals)
    
                bpm = 60.0 * FS / avg_interval
                red_data = np.array(red_buf)

                red_dc = np.mean(red_data)
                ir_dc  = np.mean(data + np.mean(buf))

                red_ac = np.std(red_data)
                ir_ac  = np.std(data)

                if red_dc > 0 and ir_dc > 0 and ir_ac > 0:

                    R = (red_ac / red_dc) / (ir_ac / ir_dc)

                    spo2 = 110 - 25 * R

                    if spo2 > 100:
                        spo2 = 100

                    if spo2 < 80:
                        spo2 = 80

                    last_valid_spo2 = spo2

                else:

                    spo2 = last_valid_spo2

                bpm_history.append(bpm)

                if len(bpm_history) > 5:
                    bpm_history.pop(0)

                bpm_avg = np.mean(bpm_history)
                last_valid_bpm = bpm_avg
                print(
                    "BPM = %.1f" % bpm_avg,
                    "RAW = %.1f" % bpm,
                    "SpO2 = %.1f%%" % spo2
                )
                if bpm<40 or bpm>180:
                
                    print(
                        "INVALID BPM = %.1f" % bpm
                    )
    
            except Exception as e:
            
                print("HEART ERROR:", e)
    
