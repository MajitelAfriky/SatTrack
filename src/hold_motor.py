from machine import Pin
import time

class StepperMotor:
    def __init__(self, step_pin, dir_pin, en_pin):
        self.step = Pin(step_pin, Pin.OUT)
        self.dir = Pin(dir_pin, Pin.OUT)
        self.en = Pin(en_pin, Pin.OUT)
        
        # Vychozi stav: motor je vypnuty a volne se protaci
        self.disable()
        self.step.value(0)
        self.dir.value(0)

    def enable(self):
        # Logicka 0 zapne H-mustky v TMC2209
        self.en.value(0)

    def disable(self):
        # Logicka 1 vypne H-mustky, rotor je volny
        self.en.value(1)

# --- Hlavni program ---
if __name__ == '__main__':
    DIR_PIN = 22
    STEP_PIN = 21
    EN_PIN = 20

    motor = StepperMotor(STEP_PIN, DIR_PIN, EN_PIN)

    try:
        print("Zapinam driver a delam kratky pohyb pro probuzeni StealthChop...")
        
        motor.enable()
        
        # Odeslani 50 pulzu pro iniciaci cívek
        motor.dir.value(1)
        time.sleep_us(10)
        
        for _ in range(50):
            motor.step.value(1)
            time.sleep_us(2)
            motor.step.value(0)
            time.sleep_us(2000) # Pomaly pohyb
            
        print("Pohyb ukoncen. Nyni by mel motor pevne drzet pozici.")
        print("Sledujte odber na zdroji a zkuste otocit hrideli.")
        
        # Smycka pro drzeni pozice
        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nPreruseno uzivatelem (KeyboardInterrupt).")
    finally:
        # Pusteni rotoru a odpojeni proudu do civek
        motor.disable()
        print("Motor uvolnen. Civky jsou bez proudu.")