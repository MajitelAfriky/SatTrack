from machine import Pin
import time

class StepperMotor:
    def __init__(self, step_pin, dir_pin, en_pin):
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

    def run_continuous(self, direction, delay_us):
        """
        Nekonecna rotace motoru konstantni rychlosti.
        direction: 1 nebo 0 (smer otaceni)
        delay_us: Pauza mezi kroky v mikrosekundach
        """
        self.enable()
        self.dir.value(direction)
        
        # Hardwarova prodleva pro stabilizaci smeru
        time.sleep_us(10) 
        
        # Nekonecna smycka pulzu
        while True:
            self.step.value(1)
            time.sleep_us(2) 
            self.step.value(0)
            
            # Pauza urcujici rychlost rotace
            time.sleep_us(int(delay_us))

# --- Hlavni program ---
if __name__ == '__main__':
    DIR_PIN = 22
    STEP_PIN = 21
    EN_PIN = 20

    motor = StepperMotor(STEP_PIN, DIR_PIN, EN_PIN)

    try:
        print("Spoustim nekonecny beh motoru.")
        print("Pro bezpecne zastaveni stisknete Ctrl+C v konzoli (Thonny/PuTTY).")
        print("Motor bezi...")
        
        # Spusteni nekonecneho pohybu
        # Zmenseni delay_us zvysi rychlost. Pokud bude prilis male, motor nestihne odstartovat.
        motor.run_continuous(direction=1, delay_us=200)
        
    except KeyboardInterrupt:
        # Tento blok se vykona okamzite po stisku Ctrl+C
        print("\nPreruseno uzivatelem (KeyboardInterrupt).")
    finally:
        # Absolutne kriticky blok: Vykona se VZDY, i kdyz program spadne na chybu.
        # Zajisti, ze cívky nezustanou pod proudem staticky stat na miste.
        motor.disable()
        print("Motor bezpecne odpojen od napajeni.")