import time
import gpiod

# ==================================
# GPIO3_A0 GPIO3_A5
# ==================================

SDA_GPIO = 20
SCL_GPIO = 21

chip = gpiod.Chip("/dev/gpiochip3")

sda = chip.get_line(SDA_GPIO)
scl = chip.get_line(SCL_GPIO)

sda.request("sda", gpiod.LINE_REQ_DIR_OUT, default_vals=[1])
scl.request("scl", gpiod.LINE_REQ_DIR_OUT, default_vals=[1])

# AS6221默认地址
AS6221_ADDR = 0x48


# ==================================
# delay
# ==================================

def delay():
    time.sleep(0.00001)


# ==================================
# gpio
# ==================================

def sda_high():
    sda.set_value(1)

def sda_low():
    sda.set_value(0)

def scl_high():
    scl.set_value(1)

def scl_low():
    scl.set_value(0)


# ==================================
# start stop
# ==================================

def start():

    sda_high()
    scl_high()
    delay()

    sda_low()
    delay()

    scl_low()


def stop():

    sda_low()
    delay()

    scl_high()
    delay()

    sda_high()
    delay()


# ==================================
# ack
# ==================================

def read_ack():

    sda.release()
    sda.request("ack", gpiod.LINE_REQ_DIR_IN)

    scl_high()
    delay()

    ack = (sda.get_value() == 0)

    scl_low()

    sda.release()
    sda.request("sda", gpiod.LINE_REQ_DIR_OUT)

    return ack


# ==================================
# write bit
# ==================================

def write_bit(bit):

    if bit:
        sda_high()
    else:
        sda_low()

    delay()

    scl_high()
    delay()

    scl_low()


# ==================================
# write byte
# ==================================

def write_byte(data):

    for _ in range(8):

        write_bit(data & 0x80)

        data <<= 1

    return read_ack()


# ==================================
# read byte
# ==================================

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

    if ack:
        sda_low()
    else:
        sda_high()

    scl_high()
    delay()

    scl_low()

    sda_high()

    return val


# ==================================
# read 16bit register
# ==================================

def read16(reg):

    start()

    if not write_byte(AS6221_ADDR << 1):
        stop()
        return 0

    if not write_byte(reg):
        stop()
        return 0

    start()

    if not write_byte((AS6221_ADDR << 1) | 1):
        stop()
        return 0

    high = read_byte(True)
    low = read_byte(False)

    stop()

    value = (high << 8) | low

    return value


# ==================================
# temperature
# ==================================

def read_temperature():

    raw = read16(0x00)

    # AS6221温度寄存器为16位二补码，LSB=0.0078125℃
    if raw & 0x8000:
        raw -= 65536

    temperature = raw * 0.0078125

    return temperature


# ==================================
# test
# ==================================

print("AS6221 TEST")

while True:

    t = read_temperature()

    print("Skin Temperature : %.2f °C" % t)

    time.sleep(1)