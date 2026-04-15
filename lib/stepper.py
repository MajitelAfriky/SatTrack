import machine
import time
import rp2

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