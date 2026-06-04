from time import sleep
import machine

from utils import log_console_file


class MQ135Sensor:
    def __init__(self, pin):
        self.pin = pin
        print(f"pin is: {pin}")
        self.sensor = machine.ADC(pin)
        self.sensor.atten(machine.ADC.ATTN_11DB)
        self.sensor.width(machine.ADC.WIDTH_12BIT)

    def measure_co2(self) -> dict[str, int]:
        for attempt in range(3):
            try:
                raw = self.sensor.read()  # 0–4095
                voltage = raw * (3.3 / 4095.0)

                Rs = 1000 * (3.3 - voltage) / voltage

                ratio = Rs / 85.0

                ppm = 116.6020682 * (ratio ** -2.769034857)
                ppm = max(300, min(5000, round(ppm)))

                return {"co2": int(ppm)}

            except Exception as err:
                log_console_file(f"MQ135 attempt {attempt + 1} failed: {err}")
                sleep(1)

        log_console_file("MQ135: could not perform measure, returning zero")
        return {"co2": 0}
