import machine
import utime as time

from utils import log_console_file


class SensorService:
    def __init__(self, config: dict, calibration_cfg: dict) -> None:
        self.config: dict = config

        self.calibration_enabled: bool = True
        self.calibration_guard_enabled: bool = True
        self.mq135_rzero: float = 65.7
        self.mq135_min_ppm: int = 350
        self.mq135_max_ppm: int = 5000
        self.mq135_samples: int = 5
        self.mq135_sample_delay_ms: int = 120
        self.mq135_use_th_correction: bool = True
        self.dht_temp_a: float = 1.0
        self.dht_temp_b: float = 0.0
        self.dht_hum_a: float = 1.0
        self.dht_hum_b: float = 0.0
        self.include_sensor_diagnostics: bool = False

        self.led = self._init_led()
        self.dht11 = self._init_dht11()
        self.mq135 = self._init_mq135()
        self.ina = self._init_ina219()
        self.mpu = self._init_mpu6050()

        self.set_calibration(calibration_cfg)

    def _to_float(self, value: object, default: float) -> float:
        try:
            return float(value)
        except Exception:
            return float(default)

    def _to_bool(self, value: object, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            text = value.strip().lower()
            if text in ("1", "true", "yes", "y", "on"):
                return True
            if text in ("0", "false", "no", "n", "off"):
                return False
        if value is None:
            return default
        try:
            return bool(value)
        except Exception:
            return default

    def set_calibration(self, calibration_cfg: dict) -> None:
        self.calibration_enabled = self._to_bool(calibration_cfg.get("enabled", True), True)
        self.calibration_guard_enabled = self._to_bool(calibration_cfg.get("guard_invalid", True), True)
        self.mq135_rzero = self._to_float(calibration_cfg.get("mq135_rzero"), 65.7)
        self.mq135_min_ppm = int(calibration_cfg.get("mq135_min_ppm", 350) or 350)
        self.mq135_max_ppm = int(calibration_cfg.get("mq135_max_ppm", 5000) or 5000)
        self.mq135_samples = int(calibration_cfg.get("mq135_samples", 5) or 5)
        if self.mq135_samples < 1:
            self.mq135_samples = 1
        if self.mq135_samples > 10:
            self.mq135_samples = 10
        self.mq135_sample_delay_ms = int(calibration_cfg.get("mq135_sample_delay_ms", 120) or 120)
        if self.mq135_sample_delay_ms < 0:
            self.mq135_sample_delay_ms = 0
        self.mq135_use_th_correction = self._to_bool(calibration_cfg.get("mq135_use_th_correction", True), True)
        self.dht_temp_a = self._to_float(calibration_cfg.get("dht_temp_a"), 1.0)
        self.dht_temp_b = self._to_float(calibration_cfg.get("dht_temp_b"), 0.0)
        self.dht_hum_a = self._to_float(calibration_cfg.get("dht_hum_a"), 1.0)
        self.dht_hum_b = self._to_float(calibration_cfg.get("dht_hum_b"), 0.0)
        self.include_sensor_diagnostics = self._to_bool(calibration_cfg.get("include_diagnostics", False), False)

        if self.calibration_guard_enabled:
            self.dht_temp_a, self.dht_temp_b = self._sanitize_linear_coefficients(
                "temp",
                self.dht_temp_a,
                self.dht_temp_b,
                raw_min=-10.0,
                raw_max=60.0,
                out_min=-30.0,
                out_max=80.0,
            )
            self.dht_hum_a, self.dht_hum_b = self._sanitize_linear_coefficients(
                "hum",
                self.dht_hum_a,
                self.dht_hum_b,
                raw_min=0.0,
                raw_max=100.0,
                out_min=0.0,
                out_max=100.0,
            )

        if self.mq135 is not None and self.calibration_enabled:
            try:
                self.mq135.set_rzero(self.mq135_rzero)
            except Exception as err:
                log_console_file("MQ135 RZERO apply failed: " + str(err))
        if self.mq135 is not None:
            try:
                self.mq135.set_ppm_limits(self.mq135_min_ppm, self.mq135_max_ppm)
            except Exception as err:
                log_console_file("MQ135 PPM limits apply failed: " + str(err))

        log_console_file(
            f"Calibration applied: enabled={self.calibration_enabled}, "
            f"guard={self.calibration_guard_enabled}, RZERO={self.mq135_rzero}, "
            f"ppm=[{self.mq135_min_ppm},{self.mq135_max_ppm}], "
            f"temp=({self.dht_temp_a},{self.dht_temp_b}), "
            f"hum=({self.dht_hum_a},{self.dht_hum_b}), "
            f"diagnostics={self.include_sensor_diagnostics}"
        )
        log_console_file(
            f"MQ135 sampling: samples={self.mq135_samples}, "
            f"delay_ms={self.mq135_sample_delay_ms}, "
            f"th_correction={self.mq135_use_th_correction}"
        )

    def _median(self, values: list) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        mid = len(sorted_vals) // 2
        if len(sorted_vals) % 2 == 1:
            return float(sorted_vals[mid])
        return float(sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0

    def _read_mq135_aggregated(self, temp: float, hum: float) -> dict:
        if self.mq135 is None:
            return {}

        samples: list = []
        for i in range(self.mq135_samples):
            try:
                sample = self._read_single_mq135_sample(temp, hum)
                samples.append(sample)
            except Exception as err:
                log_console_file(f"MQ135 sample {i + 1} failed: {err}")
            if i + 1 < self.mq135_samples and self.mq135_sample_delay_ms > 0:
                time.sleep_ms(self.mq135_sample_delay_ms)

        if not samples:
            log_console_file("MQ135: no valid samples, returning 0")
            return {"co2": 0}

        co2_values = [int(s.get("co2", 0)) for s in samples if "co2" in s]
        if not co2_values:
            log_console_file("MQ135: samples without co2, returning 0")
            return {"co2": 0}

        co2_median = int(round(self._median(co2_values)))
        out = {"co2": co2_median}

        if self.include_sensor_diagnostics:
            raw_values = [int(s.get("mq_raw_adc", 0)) for s in samples if "mq_raw_adc" in s]
            rs_values = [float(s.get("mq_rs", 0.0)) for s in samples if "mq_rs" in s]
            rs_corr_values = [float(s.get("mq_rs_corr", 0.0)) for s in samples if "mq_rs_corr" in s]
            ratio_values = [float(s.get("mq_ratio", 0.0)) for s in samples if "mq_ratio" in s]

            if raw_values:
                out["mq_raw_adc"] = int(round(self._median(raw_values)))
            if rs_values:
                out["mq_rs"] = float(self._median(rs_values))
            if rs_corr_values:
                out["mq_rs_corr"] = float(self._median(rs_corr_values))
            if ratio_values:
                out["mq_ratio"] = float(self._median(ratio_values))
            out["read_ok"] = True
            out["mq_samples"] = len(samples)

        log_console_file(
            f"MQ135 median -> co2={co2_median} ppm from "
            f"{len(samples)}/{self.mq135_samples} samples "
            f"(th_correction={self.mq135_use_th_correction})"
        )
        return out

    def _read_single_mq135_sample(self, temp: float, hum: float) -> dict:
        if self.mq135_use_th_correction:
            return self.mq135.measure_co2_diagnostics(temp, hum)

        raw = self.mq135.read_raw_adc()
        rs = self.mq135.get_resistance(raw)
        if rs <= 0:
            raise ValueError("Invalid sensor resistance")

        ppm = self.mq135.calculate_ppm_from_rs(rs)
        ratio = rs / self.mq135.RZERO
        return {
            "mq_raw_adc": int(raw),
            "mq_rs": float(rs),
            "mq_rs_corr": float(rs),
            "mq_ratio": float(ratio),
            "co2": int(ppm),
            "read_ok": True,
        }

    def _sanitize_linear_coefficients(
        self,
        label: str,
        a: float,
        b: float,
        raw_min: float,
        raw_max: float,
        out_min: float,
        out_max: float,
    ) -> tuple:
        slope = float(a)
        offset = float(b)
        valid = True

        if slope < 0.3 or slope > 3.0:
            valid = False

        lo = slope * raw_min + offset
        hi = slope * raw_max + offset
        if lo < out_min or lo > out_max or hi < out_min or hi > out_max:
            valid = False

        if valid:
            return slope, offset

        log_console_file(
            f"Calibration guard: invalid DHT {label} coeffs "
            f"a={slope}, b={offset}; fallback to raw (a=1, b=0)"
        )
        return 1.0, 0.0

    def _init_led(self) -> object:
        try:
            pin = int(self.config.get("PINS", {}).get("sensors", {}).get("led", 2))
            led = machine.Pin(pin, machine.Pin.OUT)
            led.off()
            log_console_file("LED initialized on pin " + str(pin))
            return led
        except Exception as err:
            log_console_file("LED init failed: " + str(err))
            return None

    def _init_dht11(self) -> object:
        try:
            from sensors.dht11 import DHT11Sensor

            pin = int(self.config.get("PINS", {}).get("sensors", {}).get("dht11", 5))
            sensor = DHT11Sensor(pin)
            log_console_file("DHT11 initialized on pin " + str(pin))
            return sensor
        except Exception as err:
            log_console_file("DHT11 init failed: " + str(err))
            return None

    def _init_mq135(self) -> object:
        try:
            from sensors.mq135 import MQ135Sensor

            pin = int(self.config.get("PINS", {}).get("sensors", {}).get("mq135", 34))
            sensor = MQ135Sensor(pin)
            log_console_file("MQ135 initialized on pin " + str(pin))
            return sensor
        except Exception as err:
            log_console_file("MQ135 init failed: " + str(err))
            return None

    def _init_mpu6050(self) -> object:
        try:
            from sensors.mpu6050 import MPU6050

            sensor = MPU6050(self.config)
            log_console_file("MPU6050 initialized")
            return sensor
        except Exception as err:
            log_console_file("MPU6050 init failed: " + str(err))
            return None

    def _init_ina219(self) -> object:
        try:
            from sensors.ina219 import INA219

            i2c_cfg = self.config.get("PINS", {}).get("i2c", {})
            sda_pin = int(i2c_cfg.get("sda", 21))
            scl_pin = int(i2c_cfg.get("scl", 22))
            freq = int(i2c_cfg.get("freq", 100000))

            i2c = machine.SoftI2C(
                sda=machine.Pin(sda_pin),
                scl=machine.Pin(scl_pin),
                freq=freq,
            )
            addrs = i2c.scan()
            log_console_file("I2C scan: " + str([hex(x) for x in addrs]))
            if 0x40 not in addrs:
                log_console_file("INA219 not found on I2C (addr 0x40)")
                return None

            sensor = INA219(i2c, 0x40)
            log_console_file(
                f"INA219 initialized on I2C sda={sda_pin}, scl={scl_pin}, freq={freq}"
            )
            return sensor
        except Exception as err:
            log_console_file("INA219 init failed: " + str(err))
            return None

    def set_led(self, on: bool) -> None:
        if self.led is None:
            return
        try:
            if on:
                self.led.on()
            else:
                self.led.off()
        except Exception:
            pass

    def get_battery_voltage(self) -> object:
        data = self.read_battery_data()
        value = data.get("battery")
        if value is None:
            return None
        return float(value)

    def get_battery_percentage(self) -> object:
        voltage = self.get_battery_voltage()
        if voltage is None:
            return None
        return self._battery_pct_from_voltage(float(voltage))

    def _battery_pct_from_voltage(self, voltage: float) -> object:
        battery_cfg = self.config.get("BATTERY", {})
        min_v = self._to_float(battery_cfg.get("min_voltage", 6.0), 6.0)
        max_v = self._to_float(battery_cfg.get("max_voltage", 8.4), 8.4)
        if max_v <= min_v:
            return None

        pct = (float(voltage) - min_v) * 100.0 / (max_v - min_v)
        if pct < 0:
            pct = 0.0
        if pct > 100:
            pct = 100.0
        return int(round(pct))

    def read_battery_data(self) -> dict:
        if self.ina is None:
            return {}
        try:
            data = self.ina.read()
            if not isinstance(data, dict):
                return {}
            out: dict = {}
            if "battery" in data:
                out["battery"] = self._to_float(data.get("battery"), 0.0)
            if "current_ma" in data:
                out["current_ma"] = self._to_float(data.get("current_ma"), 0.0)
            return out
        except Exception as err:
            log_console_file("INA219 read error: " + str(err))
            return {}

    def read_orientation(self) -> tuple:
        if self.mpu is None:
            return False, {"error": "MPU6050 not initialized"}
        try:
            return True, self.mpu.get_orientation()
        except Exception as err:
            return False, {"error": str(err)}

    def read_all_sensors(self) -> dict:
        data: dict = {}
        temp = 20
        hum = 50

        if self.dht11 is not None:
            try:
                dht_data = self.dht11.measure_temperature_humidity()
                temp_raw = dht_data.get("temperature", temp)
                hum_raw = dht_data.get("humidity", hum)
                temp = float(temp_raw)
                hum = float(hum_raw)
                if self.calibration_enabled and (temp_raw != 0 or hum_raw != 0):
                    temp = round(self.dht_temp_a * temp_raw + self.dht_temp_b, 2)
                    hum = round(self.dht_hum_a * hum_raw + self.dht_hum_b, 2)
                temp_out = int(round(temp))
                hum_out = int(round(hum))
                data["temperature"] = temp_out
                data["humidity"] = hum_out
                if self.include_sensor_diagnostics:
                    data["temperature_raw"] = temp_raw
                    data["humidity_raw"] = hum_raw
                    data["temperature_calibrated"] = temp
                    data["humidity_calibrated"] = hum
                log_console_file(
                    f"DHT11 -> temp_raw={temp_raw} hum_raw={hum_raw} "
                    f"temp_cal={temp} hum_cal={hum} "
                    f"temp_out={temp_out} hum_out={hum_out}"
                )
            except Exception as err:
                log_console_file("DHT11 read error: " + str(err))

        if self.mq135 is not None:
            try:
                data.update(self._read_mq135_aggregated(temp, hum))
                if "co2" in data:
                    log_console_file(f"MQ135 payload co2={data.get('co2')}")
            except Exception as err:
                log_console_file("MQ135 read error: " + str(err))

        if self.mpu is not None:
            try:
                data.update(self.mpu.get_orientation())
                log_console_file(
                    f"MPU6050 -> x={data.get('x')} y={data.get('y')} z={data.get('z')} "
                    f"has_moved={data.get('has_moved')} "
                    f"fall_detection={data.get('fall_detection_enabled')} "
                    f"delta={data.get('movement_delta')} "
                    f"mag={data.get('accel_magnitude')}"
                )
            except Exception as err:
                log_console_file("MPU6050 read error: " + str(err))

        battery_data = self.read_battery_data()
        if battery_data:
            data.update(battery_data)
            battery_pct = self._battery_pct_from_voltage(self._to_float(battery_data.get("battery"), 0.0))
            if battery_pct is not None:
                data["battery_pct"] = battery_pct
            log_console_file(
                f"INA219 -> battery={data.get('battery')}V "
                f"current={data.get('current_ma')}mA "
                f"battery_pct={data.get('battery_pct')}"
            )

        return data
