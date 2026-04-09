import sys
import uselect

az = 0.0
el = 0.0

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
                
                # Zkontrolujeme, jestli zprava obsahuje jakakoliv cisla
                has_digits = any(c.isdigit() for c in up_buffer)
                
                if not has_digits:
                    # JE TO DOTAZ NA POZICI (Neobsahuje cisla, jen pismena AZ, EL nebo P)
                    clean = up_buffer.replace('\n', '').replace('\r', '').strip()
                    
                    # Odpovime presne na to, na co se Hamlib 4.7.0 zrovna pta
                    if clean == "AZ":
                        odpoved = "AZ{}\n".format(int(az))
                    elif clean == "EL":
                        odpoved = "EL{}\n".format(int(el))
                    else:
                        # Fallback pro pripadne jine dotazy (napr. "P" nebo klasicke "AZ EL")
                        odpoved = "AZ{} EL{}\n".format(int(az), int(el))
                        
                    # Surovy zapis bajtu a okamzite vykopnuti dat ven
                    sys.stdout.buffer.write(odpoved.encode('utf-8'))
                    sys.stdout.flush()
                else:
                    # JE TO PRIKAZ K POHYBU (Obsahuje ciselne souradnice)
                    parts = up_buffer.replace('\n', ' ').replace('\r', ' ').split()
                    for p in parts:
                        if p.startswith("AZ"):
                            # Precteme azimut (nahrazeni carky resi pripadnou ceskou lokalizaci systemu)
                            try: az = float(p[2:].replace(',', '.'))
                            except ValueError: pass
                        elif p.startswith("EL"):
                            try: el = float(p[2:].replace(',', '.'))
                            except ValueError: pass
                            
                # Pamet cista a pripravena na dalsi krok
                buffer = ""
                
    except Exception:
        # Plynuly chod i pri neocekavane chybe
        buffer = ""