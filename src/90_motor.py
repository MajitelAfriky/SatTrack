from machine import Pin
import time

class StepperMotor:
    def __init__(self, step_pin, dir_pin, en_pin, steps_per_rev=200, microsteps=1):
        # Zakladni parametry motoru a driveru
        self.steps_per_rev = steps_per_rev
        self.microsteps = microsteps
        self.total_steps = self.steps_per_rev * self.microsteps
        
        # Inicializace pinu
        self.step = Pin(step_pin, Pin.OUT)
        self.dir = Pin(dir_pin, Pin.OUT)
        self.en = Pin(en_pin, Pin.OUT)
        
        self.disable()
        self.step.value(0)
        self.dir.value(0)

    def enable(self):
        self.en.value(0)

    def disable(self):
        self.en.value(1)

    def move_degrees(self, degrees, direction, rpm):
        """
        Pohyb o presny uhel definovanou rychlosti.
        """
        if rpm <= 0:
            return

        # 1. Prepočet stupnu na konkretni pocet pulzu
        steps_to_take = int((degrees / 360.0) * self.total_steps)
        
        # 2. Vypocet casovani (zpozdeni mezi pulzy pro zadane RPM)
        # 1 minuta = 60 000 000 mikrosekund
        time_per_rev_us = 60000000.0 / rpm
        delay_us = int(time_per_rev_us / self.total_steps)
        
        self.enable()
        self.dir.value(direction)
        
        # Hardwarova stabilizace smeru
        time.sleep_us(10) 
        
        # Vygenerovani pulzu
        for _ in range(steps_to_take):
            self.step.value(1)
            time.sleep_us(2)
            self.step.value(0)
            time.sleep_us(delay_us)

# --- Hlavni program ---
if __name__ == '__main__':
    DIR_PIN = 22
    STEP_PIN = 21
    EN_PIN = 20

    # Inicializace motoru
    # POZOR: Pokud se motor po spusteni otoci jen o maly kousek (napr. o 11 stupnu), 
    # znamena to, ze driver bezi v rezimu 1/8. Zmente microsteps=8 nebo microsteps=16.
    motor = StepperMotor(STEP_PIN, DIR_PIN, EN_PIN, steps_per_rev=200, microsteps=8)

    try:
        print("Spoustim nekonecnou smycku pohybu po 90 stupnich.")
        print("Pro ukonceni stisknete Ctrl+C.")
        
        while True:
            # Otoc o 90 stupnu rychlosti 60 otacek za minutu
            motor.move_degrees(degrees=90, direction=1, rpm=150)
            
            # Pidi pauza podle zadani (0.3 sekundy)
            time.sleep(0.3)

    except KeyboardInterrupt:
        print("\nSmycka prerusena uzivatelem.")
    finally:
        # Bezpecnostni odpojeni driveru
        motor.disable()
        print("Motor bezpecne odpojen od napajeni.")