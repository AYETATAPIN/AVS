import json
import uasyncio as asyncio
from umqtt.robust import MQTTClient

from utils import log_console_file, get_rfc3339_timestamp


class MQTTStorage:
    def __init__(
            self,
            mqtt_ip: str,
            port: int,
            client_id: str | None,
            topic: str,
            building_name: str,
            room_number: str
    ) -> None:
        self.client_id: str = client_id or f"ESP32S3_{get_rfc3339_timestamp()}"
        self.mqtt_ip: str = mqtt_ip
        self.port: int = port
        self.client: MQTTClient = MQTTClient(self.client_id, self.mqtt_ip, self.port)
        self.topic: str = topic
        self.building_name: str = building_name
        self.room_number: str = room_number
        self.connected = False

    def connect(self):
        try:
            log_console_file(f"trying to connect to mqtt: {self.mqtt_ip}:{self.port}")
            self.client.connect()
            self.connected = True
            log_console_file(f"MQTT client {self.client_id} connected to {self.mqtt_ip}:{self.port}")
        except Exception as err:
            log_console_file(f"MQTT client {self.client_id} connection failed: {err}")

    def save_measurement(self, measurement_data: dict) -> bool:
        payload = measurement_data.copy()
        if "ts" not in payload:
            payload["ts"] = get_rfc3339_timestamp()
        if "sensorId" not in payload:
            payload["sensorId"] = self.client_id
        if "buildingName" not in payload:
            payload["buildingName"] = self.building_name
        if "roomNumber" not in payload:
            payload["roomNumber"] = self.room_number

        for _ in range(3):
            try:
                if not self.connected:
                    self.connect()
                self.client.publish(self.topic, json.dumps(payload))
                log_console_file(f"Published: {payload}")
                return True
            except Exception as e:
                log_console_file(f"Publish failed: {e}")
                self.connected = False
                asyncio.sleep(2)
        return False

    def close(self) -> None:
        if self.client:
            try:
                self.client.disconnect()
            except:
                pass
