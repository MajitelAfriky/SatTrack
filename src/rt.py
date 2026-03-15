import machine
import time
from bno055_base import BNO055_BASE

i2c = machine.I2C(0, scl=machine.Pin(9), sda=machine.Pin(8))
imu = BNO055_BASE(i2c, address=0x29, crystal=False)

print("Inicializace senzoru...")
time.sleep(1)
print("Ukazatel pripraven. Naklanej senzor do stran!\n")

while True:
    # Vycteni Eulerovych uhlu (Heading, Roll, Pitch)
    euler_data = imu.euler()
    
    # Pojistka pro pripad, ze by senzor zrovna pocital a nevratil data
    if euler_data[1] is not None:
        roll = euler_data[1]
        
        # Omezime sledovany uhel na -45 az +45 stupnu pro lepsi citlivost
        # Vsechno nad 45 stupnu zustane na okraji ukazatele
        constrained_roll = max(-45.0, min(45.0, roll))
        
        # Prepocet uhlu (-45 az 45) na textovou pozici (0 az 40)
        # Pridame 45, abychom meli rozsah 0-90, a vydelime to tak, aby maximum bylo 40 znaku
        pos = int((constrained_roll + 45.0) / 90.0 * 40.0)
        
        # Vykresleni samotneho ukazatele pomoci ASCII znaku
        levy_prostor = "-" * pos
        pravy_prostor = "-" * (40 - pos)
        vodovaha = "[" + levy_prostor + "O" + pravy_prostor + "]"
        
        # Vypsani na jeden radek. Znak \r zajisti prepsani predchoziho textu.
        print("\rNaklon: {:>6.1f} st.  {}".format(roll, vodovaha), end="")
        
    # Kratka pauza pro plynulost animace a nezahuseni I2C sbernice
    time.sleep(0.05)