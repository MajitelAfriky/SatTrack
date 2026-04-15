import machine
import time
import rp2
import struct

@rp2.asm_pio(
    set_init=rp2.PIO.IN_HIGH,
    out_init=rp2.PIO.IN_HIGH,
    out_shiftdir=rp2.PIO.SHIFT_RIGHT
)
def pio_uart_tx_half_duplex():
    pull()
    set(pindirs, 1)
    set(pins, 0) [7]
    set(x, 7)
    label("bitloop")
    out(pins, 1)
    jmp(x_dec, "bitloop") [6]   
    set(pins, 1) [7]
    set(pindirs, 0)

class TMC2209_PIO_UART:
    def __init__(self, tx_pin, baudrate=115200, address=0):
        self.address = address
        self.sync_byte = 0x05
        pio_freq = baudrate * 8
        pin_obj = machine.Pin(tx_pin)
        self.sm = rp2.StateMachine(1, pio_uart_tx_half_duplex, freq=pio_freq, set_base=pin_obj, out_base=pin_obj)
        self.sm.active(1)

    def _calc_crc(self, datagram):
        crc = 0
        for byte in datagram[:-1]:
            for i in range(8):
                current_bit = (crc >> 7) & 1
                crc = (crc << 1) & 0xFF
                if (byte >> (7 - i)) & 1: current_bit ^= 1
                if current_bit: crc ^= 0x07
        return crc

    def write_register(self, reg_addr, value):
        write_addr = 0x80 | reg_addr
        data_bytes = struct.pack(">I", value)
        datagram = bytearray([self.sync_byte, self.address, write_addr, data_bytes[0], data_bytes[1], data_bytes[2], data_bytes[3], 0x00])
        datagram[7] = self._calc_crc(datagram)
        for byte in datagram: self.sm.put(byte)
        time.sleep(0.01)

    def setup_driver(self):
        self.write_register(0x00, 0x000000C0)# Zaonutí UART řízení
        self.write_register(0x6C, 0x15000053)# Nastavení 8 mikrostepů
        self.write_register(0x10, 0x00011002)# Digitální nastevení proudového omezení (IHOLD_IRUN)
                                             # 0x00011002 znamená: IRUN=16 (max proud), IHOLD=2 (hold proud), TPOWERDOWN=1 (čas do snížení proudu po zastavení)
