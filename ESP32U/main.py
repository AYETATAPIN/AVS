import gc
import json
import machine
import sys
import ubinascii
import uasyncio as asyncio
import utime as time

from utils import CONFIG_FILE, get_rfc3339_timestamp, log_console_file
from wifi_service import WiFiService

try:
    import esp
except ImportError:
    esp = None


STATE_INIT = "INIT"
STATE_ACTIVE = "ACTIVE"
STATE_STANDBY_LIGHT_SLEEP = "STANDBY_LIGHT_SLEEP"
REGISTER_TOPIC = "devices/register/#"


class EnvironmentalMonitor:
    def __init__(self) -> None:
        log_console_file("=== ESP32 STARTING ===")
        self.state: str = STATE_INIT

        self.config: dict = self._load_config()
        self.location_service = None

        self._load_runtime_location_from_config()
        self._read_runtime_tuning()
        self.next_sensor_publish_ms: int = 0

        gc.collect()
        try:
            log_console_file("Free heap before Wi-Fi init: " + str(gc.mem_free()))
        except Exception:
            pass
        self.wifi = WiFiService(self.config)
        self.mqtt_storage = None
        self.mqtt_profile_name: str = ""
        self.sensor_service = None
        self.ota_service = None
        self.command_service = None

    def _ensure_location_service(self) -> object:
        if self.location_service is not None:
            return self.location_service
        from location_service import LocationService
        self.location_service = LocationService(self.config)
        return self.location_service

    def _ensure_ota_service(self) -> object:
        if self.ota_service is not None:
            return self.ota_service
        from ota_service import OTAService
        self.ota_service = OTAService()
        self.ota_service.cancel_pending_rollback()
        return self.ota_service

    def _ensure_command_service(self) -> object:
        if self.command_service is not None:
            return self.command_service
        from command_service import CommandService
        self.command_service = CommandService(self)
        return self.command_service

    def _ensure_sensor_service(self) -> object:
        if self.sensor_service is not None:
            return self.sensor_service
        gc.collect()
        try:
            log_console_file("Free heap before sensor init: " + str(gc.mem_free()))
        except Exception:
            pass
        from sensor_service import SensorService
        self.sensor_service = SensorService(self.config, self.config.get("CALIBRATION", {}))
        gc.collect()
        try:
            log_console_file("Free heap after sensor init: " + str(gc.mem_free()))
        except Exception:
            pass
        return self.sensor_service

    def _ensure_mqtt_storage(self) -> object:
        mqtt_cfg, profile_name = self._resolve_mqtt_config()
        if self.mqtt_storage is not None:
            if profile_name == self.mqtt_profile_name:
                return self.mqtt_storage
            try:
                self.mqtt_storage.disconnect()
            except Exception:
                pass
            self.mqtt_storage = None
            log_console_file("MQTT profile changed to " + profile_name)
        self._ensure_command_service()
        self.mqtt_storage = self._init_mqtt_storage(mqtt_cfg, profile_name)
        self.mqtt_profile_name = profile_name
        return self.mqtt_storage

    def _ensure_runtime_services(self) -> None:
        self._ensure_location_service()
        self._ensure_ota_service()
        self._ensure_command_service()
        self._ensure_mqtt_storage()

    def _run_pending_ota_request(self) -> bool:
        ota_service = self._ensure_ota_service()
        request = ota_service.load_update_request()
        if not request:
            return False

        url = str(request.get("url", "") or "")
        sha256 = str(request.get("sha256", "") or "")
        length = int(request.get("length", 0) or 0)

        log_console_file("Pending OTA request found; running before MQTT and sensors")
        ok, message = ota_service.run_update(url, sha256, length)
        ota_service.clear_update_request()

        if not ok:
            log_console_file("Pending OTA failed; continuing normal boot: " + str(message))
            return False

        log_console_file("Pending OTA staged successfully; rebooting into update slot")
        machine.reset()
        return True

    def _load_config(self) -> dict:
        log_console_file("Reading config file: " + CONFIG_FILE)
        try:
            with open(CONFIG_FILE, "r") as file_obj:
                data = json.load(file_obj)
            if not isinstance(data, dict):
                raise ValueError("config root must be object")
            log_console_file("Config loaded successfully")
            return data
        except Exception as err:
            log_console_file("Failed to load config: " + str(err))
            machine.reset()
            return {}

    def _save_config(self) -> None:
        try:
            with open(CONFIG_FILE, "w") as file_obj:
                json.dump(self.config, file_obj)
        except Exception as err:
            log_console_file("Config save failed: " + str(err))

    def _default_device_id(self) -> str:
        try:
            return "esp32_" + ubinascii.hexlify(machine.unique_id()).decode()
        except Exception:
            return "esp32_unknown"

    def _to_bool(self, value: object, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        if isinstance(value, str):
            text = value.strip().lower()
            if text in ("1", "true", "yes", "y", "on"):
                return True
            if text in ("0", "false", "no", "n", "off"):
                return False
        try:
            return bool(value)
        except Exception:
            return default

    def _read_registered_flag(self, location_cfg: dict) -> bool:
        if "isRegistered" in location_cfg:
            return self._to_bool(location_cfg.get("isRegistered"), False)
        building = str(location_cfg.get("buildingName") or "").strip()
        room = str(location_cfg.get("roomNumber") or "").strip()
        return bool(building and room)

    def _load_runtime_location_from_config(self) -> None:
        mqtt_cfg = self.config.get("MQTT", {})
        location_cfg = self.config.get("DEVICE_LOCATION", {})

        self.device_id: str = str(mqtt_cfg.get("sensor_id") or self._default_device_id())
        self.building_name: str = str(location_cfg.get("buildingName") or "")
        self.room_number: str = str(location_cfg.get("roomNumber") or "")
        self.is_registered: bool = self._read_registered_flag(location_cfg)
        self._build_topics()

    def _build_topics(self) -> None:
        self.data_topic: str = f"sensors/{self.device_id}/data"
        self.commands_topic: str = f"devices/{self.device_id}/commands"
        if self.building_name and self.room_number:
            building_topic = self._topic_segment(self.building_name)
            room_topic = self._topic_segment(self.room_number)
            self.register_room_topic: str = f"devices/register/{building_topic}/{room_topic}"
        else:
            self.register_room_topic = REGISTER_TOPIC
        self.register_topic: str = REGISTER_TOPIC
        self.response_topic: str = f"devices/{self.device_id}/response"
        self.command_topics: list = [self.commands_topic, self.register_topic]

    def _topic_segment(self, value: object) -> str:
        text = str(value or "").strip().replace("/", "_")
        if not text:
            return "unknown"
        return text

    def _read_runtime_tuning(self) -> None:
        power_cfg = self.config.get("POWER", {})
        self.active_poll_ms: int = max(50, int(power_cfg.get("active_poll_ms", 200)))
        self.standby_poll_ms: int = max(500, int(power_cfg.get("standby_poll_ms", 5000)))
        self.snapshot_interval_sec: int = max(1, int(power_cfg.get("snapshot_interval_sec", 10)))
        self.snapshot_interval_ms: int = int(self.snapshot_interval_sec * 1000)

    def _resolve_mqtt_config(self) -> tuple:
        base_cfg = self.config.get("MQTT", {})
        if not isinstance(base_cfg, dict):
            base_cfg = {}

        resolved = {}
        for key, value in base_cfg.items():
            if key not in ("profiles", "profile_by_wifi", "active_profile"):
                resolved[key] = value

        selected = str(base_cfg.get("active_profile", "auto") or "auto").strip()
        if selected == "auto":
            wifi_profile = str(getattr(self.wifi, "connected_profile_name", "") or "").strip()
            profile_by_wifi = base_cfg.get("profile_by_wifi", {})
            if isinstance(profile_by_wifi, dict):
                selected = str(profile_by_wifi.get(wifi_profile, "") or "").strip()

        profiles = base_cfg.get("profiles", {})
        if selected and selected != "auto" and isinstance(profiles, dict):
            profile_cfg = profiles.get(selected)
            if isinstance(profile_cfg, dict):
                for key, value in profile_cfg.items():
                    resolved[key] = value

        if not selected or selected == "auto":
            selected = "default"

        return resolved, selected

    def _init_mqtt_storage(self, mqtt_cfg: dict, profile_name: str) -> object:
        from storages.mqtt_storage import MQTTStorage
        host = str(mqtt_cfg.get("host") or mqtt_cfg.get("ip") or "127.0.0.1")
        ssl_cfg = mqtt_cfg.get("SSL", {})
        use_ssl = bool(ssl_cfg.get("enabled", mqtt_cfg.get("use_ssl", False)))
        ssl_params = {}
        server_hostname = str(ssl_cfg.get("server_hostname", "") or "").strip()
        if server_hostname:
            ssl_params["server_hostname"] = server_hostname

        log_console_file(
            f"MQTT profile selected={profile_name}, host={host}, "
            f"port={int(mqtt_cfg.get('port', 8883 if use_ssl else 1883))}, ssl={use_ssl}"
        )

        storage = MQTTStorage(
            mqtt_host=host,
            port=int(mqtt_cfg.get("port", 8883 if use_ssl else 1883)),
            client_id=self.device_id,
            data_topic=self.data_topic,
            building_name=self.building_name,
            room_number=self.room_number,
            commands_topic=self.commands_topic,
            response_topic=self.response_topic,
            username=str(mqtt_cfg.get("username", "") or ""),
            password=str(mqtt_cfg.get("password", "") or ""),
            keepalive_sec=int(mqtt_cfg.get("keepalive_sec", 60)),
            use_ssl=use_ssl,
            ssl_params=ssl_params,
            connect_timeout_sec=int(mqtt_cfg.get("connect_timeout_sec", 8)),
        )
        storage.set_callback(self.mqtt_callback)
        return storage

    def _refresh_mqtt_runtime(self) -> None:
        mqtt_storage = self._ensure_mqtt_storage()
        self.mqtt_storage.configure_identity(self.device_id)
        mqtt_storage.configure_topics(
            self.data_topic,
            self.commands_topic,
            self.response_topic,
            extra_command_topics=[self.register_topic],
        )
        mqtt_storage.building_name = self.building_name
        mqtt_storage.room_number = self.room_number

    def _connect_mqtt(self) -> bool:
        self._ensure_mqtt_storage()
        self._refresh_mqtt_runtime()
        return self.mqtt_storage.connect()

    def _ensure_mqtt_connected(self) -> bool:
        self._ensure_mqtt_storage()
        self._refresh_mqtt_runtime()
        return self.mqtt_storage.ensure_connected()

    def _poll_mqtt(self) -> None:
        self._ensure_mqtt_storage()
        self.mqtt_storage.check_messages()

    def _ensure_wifi_connected(self) -> bool:
        return self.wifi.ensure_connected()

    def get_wifi_signal(self) -> int:
        return self.wifi.get_rssi()

    def safe_publish(self, topic: str, payload: str) -> bool:
        self._ensure_mqtt_storage()
        return self.mqtt_storage.publish(topic, payload, retries=2)

    def set_state(self, new_state: str) -> None:
        if self.state == new_state:
            return
        log_console_file(f"State change: {self.state} -> {new_state}")
        self.state = new_state
        if new_state == STATE_ACTIVE:
            self.wifi.configure_pm(standby=False)
            self.next_sensor_publish_ms = time.ticks_add(time.ticks_ms(), self.snapshot_interval_ms)
        elif new_state == STATE_STANDBY_LIGHT_SLEEP:
            self.wifi.configure_pm(standby=True)

    async def _delayed_hard_reset(self, seconds: int) -> None:
        await asyncio.sleep(seconds)
        machine.reset()

    def schedule_reset(self, seconds: int) -> None:
        asyncio.create_task(self._delayed_hard_reset(int(seconds)))

    def add_common_response_fields(self, response: dict) -> dict:
        firmware_version = self.config.get("FIRMWARE", {}).get("version")
        response["firmware_version"] = firmware_version if firmware_version else sys.version
        response["wifi_signal"] = self.get_wifi_signal()
        response["power_state"] = self.state
        response["isRegistered"] = self.is_registered

        try:
            sensor_service = self._ensure_sensor_service()
            battery_data = sensor_service.read_battery_data()
            battery = battery_data.get("battery")
            if battery is not None:
                response["battery"] = battery
            if "current_ma" in battery_data:
                response["current_ma"] = battery_data["current_ma"]
            battery_pct = sensor_service.get_battery_percentage()
            if battery_pct is not None:
                response["battery_pct"] = battery_pct
        except Exception as err:
            log_console_file("Battery fields skipped: " + str(err))
        return response

    def build_version_payload(self) -> dict:
        flash_size = "unknown"
        if esp is not None and hasattr(esp, "flash_size"):
            try:
                flash_size = esp.flash_size()
            except Exception:
                flash_size = "unknown"

        return {
            "firmware_version": self.config.get("FIRMWARE", {}).get("version", sys.version),
            "platform": sys.platform,
            "chip": "ESP32",
            "flash_size": flash_size,
            "ota_module": self._ensure_ota_service().has_update_module,
            "eduroam_api": self.wifi.supports_eduroam(),
        }

    def validate_location_payload(self, sensor_id: str, building: str, room: str) -> tuple:
        return self._ensure_location_service().validate_location(sensor_id, building, room)

    def apply_location_update(self, sensor_id: str, building: str, room: str) -> None:
        building_code = self._ensure_location_service().building_to_code(building)

        self.config.setdefault("MQTT", {})
        self.config.setdefault("DEVICE_LOCATION", {})
        self.config["MQTT"]["sensor_id"] = sensor_id
        self.config["DEVICE_LOCATION"]["buildingName"] = building_code
        self.config["DEVICE_LOCATION"]["roomNumber"] = str(room)
        self.config["DEVICE_LOCATION"]["isRegistered"] = True
        self._save_config()

        self.device_id = str(sensor_id)
        self.building_name = str(building_code)
        self.room_number = str(room)
        self.is_registered = True
        self._build_topics()

        log_console_file(
            f"Location updated to sensor={self.device_id}, "
            f"building={self.building_name}, room={self.room_number}"
        )
        self._connect_mqtt()

    def apply_registration_update(self, building: str, room: str) -> None:
        building_code = self._ensure_location_service().building_to_code(building)

        self.config.setdefault("DEVICE_LOCATION", {})
        self.config["DEVICE_LOCATION"]["buildingName"] = str(building_code)
        self.config["DEVICE_LOCATION"]["roomNumber"] = str(room)
        self.config["DEVICE_LOCATION"]["isRegistered"] = True
        self._save_config()

        self.building_name = str(building_code)
        self.room_number = str(room)
        self.is_registered = True
        self._build_topics()
        log_console_file(
            f"Registration updated location to "
            f"building={self.building_name}, room={self.room_number}"
        )
        self._connect_mqtt()

    def apply_unbind(self) -> None:
        self.config.setdefault("DEVICE_LOCATION", {})
        self.config["DEVICE_LOCATION"]["buildingName"] = ""
        self.config["DEVICE_LOCATION"]["roomNumber"] = ""
        self.config["DEVICE_LOCATION"]["isRegistered"] = False
        self._save_config()

        self.building_name = ""
        self.room_number = ""
        self.is_registered = False
        self._build_topics()
        log_console_file("Sensor unbound; telemetry disabled until registration")
        self._connect_mqtt()

    def publish_sensor_snapshot(self, publish: bool = True) -> dict:
        sensor_service = self._ensure_sensor_service()
        sensor_data = sensor_service.read_all_sensors()
        payload = {
            "sensorId": self.device_id,
            "buildingName": self.building_name,
            "roomNumber": self.room_number,
            "ts": get_rfc3339_timestamp(),
        }
        payload.update(sensor_data)
        try:
            log_console_file("Sensor payload -> " + json.dumps(payload))
        except Exception:
            log_console_file("Sensor payload -> " + str(payload))

        if publish and not self.is_registered:
            log_console_file("Sensor snapshot not published: sensor is not registered")
            return sensor_data

        if not publish:
            log_console_file("Sensor snapshot read without MQTT publish")
            return sensor_data

        if self.mqtt_storage.save_measurement(payload):
            log_console_file("Sensor snapshot published to " + self.data_topic)
        else:
            log_console_file("Sensor snapshot publish failed")
        return sensor_data

    def mqtt_callback(self, topic: object, msg: object) -> None:
        self._ensure_command_service()
        self.command_service.handle_mqtt_message(topic, msg)

    async def active_loop(self) -> None:
        while True:
            if self.state != STATE_ACTIVE:
                await asyncio.sleep_ms(200)
                continue

            if self._ensure_wifi_connected() and self._ensure_mqtt_connected():
                self._poll_mqtt()
                now_ms = time.ticks_ms()
                if self.is_registered and (
                    self.next_sensor_publish_ms == 0
                    or time.ticks_diff(now_ms, self.next_sensor_publish_ms) >= 0
                ):
                    self.publish_sensor_snapshot()
                    self.next_sensor_publish_ms = time.ticks_add(now_ms, self.snapshot_interval_ms)

            await asyncio.sleep_ms(self.active_poll_ms)

    async def standby_loop(self) -> None:
        while True:
            if self.state != STATE_STANDBY_LIGHT_SLEEP:
                await asyncio.sleep_ms(200)
                continue

            if self._ensure_wifi_connected():
                self._ensure_mqtt_connected()
                self._poll_mqtt()

            if self.state == STATE_STANDBY_LIGHT_SLEEP:
                try:
                    machine.lightsleep(self.standby_poll_ms)
                except Exception as err:
                    log_console_file("lightsleep failed: " + str(err))
                    await asyncio.sleep_ms(self.standby_poll_ms)

            await asyncio.sleep_ms(0)

    async def run(self) -> None:
        if not self._ensure_wifi_connected():
            log_console_file("Wi-Fi not connected on boot, restarting")
            machine.reset()

        if self._run_pending_ota_request():
            while True:
                await asyncio.sleep(1)

        self._ensure_runtime_services()

        log_console_file("Wi-Fi ready, connecting MQTT...")
        if not self._ensure_mqtt_connected():
            log_console_file("MQTT not connected on boot, restarting")
            machine.reset()

        self._ensure_sensor_service()
        self.set_state(STATE_ACTIVE)
        if self.is_registered:
            self.publish_sensor_snapshot()
        else:
            log_console_file("Telemetry disabled: sensor is not registered")
        self.next_sensor_publish_ms = time.ticks_add(time.ticks_ms(), self.snapshot_interval_ms)

        asyncio.create_task(self.active_loop())
        asyncio.create_task(self.standby_loop())

        while True:
            gc.collect()
            await asyncio.sleep(1)


async def main() -> None:
    monitor = EnvironmentalMonitor()
    await monitor.run()


if __name__ == "__main__":
    asyncio.run(main())
