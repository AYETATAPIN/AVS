import json
import utime as time

from umqtt.robust import MQTTClient

from utils import get_rfc3339_timestamp, log_console_file

try:
    import usocket as socket
except ImportError:
    try:
        import socket
    except ImportError:
        socket = None


class MQTTStorage:
    def __init__(
        self,
        mqtt_host: str,
        port: int,
        client_id: str,
        data_topic: str = "",
        building_name: str = "",
        room_number: str = "",
        commands_topic: str = "",
        response_topic: str = "",
        username: str = "",
        password: str = "",
        keepalive_sec: int = 60,
        use_ssl: bool = False,
        ssl_params: dict = None,
        connect_timeout_sec: int = 8,
    ) -> None:
        self.client_id: str = str(client_id or ("esp32_" + get_rfc3339_timestamp()))
        self.mqtt_host: str = str(mqtt_host)
        self.port: int = int(port)
        self.username: str = str(username or "")
        self.password: str = str(password or "")
        self.keepalive_sec: int = int(keepalive_sec)
        self.use_ssl: bool = bool(use_ssl)
        self.ssl_params: dict = ssl_params or {}
        self.connect_timeout_sec: int = max(2, int(connect_timeout_sec))

        self.data_topic: str = str(data_topic or "")
        self.building_name: str = str(building_name or "")
        self.room_number: str = str(room_number or "")
        self.commands_topic: str = str(commands_topic or "")
        self.command_topics: list = []
        self.response_topic: str = str(response_topic or "")
        self._set_command_topics(self.commands_topic, [])

        self._client: object = None
        self._callback: object = None
        self.connected: bool = False

    def configure_identity(self, client_id: str) -> None:
        new_id = str(client_id or "").strip()
        if not new_id or new_id == self.client_id:
            return
        self.client_id = new_id
        self.disconnect()

    def _set_command_topics(self, commands_topic: str, extra_command_topics: list) -> None:
        topics: list = []
        base = str(commands_topic or "").strip()
        if base:
            topics.append(base)
        for item in extra_command_topics or []:
            topic = str(item or "").strip()
            if topic and topic not in topics:
                topics.append(topic)
        self.commands_topic = base
        self.command_topics = topics

    def configure_topics(
        self,
        data_topic: str,
        commands_topic: str,
        response_topic: str,
        extra_command_topics: list = None,
    ) -> None:
        self.data_topic = str(data_topic or "")
        self.response_topic = str(response_topic or "")
        self._set_command_topics(commands_topic, extra_command_topics or [])

    def set_callback(self, callback: object) -> None:
        self._callback = callback
        if self._client is not None:
            try:
                self._client.set_callback(callback)
            except Exception as err:
                log_console_file("MQTT set_callback failed: " + str(err))

    def _make_client(self) -> object:
        user = self.username if self.username else None
        password = self.password if self.password else None
        return MQTTClient(
            client_id=self.client_id,
            server=self.mqtt_host,
            port=self.port,
            user=user,
            password=password,
            keepalive=self.keepalive_sec,
            ssl=self.use_ssl,
            ssl_params=self.ssl_params,
        )

    def connect(self) -> bool:
        self.disconnect()
        try:
            log_console_file(
                f"MQTT connect start: host={self.mqtt_host} "
                f"port={self.port} ssl={self.use_ssl} "
                f"timeout={self.connect_timeout_sec}s"
            )
            if socket is not None and hasattr(socket, "setdefaulttimeout"):
                try:
                    socket.setdefaulttimeout(self.connect_timeout_sec)
                except Exception:
                    pass

            self._client = self._make_client()
            if self._callback is not None:
                self._client.set_callback(self._callback)
            log_console_file("MQTT low-level connect()...")
            self._client.connect()
            log_console_file("MQTT low-level connect() done")

            for topic in self.command_topics:
                self._client.subscribe(topic)
                log_console_file("MQTT subscribed " + topic)

            self.connected = True
            log_console_file(
                f"MQTT connected: {self.mqtt_host}:{self.port} "
                f"as {self.client_id} (ssl={self.use_ssl})"
            )
            return True
        except Exception as err:
            self.connected = False
            log_console_file("MQTT connect failed: " + str(err))
            return False
        finally:
            if socket is not None and hasattr(socket, "setdefaulttimeout"):
                try:
                    socket.setdefaulttimeout(None)
                except Exception:
                    pass

    def ensure_connected(self) -> bool:
        if self._client is not None and self.connected:
            return True
        return self.connect()

    def check_messages(self) -> bool:
        if self._client is None:
            return False
        try:
            self._client.check_msg()
            return True
        except Exception as err:
            self.connected = False
            log_console_file("MQTT poll error: " + str(err))
            return False

    def publish(self, topic: str, payload: object, retries: int = 2) -> bool:
        topic_text = str(topic or "")
        if not topic_text:
            return False
        payload_out = payload

        for _ in range(max(1, int(retries))):
            if not self.ensure_connected():
                self._retry_pause()
                continue
            try:
                self._client.publish(topic_text, payload_out)
                return True
            except Exception as err:
                self.connected = False
                log_console_file("MQTT publish error: " + str(err))
                self._retry_pause()
        return False

    def publish_json(self, topic: str, payload: dict, retries: int = 2) -> bool:
        try:
            data = json.dumps(payload)
        except Exception as err:
            log_console_file("MQTT json encode failed: " + str(err))
            return False
        return self.publish(topic, data, retries=retries)

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
        return self.publish_json(self.data_topic, payload, retries=3)

    def _retry_pause(self) -> None:
        try:
            time.sleep_ms(300)
        except Exception:
            pass

    def disconnect(self) -> None:
        if self._client is not None:
            try:
                self._client.disconnect()
            except Exception:
                pass
        self._client = None
        self.connected = False

    def close(self) -> None:
        self.disconnect()
