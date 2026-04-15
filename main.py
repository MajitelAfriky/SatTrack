import machine
import time
import rp2
import struct
import sys
import uselect
from tmc2209 import TMC2209_PIO_UART
from stepper import PioStepper

UART_PIN = 16
DIR_PIN = 22
STEP_PIN = 21
EN_PIN = 20

MICROSTEPS = 8 # 1.8° * 8 = 0.225° na krok, 1600 kroků na otáčku.
GEAR_RATIO = 50.4
RPM = 0.8 # 0.8 * 50.4 = 40.32 RPM na hřídeli motoru

tmc = TMC2209_PIO_UART(tx_pin=UART_PIN)
tmc.setup_driver()

# Pridano gear_ratio=50.4 pro planetovou/snekovou prevodovku
motor = PioStepper(STEP_PIN, DIR_PIN, EN_PIN, microsteps=MICROSTEPS, gear_ratio=GEAR_RATIO)
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
            motor.move_relative(diff, output_rpm=RPM)

    except Exception:
        buffer = ""