from time import sleep

import machine
import math

from utils import log_console_file


class MQ135Sensor:
    RLOAD = 10.0
    RZERO = 65.7
    PARA = 116.6020682
    PARB = 2.769034857

    CORA = 0.00035
    CORB = 0.02718
    CORC = 1.39538
    CORD = 0.0018

    CORE = -0.003333333
    CORF = -0.001923077
    CORG = 1.130128205

    VCC = 5.0

    def __init__(self, pin: int) -> None:
        self.pin: int = int(pin)
        self.min_ppm: int = 350
        self.max_ppm: int = 5000
        log_console_file(
            f"MQ135 init -> pin={self.pin}, VCC={self.VCC}V, "
            f"RLOAD={self.RLOAD} kOhm, RZERO={self.RZERO}"
        )

        self.adc: object = machine.ADC(machine.Pin(self.pin))
        self.adc.atten(machine.ADC.ATTN_11DB)
        self.adc.width(machine.ADC.WIDTH_12BIT)

    def set_rzero(self, value: float) -> None:
        self.RZERO = float(value)
        log_console_file(f"MQ135 RZERO overridden: {self.RZERO}")

    def set_ppm_limits(self, min_ppm: int, max_ppm: int) -> None:
        low = int(min_ppm)
        high = int(max_ppm)
        if high <= low:
            high = low + 1
        self.min_ppm = low
        self.max_ppm = high
        log_console_file(f"MQ135 PPM limits set: min={self.min_ppm}, max={self.max_ppm}")

    def read_raw_adc(self) -> int:
        return int(self.adc.read())

    def get_resistance(self, raw: int = None) -> float:
        if raw is None:
            raw = self.read_raw_adc()
        if raw == 0:
            return -1.0

        voltage = raw * 3.3 / 4095.0
        if voltage >= self.VCC:
            return 0.0

        return self.RLOAD * (self.VCC / voltage - 1.0)

    def get_correction_factor(self, temperature: float, humidity: float) -> float:
        if temperature >= 20:
            return self.CORE * temperature + self.CORF * humidity + self.CORG
        return self.CORA * temperature * temperature - self.CORB * temperature + self.CORC - (humidity - 33.0) * self.CORD

    def get_corrected_resistance(self, temperature: float, humidity: float, rs: float = None) -> float:
        if rs is None:
            rs = self.get_resistance()
        if rs <= 0:
            return -1.0

        correction = self.get_correction_factor(temperature, humidity)
        if correction <= 0:
            return -1.0
        return rs / correction

    def calculate_ppm_from_rs(self, rs_corr: float) -> int:
        ratio = rs_corr / self.RZERO
        ppm = self.PARA * math.pow(ratio, -self.PARB)
        ppm = max(self.min_ppm, min(self.max_ppm, round(ppm)))
        return int(ppm)

    def measure_co2_diagnostics(self, temperature: float, humidity: float) -> dict:
        raw = self.read_raw_adc()
        rs = self.get_resistance(raw)
        if rs <= 0:
            raise ValueError("Invalid sensor resistance")

        rs_corr = self.get_corrected_resistance(temperature, humidity, rs=rs)
        if rs_corr <= 0:
            raise ValueError("Invalid corrected resistance")

        ppm = self.calculate_ppm_from_rs(rs_corr)
        ratio = rs_corr / self.RZERO
        return {
            "mq_raw_adc": int(raw),
            "mq_rs": float(rs),
            "mq_rs_corr": float(rs_corr),
            "mq_ratio": float(ratio),
            "co2": int(ppm),
            "read_ok": True,
        }

    def measure_co2(self, temperature: float, humidity: float) -> dict:
        for attempt in range(3):
            try:
                diagnostic = self.measure_co2_diagnostics(temperature, humidity)
                log_console_file(
                    f"MQ135 -> CO2={diagnostic['co2']} ppm "
                    f"(Rs_corr={diagnostic['mq_rs_corr']:.1f} kOhm, "
                    f"ratio={diagnostic['mq_ratio']:.3f})"
                )
                return {"co2": int(diagnostic["co2"])}
            except Exception as err:
                log_console_file(f"MQ135 attempt {attempt + 1} failed: {err}")
                sleep(1.2)

        log_console_file("MQ135: all attempts failed -> returning 0")
        return {"co2": 0}
