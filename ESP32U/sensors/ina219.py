import time


class INA219:
    def __init__(self, i2c: object, addr: int = 0x40) -> None:
        self.i2c: object = i2c
        self.addr: int = int(addr)
        try:
            self._write_word(0x00, 0x399F)
            time.sleep_ms(10)
        except Exception:
            pass

    def _write_word(self, reg: int, val: int) -> None:
        data = bytes([(val >> 8) & 0xFF, val & 0xFF])
        self.i2c.writeto_mem(self.addr, int(reg), data)

    def _read_word(self, reg: int) -> int:
        data = self.i2c.readfrom_mem(self.addr, int(reg), 2)
        return int((data[0] << 8) | data[1])

    def read(self) -> dict:
        try:
            bus_raw = self._read_word(0x02)
            bus_v = (bus_raw >> 3) * 0.004

            shunt_raw = self._read_word(0x01)
            if shunt_raw & 0x8000:
                shunt_raw -= 0x10000
            shunt_mv = shunt_raw * 0.01

            current_ma = shunt_mv / 0.1
            return {
                "battery": round(bus_v, 2),
                "current_ma": round(current_ma, 1),
            }
        except Exception:
            return {
                "battery": 0.0,
                "current_ma": 0.0,
            }
