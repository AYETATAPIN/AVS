import json
import os
import random
import ssl
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from itertools import cycle

import paho.mqtt.client as mqtt
from locust import HttpUser, User, between, task

if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.strip().split("=", 1)
                os.environ.setdefault(key, value)

MQTT_HOST = "nsu-metrics.ru"
MQTT_PORT = 8883
MQTT_USER = os.environ["MQTT_USERNAME"]
MQTT_PASS = os.environ["MQTT_PASSWORD"]
MQTT_KEEPALIVE = 180
MQTT_TIMEOUT = 10
MQTT_QOS = 1
HTTP_HOST = "https://nsu-metrics.ru"
HTTP_TIMEOUT = 120

# Sensors backed by real hardware — locust must NOT impersonate them,
# иначе фейковые публикации затрут реальные показания в "current".
REAL_SENSORS: set[str] = {"sensor_631"}  # ESP32, аудитория 2128

@dataclass(frozen=True)
class Sensor:
    id: str
    index: int
    room: str
    building: str

def load_sensors() -> list[Sensor]:
    sensors = []
    with open("ingest-go/mapping_eng.txt", "r", encoding="utf-8") as f:
        for line in filter(str.strip, f):
            s_id, room, bld = (p.strip() for p in line.split("|"))
            if s_id in REAL_SENSORS:
                continue
            sensors.append(Sensor(s_id, int(s_id.split("_")[1]), room, bld))
    return sensors

SENSORS = load_sensors()
SENSOR_CYCLE = cycle(SENSORS)
MQTT_USERS_FIXED = len(SENSORS)

STATIC_ASSETS = [
    "/style.css",
    "/js/imdf-parser.js",
    "/js/sensor-api.js",
    "/js/campus-map.js",
    "/js/charts.js",
    "/js/app.js",
    "/imdf-data/address.geojson",
    "/imdf-data/building.geojson",
    "/imdf-data/footprint.geojson",
    "/imdf-data/level.geojson",
    "/imdf-data/opening.geojson",
    "/imdf-data/venue.geojson",
    "/imdf-data/manifest.json",
]


class MqttSensorUser(User):
    fixed_count = MQTT_USERS_FIXED
    wait_time = between(0.5, 1.5)

    def __init__(self, environment):
        super().__init__(environment)
        self.sensor = next(SENSOR_CYCLE)
        self.is_connected = False
        self.next_publish_at = 0.0

        client_id = f"avs-locust-{self.sensor.id}-{uuid.uuid4().hex[:6]}"
    
        try:
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        except AttributeError:
            self.mqtt_client = mqtt.Client(client_id=client_id)

        self.mqtt_client.username_pw_set(MQTT_USER, MQTT_PASS)
        
        ctx = ssl.create_default_context()
        ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
        self.mqtt_client.tls_set_context(ctx)
        self.mqtt_client.reconnect_delay_set(1.5, 15.0)
        self.mqtt_client.on_connect = lambda c, u, f, rc, *_: setattr(self, "is_connected", getattr(rc, "value", rc) == 0)
        self.mqtt_client.on_disconnect = lambda c, u, *_: setattr(self, "is_connected", False)

    def on_start(self):
        time.sleep(random.uniform(0.0, 60.0))
        start_ts = time.perf_counter()
        try:
            self.mqtt_client.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEPALIVE)
            self.mqtt_client.loop_start()
            self._log_event("CONNECT", start_ts)
            self.next_publish_at = time.time() + random.uniform(0.0, 5.0)
        except Exception as e:
            self._log_event("CONNECT", start_ts, exc=e)

    def on_stop(self):
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()

    @task
    def publish_loop(self):
        now = time.time()
        if now >= self.next_publish_at:
            self.publish_data()
            self.next_publish_at = now + random.uniform(48.0, 72.0)

    def publish_data(self):
        if not self.is_connected:
            return

        topic = f"sensors/{self.sensor.index}/data"
        payload = json.dumps({
            "sensorId": self.sensor.id,
            "buildingName": self.sensor.building,
            "roomNumber": self.sensor.room,
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "co2": random.randint(450, 1800),
            "temperature": random.randint(17, 30),
            "humidity": random.randint(25, 75),
        }, separators=(",", ":")).encode("utf-8")

        start_ts = time.perf_counter()
        try:
            msg = self.mqtt_client.publish(topic, payload, qos=MQTT_QOS)
            msg.wait_for_publish(timeout=MQTT_TIMEOUT)
            
            exc = None if msg.is_published() else TimeoutError("PUBACK timeout")
            self._log_event("PUBLISH", start_ts, len(payload), exc, topic)
        except Exception as e:
            self._log_event("PUBLISH", start_ts, len(payload), e, topic)

    def _log_event(self, kind: str, start_ts: float, length: int = 0, exc: Exception = None, name: str = None):
        self.environment.events.request.fire(
            request_type=f"MQTT-{kind}",
            name=name or kind,
            response_time=(time.perf_counter() - start_ts) * 1000,
            response_length=length,
            exception=exc,
            context={"sensor_id": self.sensor.id},
        )


class WebHttpUser(HttpUser):
    weight = 1
    host = HTTP_HOST
    wait_time = between(0.7, 2.0)

    def on_start(self):
        self.client.verify = False

    @task
    def mixed_web_load(self):
        roll = random.random()
        if roll < 0.25:
            self.fetch_frontend_bundle()
        elif roll < 0.80:
            self.fetch_current_data()
        else:
            self.fetch_sensor_history()

    def fetch_frontend_bundle(self):
        self.client.get("/", name="GET /", timeout=HTTP_TIMEOUT)
        for path in STATIC_ASSETS:
            self.client.get(path, name="GET static", timeout=HTTP_TIMEOUT)

    def fetch_current_data(self):
        self.client.get("/api/sensors/current", name="GET /api/sensors/current", timeout=HTTP_TIMEOUT)

    def fetch_sensor_history(self):
        sensor = random.choice(SENSORS).id
        to_ts = datetime.now(timezone.utc)
        from_ts = to_ts - timedelta(hours=24)
        self.client.get(
            f"/api/sensors/{sensor}/history/aggregated",
            params={
                "from": from_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "to": to_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "intervalSeconds": 3600,
            },
            name="GET /api/sensors/:sensor/history/aggregated",
            timeout=HTTP_TIMEOUT,
        )