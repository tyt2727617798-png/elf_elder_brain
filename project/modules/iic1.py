import time
import gpiod
import numpy as np
from scipy.signal import find_peaks

# =========================
# GPIO 配置（RK3588）
# =========================
SDA_GPIO = 1
SCL_GPIO = 6
MAX30102_ADDR = 0x57

# 关键：增大延时至 100µs，提高稳定性
I2C_DELAY = 0.0001          # 100µs

chip = gpiod.Chip("/dev/gpiochip3")
sda = chip.get_line(SDA_GPIO)
scl = chip.get_line(SCL_GPIO)

# 初始化方向（输出高电平）
sda.request("sda_out", gpiod.LINE_REQ_DIR_OUT, default_vals=[1])
scl.request("scl_out", gpiod.LINE_REQ_DIR_OUT, default_vals=[1])

# =========================
# 全局变量（与原逻辑相同）
# =========================
ir_buffer = []
red_buffer = []
buf = []
last_calc_time = time.time()
FS = 100
CALC_INTERVAL = 5
bpm_history = []
last_valid_bpm = 75
last_valid_spo2 = 98

# =========================
# 基础 GPIO 控制
# =========================
def sda_high(): sda.set_value(1)
def sda_low():  sda.set_value(0)
def scl_high(): scl.set_value(1)
def scl_low():  scl.set_value(0)

def delay():
    time.sleep(I2C_DELAY)

def set_sda_input():
    sda.request("sda_in", gpiod.LINE_REQ_DIR_IN)

def set_sda_output():
    sda.request("sda_out", gpiod.LINE_REQ_DIR_OUT, default_vals=[1])

def set_scl_output():
    scl.request("scl_out", gpiod.LINE_REQ_DIR_OUT, default_vals=[1])

# =========================
# I2C 总线恢复
# =========================
def i2c_recover():
    try:
        set_sda_output()
        set_scl_output()
        sda_high()
        scl_high()
        delay()
        for _ in range(9):
            scl_high()
            delay()
            scl_low()
            delay()
        sda_low()
        delay()
        scl_high()
        delay()
        sda_high()
        delay()
        set_sda_output()
    except:
        pass

# =========================
# START / STOP
# =========================
def start():
    sda_high()
    scl_high()
    delay()
    sda_low()
    delay()
    scl_low()
    delay()

def stop():
    sda_low()
    delay()
    scl_high()
    delay()
    sda_high()
    delay()

# =========================
# 读 ACK（带超时）
# =========================
def read_ack(timeout=0.005):
    set_sda_input()
    scl_low()
    delay()
    scl_high()
    delay()
    start_t = time.time()
    while sda.get_value() == 1:
        if time.time() - start_t > timeout:
            scl_low()
            set_sda_output()
            return False
    scl_low()
    set_sda_output()
    return True

# =========================
# 写 bit
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
    delay()

# =========================
# 写 byte（带重试）
# =========================
def write_byte(data, retry=3):
    for attempt in range(retry):
        start()
        if write_byte_raw(data):
            stop()
            return True
        i2c_recover()
    return False

def write_byte_raw(data):
    for i in range(8):
        write_bit(data & 0x80)
        data <<= 1
    return read_ack()

# =========================
# 读 bit
# =========================
def read_bit():
    set_sda_input()
    scl_high()
    delay()
    bit = sda.get_value()
    scl_low()
    delay()
    set_sda_output()
    return bit

# =========================
# 读 byte
# =========================
def read_byte(ack=True):
    val = 0
    set_sda_input()
    for _ in range(8):
        val <<= 1
        scl_high()
        delay()
        if sda.get_value():
            val |= 1
        scl_low()
        delay()
    set_sda_output()
    # 发送 ACK/NACK
    if ack:
        sda_low()
    else:
        sda_high()
    scl_high()
    delay()
    scl_low()
    delay()
    sda_high()
    return val

