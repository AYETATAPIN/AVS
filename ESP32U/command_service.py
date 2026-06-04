import json

from utils import log_console_file


STATE_ACTIVE = "ACTIVE"
STATE_STANDBY_LIGHT_SLEEP = "STANDBY_LIGHT_SLEEP"


class CommandService:
    def __init__(self, monitor: object) -> None:
        self.monitor: object = monitor
        self._handlers: dict = {
            "register": self._handle_register,
            "get_sensors": self._handle_get_sensors,
            "reboot": self._handle_reboot,
            "get_orientation": self._handle_get_orientation,
            "get_version": self._handle_get_version,
            "get_battery": self._handle_get_battery,
            "set_location": self._handle_set_location,
            "enable_fall_detection": self._handle_enable_fall_detection,
            "power_off": self._handle_power_off,
            "power_on": self._handle_power_on,
            "ota_update": self._handle_ota_update,
            "ota_rollback": self._handle_ota_rollback,
            "unbind": self._handle_unbind,
        }

    def handle_mqtt_message(self, topic: object, msg: object) -> None:
        cmd_id = "unknown"
        response_topic = str(self.monitor.response_topic)
        topic_text = topic.decode() if isinstance(topic, bytes) else str(topic)
        self.monitor.sensor_service.set_led(True)

        try:
            raw = msg.decode() if isinstance(msg, bytes) else str(msg)
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("Command payload must be JSON object")

            cmd_id = str(payload.get("command_id", "unknown"))
            cmd = str(payload.get("command", "") or "")
            params = payload.get("parameters", {})
            if not isinstance(params, dict):
                params = {}

            log_console_file(f"Received command {cmd} ({cmd_id})")
            response: dict = {"command_id": cmd_id, "status": "success"}

            handler = self._handlers.get(cmd)
            if handler is None:
                response["status"] = "failed"
                response["data"] = {"error": "Unknown command"}
            else:
                should_stop, response_topic, should_publish = handler(params, response, response_topic, topic_text)
                if should_stop:
                    return
                if not should_publish:
                    return

            response = self.monitor.add_common_response_fields(response)
            self.monitor.safe_publish(response_topic, json.dumps(response))
        except Exception as err:
            log_console_file("MQTT callback error: " + str(err))
            err_resp = {
                "command_id": cmd_id,
                "status": "failed",
                "data": {"error": str(err)},
            }
            err_resp = self.monitor.add_common_response_fields(err_resp)
            self.monitor.safe_publish(response_topic, json.dumps(err_resp))
        finally:
            self.monitor.sensor_service.set_led(False)

    def _is_register_topic(self, topic_text: str) -> bool:
        return topic_text.startswith("devices/register/")

    def _is_broadcast_register_topic(self, topic_text: str) -> bool:
        return topic_text.strip() == "devices/register/broadcast"

    def _normalize_building_value(self, value: object) -> str:
        text = str(value or "").strip().replace("_", " ")
        return self.monitor.location_service.normalize_building(text)

    def _normalize_room_value(self, value: object) -> str:
        text = str(value or "").strip().replace("_", "")
        return self.monitor.location_service.normalize_room(text)

    def _to_bool(self, value: object, default: bool = False) -> bool:
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
            return default
        try:
            return bool(value)
        except Exception:
            return default

    def _register_topic_matches_payload(self, topic_text: str, building: object, room: object) -> bool:
        if self._is_broadcast_register_topic(topic_text):
            return True

        parts = topic_text.split("/")
        if len(parts) < 4:
            return True

        topic_building = parts[2]
        topic_room = parts[3]
        return (
            self._normalize_building_value(topic_building) == self._normalize_building_value(building)
            and self._normalize_room_value(topic_room) == self._normalize_room_value(room)
        )

    def _handle_register(self, params: dict, response: dict, response_topic: str, topic_text: str) -> tuple:
        if not self._is_register_topic(topic_text):
            return False, response_topic, False

        building = (
            params.get("building_name")
            or params.get("building")
            or params.get("buildingName")
        )
        room = (
            params.get("room_number")
            or params.get("room")
            or params.get("roomNumber")
        )
        if not building or not room:
            response["status"] = "failed"
            response["data"] = {"error": "building_name and room_number are required"}
            return False, response_topic, True

        if not self._register_topic_matches_payload(topic_text, building, room):
            log_console_file(
                f"Register ignored: topic does not match payload ({topic_text})"
            )
            return False, response_topic, False

        if self.monitor.is_registered and not self._is_broadcast_register_topic(topic_text):
            log_console_file(
                f"Register ignored: sensor already registered to "
                f"{self.monitor.building_name}/{self.monitor.room_number}"
            )
            return False, response_topic, False

        self.monitor.apply_registration_update(str(building), str(room))
        response["data"] = {
            "message": (
                f"Sensor successfully registered to "
                f"{self.monitor.building_name} {self.monitor.room_number}"
            ),
            "device_id": self.monitor.device_id,
            "saved": True,
            "isRegistered": True,
            "buildingName": self.monitor.building_name,
            "roomNumber": self.monitor.room_number,
        }
        return False, response_topic, True

    def _handle_get_sensors(self, params: dict, response: dict, response_topic: str, topic_text: str) -> tuple:
        sensor_data = self.monitor.publish_sensor_snapshot(publish=self.monitor.is_registered)
        response["data"] = sensor_data
        return False, response_topic, True

    def _handle_reboot(self, params: dict, response: dict, response_topic: str, topic_text: str) -> tuple:
        delay = int(params.get("delay", 3) or 3)
        response["data"] = {"message": f"rebooting in {delay}s"}
        self.monitor.schedule_reset(delay)
        return False, response_topic, True

    def _handle_get_orientation(self, params: dict, response: dict, response_topic: str, topic_text: str) -> tuple:
        ok, data = self.monitor.sensor_service.read_orientation()
        if not ok:
            response["status"] = "failed"
        response["data"] = data
        return False, response_topic, True

    def _handle_get_version(self, params: dict, response: dict, response_topic: str, topic_text: str) -> tuple:
        response["data"] = self.monitor.build_version_payload()
        return False, response_topic, True

    def _handle_get_battery(self, params: dict, response: dict, response_topic: str, topic_text: str) -> tuple:
        battery_data = self.monitor.sensor_service.read_battery_data()
        voltage = self.monitor.sensor_service.get_battery_voltage()
        percentage = self.monitor.sensor_service.get_battery_percentage()
        response["data"] = {
            "battery": voltage if voltage is not None else "unknown",
            "percentage": percentage if percentage is not None else "unknown",
            "current_ma": battery_data.get("current_ma", "unknown"),
            "source": "ina219",
        }
        return False, response_topic, True

    def _handle_set_location(self, params: dict, response: dict, response_topic: str, topic_text: str) -> tuple:
        sensor_id = params.get("sensor_id") or params.get("sensorId")
        building = params.get("building") or params.get("buildingName")
        room = params.get("room") or params.get("roomNumber")
        if not sensor_id or not building or not room:
            response["status"] = "failed"
            response["data"] = {"error": "sensor_id, building and room are required"}
            return False, response_topic, True

        valid, reason = self.monitor.validate_location_payload(str(sensor_id), str(building), str(room))
        if not valid:
            response["status"] = "failed"
            response["data"] = {"error": reason}
            return False, response_topic, True

        old_response_topic = response_topic
        self.monitor.apply_location_update(str(sensor_id), str(building), str(room))
        response_topic = old_response_topic
        response["data"] = {
            "saved": True,
            "sensor_id": self.monitor.device_id,
            "building": self.monitor.building_name,
            "room": self.monitor.room_number,
            "isRegistered": self.monitor.is_registered,
        }
        return False, response_topic, True

    def _handle_enable_fall_detection(self, params: dict, response: dict, response_topic: str, topic_text: str) -> tuple:
        enable = self._to_bool(params.get("enable", False), False)
        try:
            mpu = self.monitor.sensor_service.mpu
            if mpu is not None and hasattr(mpu, "enable_fall_detection"):
                mpu.enable_fall_detection(enable)
                baseline = mpu.get_orientation()
                if hasattr(mpu, "get_fall_detection_state"):
                    state = mpu.get_fall_detection_state()
                else:
                    state = {"enabled": enable}
                state["baseline"] = baseline
                response["data"] = state
            else:
                response["status"] = "failed"
                response["data"] = {"error": "MPU6050 fall detection is unavailable"}
        except Exception as err:
            response["status"] = "failed"
            response["data"] = {"error": str(err)}
        return False, response_topic, True

    def _handle_power_off(self, params: dict, response: dict, response_topic: str, topic_text: str) -> tuple:
        self.monitor.set_state(STATE_STANDBY_LIGHT_SLEEP)
        response["data"] = {
            "message": "Entered standby light sleep",
            "poll_interval_ms": self.monitor.standby_poll_ms,
        }
        return False, response_topic, True

    def _handle_power_on(self, params: dict, response: dict, response_topic: str, topic_text: str) -> tuple:
        self.monitor.set_state(STATE_ACTIVE)
        response["data"] = {"message": "Returned to active mode"}
        return False, response_topic, True

    def _handle_ota_update(self, params: dict, response: dict, response_topic: str, topic_text: str) -> tuple:
        url = str(params.get("url", "") or "")
        sha256 = str(params.get("sha256") or params.get("sha") or "")
        length = int(params.get("length", 0) or 0)

        ok, message = self.monitor.ota_service.save_update_request(url, sha256, length)
        if not ok:
            response["status"] = "failed"
            response["data"] = {"error": message}
            return False, response_topic, True

        response["data"] = {
            "message": message,
            "deferred": True,
            "rebooting": True,
        }
        self.monitor.schedule_reset(2)
        return False, response_topic, True

    def _handle_ota_rollback(self, params: dict, response: dict, response_topic: str, topic_text: str) -> tuple:
        ok, message = self.monitor.ota_service.run_rollback()
        if not ok:
            response["status"] = "failed"
            response["data"] = {"error": message}
            return False, response_topic, True

        response["data"] = {"message": message, "rebooting": True}
        response = self.monitor.add_common_response_fields(response)
        self.monitor.safe_publish(response_topic, json.dumps(response))
        self.monitor.schedule_reset(2)
        self.monitor.sensor_service.set_led(False)
        return True, response_topic, False

    def _handle_unbind(self, params: dict, response: dict, response_topic: str, topic_text: str) -> tuple:
        self.monitor.apply_unbind()
        response["data"] = {
            "message": "Sensor successfully unbound",
            "saved": True,
            "isRegistered": False,
        }
        return False, response_topic, True
