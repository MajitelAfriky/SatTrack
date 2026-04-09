import sys
import select
import re
import machine
import time

# --- NASTAVENÍ HARDWARU ---
# Inicializace stavové LED na Raspberry Pi Pico W / Pico 2 W
led = machine.Pin("LED", machine.Pin.OUT)
led_timer = 0
LED_ON_TIME_MS = 50 # Doba bliknutí v milisekundách

# --- NASTAVENÍ PARSOVÁNÍ ---
# Regulární výraz pro zachycení hodnot z protokolu Easycomm I
# Zkompilováno předem pro vyšší výkon ve smyčce
pattern = re.compile(r"AZ\s*([0-9\.]+).*?EL\s*([0-9\.]+)")

# Nastavení pro neblokující čtení ze sériové linky (USB)
poll = select.poll()
poll.register(sys.stdin, select.POLLIN)

def parse_easycomm_robust(command):
    # Očištění vstupu a převod na velká písmena pro jistotu
    command = command.strip().upper()
    match = pattern.search(command)
    
    if match:
        try:
            azimuth = float(match.group(1))
            elevation = float(match.group(2))
            return azimuth, elevation
        except ValueError:
            return None, None
            
    return None, None

# --- HLAVNÍ SMYČKA ---
while True:
    
    # 1. ČÁST: Zpracování příchozích požadavků
    if poll.poll(0):
        line = sys.stdin.readline()
        
        if line:
            az, el = parse_easycomm_robust(line)
            
            if az is not None and el is not None:
                # -> PLATNÁ DATA PŘIJATA A ROZPARSOVÁNA <-
                
                # Rozsvítíme LED a zaznamenáme aktuální čas v milisekundách
                led.value(1)
                led_timer = time.ticks_ms()
                
                # ZDE ZAVOLÁŠ SVÉ FUNKCE PRO POHYB MOTORŮ
                # move_motors(az, el)
                pass

    # 2. ČÁST: Správa hardwaru a časovačů
    # Tato část se vyhodnocuje neustále a nečeká na příchozí data z USB
    if led.value() == 1:
        # Pokud LED svítí, zkontrolujeme, zda už uplynul požadovaný čas
        if time.ticks_diff(time.ticks_ms(), led_timer) > LED_ON_TIME_MS:
            led.value(0) # Čas vypršel, zhasneme LED