# =========================
# 写寄存器（带重试）
# =========================
def write_reg(reg, val, retry=3):
    for attempt in range(retry):
        start()
        if (write_byte_raw(MAX30102_ADDR << 1) and
            write_byte_raw(reg) and
            write_byte_raw(val)):
            stop()
            return True
        i2c_recover()
    return False

# =========================
# 读寄存器（带重试）
# =========================
def read_reg(reg, retry=3):
    for attempt in range(retry):
        start()
        if not write_byte_raw(MAX30102_ADDR << 1):
            i2c_recover()
            continue
        if not write_byte_raw(reg):
            i2c_recover()
            continue
        start()
        if not write_byte_raw((MAX30102_ADDR << 1) | 1):
            i2c_recover()
            continue
        val = read_byte(False)
        stop()
        return val
    return 0

# =========================
# 读 FIFO（带重试）
# =========================
def read_fifo(retry=3):
    for attempt in range(retry):
        start()
        if not write_byte_raw(MAX30102_ADDR << 1):
            i2c_recover()
            continue
        if not write_byte_raw(0x07):
            i2c_recover()
            continue
        stop()
        start()
        if not write_byte_raw((MAX30102_ADDR << 1) | 1):
            i2c_recover()
            continue
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
    return 0, 0

# =========================
# 初始化 MAX30102（增加重试）
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
# 主循环（增加异常保护）
# =========================
print("Starting main loop...", flush=True)
while True:
    try:
        red, ir = read_fifo()
        if ir < 10000:
            continue

        buf.append(ir)
        red_buffer.append(red)

        if len(red_buffer) > 500:
            red_buffer.pop(0)
        if len(buf) > 500:
            buf.pop(0)

        if len(buf) >= 300 and (time.time() - last_calc_time >= CALC_INTERVAL):
            last_calc_time = time.time()

            data = np.array(buf)
            data = data - np.mean(data)
            data = np.convolve(data, np.ones(5)/5, mode='same')
            signal_amp = np.max(data) - np.min(data)

            print("\nIR_MIN =", int(np.min(buf)),
                  "IR_MAX =", int(np.max(buf)),
                  "DELTA =", int(signal_amp))

            if signal_amp < 200:
                print("WEAK SIGNAL")
                continue

            try:
                peaks, properties = find_peaks(
                    data,
                    distance=int(FS * 0.45),
                    prominence=signal_amp * 0.12
                )

                if len(peaks) < 2:
                    print("NO PULSE")
                    print("BPM = %.1f (HOLD)" % last_valid_bpm,
                          "SpO2 = %.1f%%" % last_valid_spo2)
                    continue

                intervals = np.diff(peaks)
                avg_interval = np.mean(intervals)
                bpm = 60.0 * FS / avg_interval

                red_data = np.array(red_buffer)
                red_dc = np.mean(red_data)
                ir_dc  = np.mean(data + np.mean(buf))
                red_ac = np.std(red_data)
                ir_ac  = np.std(data)

                if red_dc > 0 and ir_dc > 0 and ir_ac > 0:
                    R = (red_ac / red_dc) / (ir_ac / ir_dc)
                    spo2 = 110 - 25 * R
                    if spo2 > 100: spo2 = 100
                    if spo2 < 80: spo2 = 80
                    last_valid_spo2 = spo2
                else:
                    spo2 = last_valid_spo2

                bpm_history.append(bpm)
                if len(bpm_history) > 5:
                    bpm_history.pop(0)
                bpm_avg = np.mean(bpm_history)
                last_valid_bpm = bpm_avg

                print("BPM = %.1f" % bpm_avg,
                      "RAW = %.1f" % bpm,
                      "SpO2 = %.1f%%" % spo2)

                if bpm < 40 or bpm > 180:
                    print("INVALID BPM = %.1f" % bpm)

            except Exception as e:
                print("CALC ERROR:", e)

    except Exception as e:
        print("LOOP ERROR:", e)
        i2c_recover()
        time.sleep(0.1)
