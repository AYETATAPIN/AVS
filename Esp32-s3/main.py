import machine
import network
import json
import uasyncio as asyncio

from sensors.dht11 import DHT11Sensor
from sensors.mq135 import MQ135Sensor
from storages.mqtt_storage import MQTTStorage
from utils import log_console_file, CONFIG_FILE, get_rfc3339_timestamp


class EnvironmentalMonitor:
    def __init__(self) -> None:
        log_console_file("Reading config")

        with open(CONFIG_FILE, "r") as f:
            self.config = json.load(f)

        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)

        ssid = self.config["WIFI"]["ssid"]
        password = self.config["WIFI"]["password"]

        if not wlan.isconnected():
            log_console_file(f"Connecting to WiFi: {ssid} with password {password}")
            wlan.connect(ssid, password)

            while not wlan.isconnected():
                machine.idle()

        log_console_file(f"WiFi connected, network config: {wlan.ifconfig()}")

        self.device_id: str = "esp32_001"

        self.dht11_pin: int = self.config["PINS"]["sensors"]["dht11"]
        self.mq135_pin: int = self.config["PINS"]["sensors"]["mq135"]
        self.led_pin: int = self.config["PINS"]["sensors"]["led"]

        self.led = machine.Pin(self.led_pin, machine.Pin.OUT)
        self.led.off()

        log_console_file("Initializing sensors")

        self.dht11 = DHT11Sensor(self.dht11_pin)
        self.mq135 = MQ135Sensor(self.mq135_pin)

        log_console_file("Initializing MQTT")

        self.mqtt_ip: str = self.config["MQTT"]["ip"]
        self.mqtt_port: int = self.config["MQTT"]["port"]
        self.sensor_id: str = self.config["MQTT"]["sensor_id"]

        self.building_name: str = self.config["DEVICE_LOCATION"]["buildingName"]
        self.room_number: str = self.config["DEVICE_LOCATION"]["roomNumber"]

        self.data_topic: str = f"sensors/room{self.room_number}/data"
        self.commands_topic: str = f"devices/{self.device_id}/commands"
        self.response_topic: str = f"devices/{self.device_id}/response"

        self.mqtt_storage = MQTTStorage(
            mqtt_ip=self.mqtt_ip,
            port=self.mqtt_port,
            client_id=self.device_id,
            topic=self.data_topic,
            building_name=self.building_name,
            room_number=self.room_number
        )

        self.mqtt_storage.connect()
        self.mqtt_storage.client.set_callback(self.mqtt_callback)
        self.mqtt_storage.client.subscribe(self.commands_topic)

        log_console_file("Initialization completed")

    def read_all_sensors(self) -> dict[str, int]:
        data = dict()

        dht11_data = self.dht11.measure_temperature_humidity()
        mq135_data = self.mq135.measure_co2()

        data.update(dht11_data)
        data.update(mq135_data)

        return data

    def mqtt_callback(self, topic, msg):
        try:
            data = json.loads(msg)
            log_console_file(f"got command: {msg}")
            command_id = data['command_id']
            command = data['command']
            parameters = data.get('parameters', {})

            self.led.on()

            if command == 'get_sensors':
                sensor_data = self.read_all_sensors()
                response = {
                    "command_id": command_id,
                    "status": "success",
                    "data": sensor_data
                }
            elif command == 'reboot':
                delay = parameters.get('delay', 0)
                response = {
                    "command_id": command_id,
                    "status": "success",
                    "data": {"message": f"rebooting in {delay}s"}
                }
                asyncio.get_event_loop().call_later(delay, machine.reset)
            elif command == 'get_battery':
                # Assuming battery measurement logic here
                battery = 3.7  # Placeholder
                percentage = 85  # Placeholder
                response = {
                    "command_id": command_id,
                    "status": "success",
                    "data": {"battery": battery, "percentage": percentage}
                }
            elif command == 'get_version':
                firmware_version = "1.2.3"  # Placeholder
                response = {
                    "command_id": command_id,
                    "status": "success",
                    "data": {"firmware_version": firmware_version}
                }
            # Add handlers for other commands as needed
            else:
                response = {
                    "command_id": command_id,
                    "status": "failed",
                    "data": {"error": "Unknown command"}
                }

            # Add optional fields if available
            firmware_version = "1.2.3"  # Placeholder
            battery = 3.7  # Placeholder
            wifi_signal = -45  # Placeholder
            response.update({
                "firmware_version": firmware_version,
                "battery": battery,
                "wifi_signal": wifi_signal
            })

            self.mqtt_storage.client.publish(self.response_topic, json.dumps(response))
            self.led.off()
        except Exception as e:
            log_console_file(f"Error processing command: {e}")
            try:
                response = {
                    "command_id": command_id,
                    "status": "failed",
                    "data": {"error": str(e)}
                }
                self.mqtt_storage.client.publish(self.response_topic, json.dumps(response))
            except:
                pass

    async def mqtt_loop(self) -> None:
        log_console_file("Starting MQTT loop")
        while True:
            if not self.mqtt_storage.connected:
                self.mqtt_storage.connect()
                self.mqtt_storage.client.subscribe(self.commands_topic)
            self.mqtt_storage.client.check_msg()
            await asyncio.sleep(0.1)

    async def run(self) -> None:
        # Send sensor data once at startup to data topic
        self.led.on()
        log_console_file("Sending initial sensor data")
        sensor_data = self.read_all_sensors()
        initial_payload = {
            "sensorId": self.device_id,
            "buildingName": self.building_name,
            "roomNumber": self.room_number,
            "ts": get_rfc3339_timestamp(),
        }
        initial_payload.update(sensor_data)
        self.mqtt_storage.save_measurement(initial_payload)
        self.led.off()

        asyncio.create_task(self.mqtt_loop())

        while True:
            await asyncio.sleep(1)


async def main() -> None:
    monitor = EnvironmentalMonitor()
    await monitor.run()


if __name__ == "__main__":
    asyncio.run(main())