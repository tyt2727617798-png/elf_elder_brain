import time
import gpiod
import threading

SDA_GPIO = 1
SCL_GPIO = 6
MAX30102_ADDR = 0x57
I2C_DELAY = 0.0001

chip = gpiod.Chip("/dev/gpiochip3")
sda = None
scl = None
_gpio_lock = threading.Lock()
_gpio_initialized = False

def init_gpio():
    global sda, scl, _gpio_initialized
    with _gpio_lock:
        if _gpio_initialized:
            return
        sda = chip.get_line(SDA_GPIO)
        scl = chip.get_line(SCL_GPIO)
        sda.request("sda_out", gpiod.LINE_REQ_DIR_OUT, default_vals=[1])
        scl.request("scl_out", gpiod.LINE_REQ_DIR_OUT, default_vals=[1])
        _gpio_initialized = True

def sda_high(): sda.set_value(1)
def sda_low():  sda.set_value(0)
def scl_high(): scl.set_value(1)
def scl_low():  scl.set_value(0)
def delay(): time.sleep(I2C_DELAY)

def set_sda_input():
    # 安全切换：先释放，再请求为输入
    try:
        sda.release()
    except:
        pass
    sda.request("sda_in", gpiod.LINE_REQ_DIR_IN)

def set_sda_output():
    try:
        sda.release()
    except:
        pass
    sda.request("sda_out", gpiod.LINE_REQ_DIR_OUT, default_vals=[1])

def i2c_recover():
    try:
        set_sda_output()
        scl.request("scl_out", gpiod.LINE_REQ_DIR_OUT, default_vals=[1])
        sda_high(); scl_high(); delay()
        for _ in range(9):
            scl_high(); delay()
            scl_low(); delay()
        sda_low(); delay()
        scl_high(); delay()
        sda_high(); delay()
        set_sda_output()
    except:
        pass

def start():
    sda_high(); scl_high(); delay()
    sda_low(); delay(); scl_low(); delay()

def stop():
    sda_low(); delay()
    scl_high(); delay(); sda_high(); delay()

def read_ack(timeout=0.005):
    set_sda_input()
    scl_low(); delay()
    scl_high(); delay()
    start_t = time.time()
    while sda.get_value() == 1:
        if time.time() - start_t > timeout:
            scl_low()
            set_sda_output()
            return False
    scl_low()
    set_sda_output()
    return True

def write_bit(bit):
    if bit: sda_high()
    else: sda_low()
    delay(); scl_high(); delay(); scl_low(); delay()

def write_byte_raw(data):
    for _ in range(8):
        write_bit(data & 0x80)
        data <<= 1
    return read_ack()

def write_byte(data, retry=3):
    for _ in range(retry):
        start()
        if write_byte_raw(data): stop(); return True
        i2c_recover()
    return False

def read_bit():
    set_sda_input()
    scl_high(); delay()
    bit = sda.get_value()
    scl_low(); delay(); set_sda_output()
    return bit

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
    scl_high(); delay(); scl_low(); delay()
    sda_high()
    return val

def write_reg(reg, val, retry=3):
    for _ in range(retry):
        start()
        if (write_byte_raw(MAX30102_ADDR << 1) and
            write_byte_raw(reg) and write_byte_raw(val)):
            stop(); return True
        i2c_recover()
    return False

def read_reg(reg, retry=3):
    for _ in range(retry):
        start()
        if not write_byte_raw(MAX30102_ADDR << 1): i2c_recover(); continue
        if not write_byte_raw(reg): i2c_recover(); continue
        start()
        if not write_byte_raw((MAX30102_ADDR << 1) | 1): i2c_recover(); continue
        val = read_byte(False)
        stop(); return val
    return 0

def read_fifo(retry=3):
    for _ in range(retry):
        start()
        if not write_byte_raw(MAX30102_ADDR << 1): i2c_recover(); continue
        if not write_byte_raw(0x07): i2c_recover(); continue
        stop()
        start()
        if not write_byte_raw((MAX30102_ADDR << 1) | 1): i2c_recover(); continue
        b1 = read_byte(True); b2 = read_byte(True); b3 = read_byte(True)
        b4 = read_byte(True); b5 = read_byte(True); b6 = read_byte(False)
        stop()
        red = ((b1 << 16) | (b2 << 8) | b3) & 0x3FFFF
        ir  = ((b4 << 16) | (b5 << 8) | b6) & 0x3FFFF
        return red, ir
    return 0, 0

def init_max30102():
    init_gpio()           # 保证 GPIO 已初始化（内部有锁和标志位）
    part = read_reg(0xFF)
    print("PART ID =", hex(part))
    write_reg(0x09, 0x40)
    time.sleep(1)
    write_reg(0x08, 0x0F)
    write_reg(0x09, 0x03)
    write_reg(0x0A, 0x6F)
    write_reg(0x0C, 0x24)
    write_reg(0x0D, 0x24)
    time.sleep(1)
    print("MAX30102 初始化完成")
