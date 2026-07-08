import time, math, gpiod, threading

SDA_GPIO = 0
SCL_GPIO = 5

chip = gpiod.Chip("/dev/gpiochip3")
sda = None
scl = None
_mpu_lock = threading.Lock()
_mpu_initialized = False

MPU6050_ADDR = 0x68

def delay():
    time.sleep(0.00001)

def init_gpio():
    global sda, scl, _mpu_initialized
    with _mpu_lock:
        if _mpu_initialized:
            return
        sda = chip.get_line(SDA_GPIO)
        scl = chip.get_line(SCL_GPIO)
        sda.request("sda_out", gpiod.LINE_REQ_DIR_OUT, default_vals=[1])
        scl.request("scl_out", gpiod.LINE_REQ_DIR_OUT, default_vals=[1])
        _mpu_initialized = True

def set_sda_input():
    try: sda.release()
    except: pass
    sda.request("sda_in", gpiod.LINE_REQ_DIR_IN)

def set_sda_output():
    try: sda.release()
    except: pass
    sda.request("sda_out", gpiod.LINE_REQ_DIR_OUT, default_vals=[1])

def sda_high(): sda.set_value(1)
def sda_low():  sda.set_value(0)
def scl_high(): scl.set_value(1)
def scl_low():  scl.set_value(0)

def start():
    sda_high(); scl_high(); delay()
    sda_low(); delay()
    scl_low(); delay()

def stop():
    sda_low(); delay()
    scl_high(); delay()
    sda_high(); delay()

def read_ack():
    set_sda_input()
    scl_high(); delay()
    ack = (sda.get_value() == 0)
    scl_low()
    set_sda_output()
    return ack

def write_bit(bit):
    if bit: sda_high()
    else: sda_low()
    delay()
    scl_high(); delay()
    scl_low()

def write_byte(data):
    for _ in range(8):
        write_bit(data & 0x80)
        data <<= 1
    return read_ack()

def read_byte(ack=True):
    val = 0
    set_sda_input()
    for _ in range(8):
        val <<= 1
        scl_high(); delay()
        if sda.get_value(): val |= 1
        scl_low(); delay()
    set_sda_output()
    if ack: sda_low()
    else: sda_high()
    scl_high(); delay()
    scl_low()
    sda_high()
    return val

def write_reg(reg, val):
    start()
    if not write_byte(MPU6050_ADDR << 1): stop(); return False
    if not write_byte(reg): stop(); return False
    if not write_byte(val): stop(); return False
    stop()
    return True

def read_reg(reg):
    start()
    if not write_byte(MPU6050_ADDR << 1): stop(); return 0
    if not write_byte(reg): stop(); return 0
    start()
    if not write_byte((MPU6050_ADDR << 1) | 1): stop(); return 0
    val = read_byte(False)
    stop()
    return val

def read16(reg):
    high = read_reg(reg)
    low  = read_reg(reg + 1)
    value = (high << 8) | low
    if value > 32767: value -= 65536
    return value

def init_mpu6050():
    init_gpio()   # 安全初始化，只会执行一次
    who = read_reg(0x75)
    print("WHO_AM_I =", hex(who))
    if who not in [0x68, 0x69]:
        print("MPU6050 NOT FOUND")
        return False
    print("MPU6050 FOUND")
    write_reg(0x6B, 0x00)
    time.sleep(0.1)
    print("MPU6050 INIT OK")
    return True
