import machine
import time
import rp2
from bno055_base import BNO055_BASE

# --- PIO Mikrokód pro generování pulzů ---
# Tento kód se neprovádí v Pythonu, ale zkompiluje se přímo do křemíku PIO koprocesoru.
@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
def stepper_pio():
    pull(block)             # 1. Čeká na hodnotu z FIFO (Počet kroků - 1)
    mov(y, osr)             # Uloží počet kroků do pracovního registru Y
    
    pull(block)             # 2. Čeká na druhou hodnotu (Zpoždění v mikrosekundách)
    
    label("step_loop")
    set(pins, 1) [5]        # Nastaví STEP pin na 3.3V a čeká 5 cyklů (6 mikrosekund)
    set(pins, 0)            # Stáhne STEP pin na 0V
    
    mov(x, osr)             # Načte hodnotu zpoždění do registru X
    label("delay_loop")
    jmp(x_dec, "delay_loop")# Hardwarová smyčka odpočítávající zpoždění (1 cyklus = 1 us)
    
    jmp(y_dec, "step_loop") # Sníží počet kroků, pokud není pod nulou, opakuje krok

# --- Objektový obal pro PIO Motor ---
class PioStepper:
    def __init__(self, step_pin, dir_pin, en_pin, microsteps=8, steps_per_rev=200):
        self.step = machine.Pin(step_pin, machine.Pin.OUT)
        self.dir = machine.Pin(dir_pin, machine.Pin.OUT)
        self.en = machine.Pin(en_pin, machine.Pin.OUT)
        
        self.steps_per_rev = steps_per_rev * microsteps
        self.current_angle = 0.0 # Interní sledování polohy rotoru
        
        # Inicializace PIO automatu (SM 0)
        # freq=1_000_000 znamená, že jeden instrukční cyklus trvá přesně 1 mikrosekundu
        self.sm = rp2.StateMachine(0, stepper_pio, freq=1_000_000, set_base=self.step)
        self.sm.active(1)
        
        self.disable()
        self.dir.value(0)

    def enable(self):
        self.en.value(0)

    def disable(self):
        self.en.value(1)

    def move_relative(self, delta_degrees, rpm):
        if rpm <= 0 or delta_degrees == 0:
            return

        # Určení směru rotace
        direction = 1 if delta_degrees > 0 else 0
        self.dir.value(direction)
        
        # Výpočet počtu kroků
        steps = int((abs(delta_degrees) / 360.0) * self.steps_per_rev)
        if steps == 0:
            return
            
        # Výpočet zpoždění pro dosažení požadovaného RPM
        time_per_rev_us = 60000000.0 / rpm
        delay_us = int(time_per_rev_us / self.steps_per_rev)
        
        # Hardwarová stabilizace změny směru
        time.sleep_us(10)
        
        # Odeslání dat do FIFO paměti PIO koprocesoru
        # Předáváme steps - 1, protože instrukce jmp(y_dec, ...) počítá až do -1
        self.sm.put(steps - 1)
        self.sm.put(delay_us)
        
        # Aktualizace interního stavu polohy
        # Přičítáme teoretickou hodnotu, abychom zamezili kumulaci zaokrouhlovacích chyb
        actual_delta = (steps * 360.0) / self.steps_per_rev
        self.current_angle += actual_delta if direction == 1 else -actual_delta
        
        # Normalizace interního úhlu do rozsahu 0-360
        self.current_angle %= 360.0

# --- Hlavní program ---
if __name__ == '__main__':
    # Konfigurace BNO055
    I2C_ADDRESS = 0x29
    i2c = machine.I2C(0, scl=machine.Pin(9), sda=machine.Pin(8))
    imu = BNO055_BASE(i2c, address=I2C_ADDRESS, crystal=False)
    
    # Konfigurace Motoru (upraveno pro 1/8 mikrokrokování)
    DIR_PIN = 22
    STEP_PIN = 21
    EN_PIN = 20
    motor = PioStepper(STEP_PIN, DIR_PIN, EN_PIN, microsteps=8)
    
    print("Inicializace senzoru...")
    time.sleep(1) # Počkáme na náběh IMU
    
    # Zarovnání výchozí pozice motoru se senzorem při startu
    initial_heading = imu.euler()[0]
    if initial_heading is not None:
        motor.current_angle = initial_heading
    
    motor.enable()
    print("Sledování polohy aktivováno. Otáčejte senzorem.")

    try:
        while True:
            # 1. Vyčtení dat ze senzoru
            heading, roll, pitch = imu.euler()
            if heading is None:
                time.sleep(0.05)
                continue
                
            # 2. Výpočet nejkratší trajektorie (Shortest Path Math)
            # Rozdíl mezi požadovaným úhlem (heading) a aktuálním úhlem motoru
            diff = heading - motor.current_angle
            
            # Normalizace rozdílu do rozsahu -180 až +180 stupňů
            # Tím je zajištěno, že motor překoná mrtvý bod (přechod z 359 na 0) nejkratší cestou
            diff = (diff + 180) % 360 - 180
            
            # 3. Pokud je rozdíl dostatečný (např. > 0.5 stupně pro zamezení šumu), pohneme motorem
            if abs(diff) > 0.5:
                # Odeslání požadavku do PIO. Rychlost sledování (RPM) lze upravit.
                motor.move_relative(diff, rpm=80)
            
            # Formátovaný výstup do konzole
            print('\033[H\033[2J', end='') # Vyčištění terminálu
            print(f"BNO055 Heading:  {heading:>6.1f}°")
            print(f"Motor Position:  {motor.current_angle:>6.1f}°")
            print(f"Tracking Delta:  {diff:>6.1f}°")
            
            # Ponecháme procesor chvíli volný. PIO si případný pohyb odbaví hardwarově.
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\nProgram přerušen.")
    finally:
        motor.disable()
        print("Driver TMC2209 bezpečně odpojen.")