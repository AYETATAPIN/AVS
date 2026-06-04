from time import sleep

import dht
import machine

from utils import log_console_file


class DHT11Sensor:
    def __init__(self, pin: int) -> None:
        self.pin: int = int(pin)
        self.sensor: object = dht.DHT11(machine.Pin(self.pin))

    def measure_temperature_humidity(self) -> dict:
        for attempt in range(3):
            try:
                self.sensor.measure()
                temperature = self.sensor.temperature()
                humidity = self.sensor.humidity()
                if temperature is not None and humidity is not None:
                    return {
                        "temperature": int(temperature),
                        "humidity": int(humidity),
                    }
            except Exception as err:
                log_console_file(f"DHT11 attempt {attempt + 1} failed: {err}")
                sleep(1)

        log_console_file("DHT11: could not perform measure, returning zero")
        return {"temperature": 0, "humidity": 0}
