import machine
import time
import rp2
import struct
import sys
import uselect

# ==========================================
# 1. PIO UART (TMC2209 SETUP)
# ==========================================
@rp2.asm_pio(
    set_init=rp2.PIO.IN_HIGH,
    out_init=rp2.PIO.IN_HIGH,
    out_shiftdir=rp2.PIO.SHIFT_RIGHT
)
def pio_uart_tx_half_duplex():
    pull()
    set(pindirs, 1)
    set(pins, 0) [7]
    set(x, 7)
    label("bitloop")
    out(pins, 1)
    jmp(x_dec, "bitloop") [6]
    set(pins, 1) [7]
    set(pindirs, 0)

class TMC2209_PIO_UART:
    def __init__(self, tx_pin, baudrate=115200, address=0):
        self.address = address
        self.sync_byte = 0x05
        pio_freq = baudrate * 8
        pin_obj = machine.Pin(tx_pin)
        self.sm = rp2.StateMachine(1, pio_uart_tx_half_duplex, freq=pio_freq, set_base=pin_obj, out_base=pin_obj)
        self.sm.active(1)

    def _calc_crc(self, datagram):
        crc = 0
        for byte in datagram[:-1]:
            for i in range(8):
                current_bit = (crc >> 7) & 1
                crc = (crc << 1) & 0xFF
                if (byte >> (7 - i)) & 1: current_bit ^= 1
                if current_bit: crc ^= 0x07
        return crc

    def write_register(self, reg_addr, value):
        write_addr = 0x80 | reg_addr
        data_bytes = struct.pack(">I", value)
        datagram = bytearray([self.sync_byte, self.address, write_addr, data_bytes[0], data_bytes[1], data_bytes[2], data_bytes[3], 0x00])
        datagram[7] = self._calc_crc(datagram)
        for byte in datagram: self.sm.put(byte)
        time.sleep(0.01)

    def setup_driver(self):
        self.write_register(0x00, 0x000000C0)
        self.write_register(0x6C, 0x15000053)
        self.write_register(0x10, 0x00011002)

# ==========================================
# 2. PIO KROKOVÝ MOTOR (ABSOLUTNÍ POZICE + PŘEVODOVKA)
# ==========================================
@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
def stepper_pio():
    pull(block)             
    mov(y, osr)
    pull(block)             
    label("step_loop")
    set(pins, 1) [5]
    set(pins, 0)
    mov(x, osr)
    label("delay_loop")
    jmp(x_dec, "delay_loop")
    jmp(y_dec, "step_loop")

class PioStepper:
    def __init__(self, step_pin, dir_pin, en_pin, microsteps=8, steps_per_rev=200, gear_ratio=1.0):
        self.step = machine.Pin(step_pin, machine.Pin.OUT)
        self.dir = machine.Pin(dir_pin, machine.Pin.OUT)
        self.en = machine.Pin(en_pin, machine.Pin.OUT)
        
        self.steps_per_360 = int(steps_per_rev * microsteps * gear_ratio)
        self.current_angle = 0.0
        
        # Proměnná pro sledování doby běhu motoru
        self.busy_until = time.ticks_ms()
        
        self.sm = rp2.StateMachine(0, stepper_pio, freq=1_000_000, set_base=self.step)
        self.sm.active(1)
        self.disable()

    def enable(self):
        self.en.value(0)

    def disable(self):
        self.en.value(1)

    def move_relative(self, delta_degrees, output_rpm):
        # 1. OCHRANA PROTI ZAMRZNUTÍ
        # Pokud motor fyzicky stále provádí předchozí pohyb, zablokujeme nové příkazy.
        # Časovač time.ticks_diff bezpečně řeší i přetečení milisekund.
        if time.ticks_diff(time.ticks_ms(), self.busy_until) < 0:
            return

        if output_rpm <= 0 or delta_degrees == 0:
            return
            
        direction = 1 if delta_degrees > 0 else 0
        self.dir.value(direction)
        
        steps = int((abs(delta_degrees) / 360.0) * self.steps_per_360)
        if steps == 0:
            return
            
        time_per_rev_us = 60000000.0 / output_rpm
        delay_us = int(time_per_rev_us / self.steps_per_360)
        
        # 2. VÝPOČET DOBY BĚHU
        # Zjistíme, kolik milisekund bude tento příkaz trvat a zamkneme motor
        move_duration_ms = int((steps * delay_us) / 1000)
        self.busy_until = time.ticks_add(time.ticks_ms(), move_duration_ms)
        
        time.sleep_us(10)
        
        # Nyní máme absolutní jistotu, že FIFO paměť není plná a zápis nezamrzne
        self.sm.put(steps - 1)
        self.sm.put(delay_us)
        
        actual_delta = (steps * 360.0) / self.steps_per_360
        self.current_angle += actual_delta if direction == 1 else -actual_delta
        self.current_angle %= 360.0

# ==========================================
# 3. SÉRIOVÁ SMYČKA S GPREDICTEM
# ==========================================
if __name__ == '__main__':
    UART_PIN = 16
    DIR_PIN = 22
    STEP_PIN = 21
    EN_PIN = 20

    tmc = TMC2209_PIO_UART(tx_pin=UART_PIN)
    tmc.setup_driver()
    
    # Pridano gear_ratio=49.3 pro planetovou/snekovou prevodovku
    motor = PioStepper(STEP_PIN, DIR_PIN, EN_PIN, microsteps=8, gear_ratio=49.3)
    motor.enable()

    target_az = 0.0
    target_el = 0.0

    poll = uselect.poll()
    poll.register(sys.stdin, uselect.POLLIN)
    buffer = ""

    while True:
        try:
            events = poll.poll(15)
            if events:
                for file, event in events:
                    if event & uselect.POLLIN:
                        char = sys.stdin.read(1)
                        if char:
                            buffer += char
            else:
                if buffer:
                    up_buffer = buffer.upper()
                    has_digits = any(c.isdigit() for c in up_buffer)
                    
                    if not has_digits:
                        clean = up_buffer.replace('\n', '').replace('\r', '').strip()
                        
                        if clean == "AZ":
                            odpoved = "AZ0\n"
                        elif clean == "EL":
                            odpoved = "EL0\n"
                        else:
                            odpoved = "AZ0 EL0\n"
                            
                        sys.stdout.buffer.write(odpoved.encode('utf-8'))
                        sys.stdout.flush()
                    else:
                        parts = up_buffer.replace('\n', ' ').replace('\r', ' ').split()
                        for p in parts:
                            if p.startswith("AZ"):
                                try: target_az = float(p[2:].replace(',', '.'))
                                except ValueError: pass
                            elif p.startswith("EL"):
                                try: target_el = float(p[2:].replace(',', '.'))
                                except ValueError: pass
                    buffer = ""
            
            diff = target_az - motor.current_angle
            diff = (diff + 180) % 360 - 180
            
            if abs(diff) > 0.5:
                # RPM nastavujeme na 1.5 - to je velmi klidna a realisticka rychlost rotace anteny
                motor.move_relative(diff, output_rpm=1.5)
                
        except Exception:
            buffer = ""