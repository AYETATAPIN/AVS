import machine
import time
import gc

try:
    from utils.ap_manager import APManager
    from sensors.dht11 import DHT11Sensor
    from sensors.mq135 import MQ135Sensor
    from displays.st7735 import ST7735Display
    from storages.tcp_storage import TCPStorage
except ImportError as e:
    print(f"Import error: {e}")


class EnvironmentalMonitor:
    def __init__(self):
        print("Initializing ESP32S3 Environmental Monitor (AP + TCP mode)")

        self.DHT11_PIN = 5
        self.MQ135_PIN = 0
        self.LED_PIN = 16

        self.led = machine.Pin(self.LED_PIN, machine.Pin.OUT)
        self.led.off()

        print("Initializing sensors...")
        self.dht11 = DHT11Sensor(self.DHT11_PIN)
        self.mq135 = MQ135Sensor(self.MQ135_PIN)

        print("Initializing display...")
        self.display = ST7735Display()

        # Start AP
        ap = APManager(ssid="ESP32S3-Sensor", password="12345678")
        ap.start()

        # TCP storage (to PC)
        self.tcp_storage = TCPStorage(port=12345)
        self.tcp_storage.start_server()

        print(f"Free memory: {gc.mem_free()} bytes")
        print("System ready - connect PC to AP and TCP port")

    def read_all_sensors(self):
        data = {}

        dht_data = self.dht11.read_data()
        if 'temperature' in dht_data:
            data['temperature'] = dht_data['temperature']
        if 'humidity' in dht_data:
            data['humidity'] = dht_data['humidity']

        mq_data = self.mq135.read_data()
        if 'gas_level' in mq_data:
            data['gas_level'] = mq_data['gas_level']

        # Add metadata
        data['sensor_type'] = 'ESP32S3'
        data['location'] = 'Room_101'

        return data

    def run_measurement_cycle(self, count=10, interval=2):
        print(f"Starting {count} measurements")

        for i in range(count):
            print(f"\nMeasurement {i + 1}/{count}")

            self.led.on()
            sensor_data = self.read_all_sensors()
            print(sensor_data)

            # Display
            self.display.show_measurement(i + 1, count, sensor_data)

            # Send raw data to PC via TCP
            self.tcp_storage.send_measurement(sensor_data)

            # Optional: check for incoming commands from PC
            cmd = self.tcp_storage.receive_command()
            if cmd:
                # Handle commands here if needed (e.g., "reset", config)
                pass

            # Console output
            print(f"Temp: {sensor_data.get('temperature', 'N/A')}C")
            print(f"Hum: {sensor_data.get('humidity', 'N/A')}%")
            print(f"Gas: {sensor_data.get('gas_level', 'N/A')}%")

            self.led.off()

            if i < count - 1:
                time.sleep(interval)

        print("\nMeasurement cycle completed")
        self.tcp_storage.close()


def main():
    monitor = EnvironmentalMonitor()
    monitor.run_measurement_cycle(count=10, interval=10)  # Adjust as needed

    monitor.display.clear()
    print("Application finished")


if __name__ == "__main__":
    main()