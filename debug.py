import serial
import time

COM_PORT = 'COM5'
BAUD_RATE = 115200 

print(f"Otevírám port {COM_PORT}...")
try:
    # Otevřeme port s dvouvteřinovým timeoutem
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=2)
except Exception as e:
    print(f"Nepodařilo se otevřít port: {e}")
    print("Máš zavřené Thonny a rotctld?")
    exit(1)

# Krátká pauza, aby se Pico po otevření portu vzpamatovalo
time.sleep(1)

# 1. ZÁSADNÍ ZMĚNA: Posíláme čisté "AZ EL" absolutně bez odřádkování na konci
dotaz = b"AZ EL"
print(f"\n[PC -> PICO] Odesílám přesně to, co Hamlib: {repr(dotaz)}")
ser.write(dotaz)

# Nyní jen čekáme. Pico by mělo po 10 milisekundách ticha pochopit, 
# že už nic dalšího nepřijde, a poslat odpověď.

# 2. Přečteme řádek, který Pico pošle zpět
odpoved = ser.readline()

# 3. Výpis výsledku
print("\n--- VÝSLEDEK ---")
if not odpoved:
    print("[PICO -> PC] Nic nepřišlo! (Timeout)")
    print("Znamená to, že Pico pořád paličatě čeká na nějaký konec řádku.")
else:
    print(f"[PICO -> PC] Surové bajty: {odpoved}")
    if odpoved == b"AZ0.0 EL0.0\n":
        print(">>> PERFEKTNÍ! Tohle musí Hamlib stoprocentně vzít.")
    else:
        print(">>> Není to úplně přesné, zkontroluj ty znaky navíc.")

ser.close()