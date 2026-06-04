from time import sleep
import machine
import dht

from utils import log_console_file


class DHT11Sensor:
    def __init__(self, pin: int) -> None:
        self.pin: int = pin
        self.sensor = dht.DHT11(machine.Pin(pin))

    def measure_temperature_humidity(self) -> dict[str, int]:
        for attempt in range(3):
            try:
                self.sensor.measure()
                temperature: int = self.sensor.temperature()
                humidity: int = self.sensor.humidity()

                if temperature is not None and humidity is not None:
                    return {
                        "temperature": temperature,
                        "humidity": humidity
                    }
            except Exception as err:
                err_msg = f"DHT11 attempt {attempt + 1} failed: {err}"
                log_console_file(err_msg)
                sleep(1)

        log_console_file("DHT11: could not perform measure, returning zero")
        return {"temperature": 0, "humidity": 0}
