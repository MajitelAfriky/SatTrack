import machine
import time
import rp2
import struct
from bno055_base import BNO055_BASE

# ==========================================
# 1. PIO HALF-DUPLEX UART TX
# ==========================================
@rp2.asm_pio(
    set_init=rp2.PIO.IN_HIGH,
    out_init=rp2.PIO.IN_HIGH,
    out_shiftdir=rp2.PIO.SHIFT_RIGHT
)
def pio_uart_tx_half_duplex():
    pull()                    # Ceka na bajt ve FIFO pameti
    
    set(pindirs, 1)           # Prevezme kontrolu: pin se stava vystupem
    
    set(pins, 0) [7]          # Start bit (0) + zpozdeni (celkem 8 cyklu)
    
    set(x, 7)                 # Priprava na 8 datovych bitu
    label("bitloop")
    out(pins, 1)              # Vystrci 1 bit na pin z OSR registru
    jmp(x_dec, "bitloop") [6] # Odpocet bitu + zpozdeni (smycka trva 8 cyklu)
    
    set(pins, 1) [7]          # Stop bit (1) + zpozdeni
    
    set(pindirs, 0)           # Uvolneni sbernice: pin se stava vstupem

class TMC2209_PIO_UART:
    def __init__(self, tx_pin, baudrate=115200, address=0):
        self.address = address
        self.sync_byte = 0x05
        
        # Matematika casovani: Jeden bit trva 8 PIO instrukci
        # Pri 115200 bps musi PIO bezet na frekvenci 115200 * 8 = 921600 Hz
        pio_freq = baudrate * 8
        pin_obj = machine.Pin(tx_pin)
        
        # Spoustime na StateMachine 1 (SM 0 je pro motor)
        self.sm = rp2.StateMachine(
            1, pio_uart_tx_half_duplex, 
            freq=pio_freq, 
            set_base=pin_obj, 
            out_base=pin_obj
        )
        self.sm.active(1)

    def _calc_crc(self, datagram):
        crc = 0
        for byte in datagram[:-1]:
            for i in range(8):
                current_bit = (crc >> 7) & 1
                crc = (crc << 1) & 0xFF
                if (byte >> (7 - i)) & 1:
                    current_bit ^= 1
                if current_bit:
                    crc ^= 0x07
        return crc

    def write_register(self, reg_addr, value):
        write_addr = 0x80 | reg_addr
        data_bytes = struct.pack(">I", value)
        
        datagram = bytearray([
            self.sync_byte, self.address, write_addr, 
            data_bytes[0], data_bytes[1], data_bytes[2], data_bytes[3], 0x00
        ])
        
        datagram[7] = self._calc_crc(datagram)
        
        # Odeslani datagramu bajt po bajtu do PIO automatu
        for byte in datagram:
            self.sm.put(byte)
            
        time.sleep(0.01)

    def setup_driver(self):
        print("Konfiguruji TMC2209 pres bezkolizni PIO UART...")
        self.write_register(0x00, 0x000000C0) # GCONF
        self.write_register(0x6C, 0x15000053) # CHOPCONF (8 mikrokroku)
        self.write_register(0x10, 0x00011002) # IHOLD_IRUN
        print("Konfigurace dokoncena.")

# ==========================================
# 2. PIO MOTOR KONTROLER
# ==========================================
@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
def stepper_spin_pio():
    pull(noblock)
    mov(x, osr)
    set(pins, 1) [5]
    set(pins, 0)
    mov(y, x)
    label("delay")
    jmp(y_dec, "delay")

class BackgroundSpinner:
    def __init__(self, step_pin, dir_pin, en_pin):
        self.step = machine.Pin(step_pin, machine.Pin.OUT)
        self.dir = machine.Pin(dir_pin, machine.Pin.OUT)
        self.en = machine.Pin(en_pin, machine.Pin.OUT)
        
        self.sm = rp2.StateMachine(0, stepper_spin_pio, freq=1_000_000, set_base=self.step)
        
        # ZDE BYLA CHYBA: Nesmíme automat zapnout dřív, než má data
        # self.sm.active(1) <-- Tento řádek jsme smazali
        
        self.disable()

    def enable(self):
        self.en.value(0)

    def disable(self):
        self.en.value(1)
        self.sm.active(0) # Při vypnutí motoru zastavíme i odpočet v PIO

    def set_speed(self, delay_us, direction=1):
        self.dir.value(direction)
        # 1. Nejdříve natlačíme hodnotu rychlosti do vyrovnávací paměti (FIFO)
        self.sm.put(int(delay_us))
        # 2. Až teď, když máme jistotu, že tam nečeká nula, PIO zapneme
        self.sm.active(1)

# ==========================================
# 3. HLAVNI PROGRAM
# ==========================================
if __name__ == '__main__':
    # Inicializace dynamickeho PIO UARTu primo na jednom pinu
    UART_PIN = 16
    tmc = TMC2209_PIO_UART(tx_pin=UART_PIN)
    tmc.setup_driver()

    # Inicializace motoru
    DIR_PIN = 22
    STEP_PIN = 21
    EN_PIN = 20
    motor = BackgroundSpinner(STEP_PIN, DIR_PIN, EN_PIN)

    # Inicializace BNO055
    I2C_ADDRESS = 0x29
    i2c = machine.I2C(0, scl=machine.Pin(9), sda=machine.Pin(8))
    imu = BNO055_BASE(i2c, address=I2C_ADDRESS, crystal=False)
    
    time.sleep(1)
    
    motor.enable()
    motor.set_speed(delay_us=1000, direction=1)
    
    print('\033[2J', end='')

    try:
        while True:
            heading, roll, pitch = imu.euler()
            if heading is None: heading = 0.0
            
            print('\033[H', end='')
            print("=========================================")
            print(" PIO UART TX + PIO MOTOR + BNO055")
            print("=========================================")
            print(f" HEADING: {heading:>6.1f} deg")
            print("=========================================")
            
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nPreruseno.")
    finally:
        motor.disable()
        tmc.write_register(0x10, 0x00000000)
        print("Driver odpojen.")