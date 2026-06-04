from machine import Pin, SoftI2C


class MPU6050:
    def __init__(self, config: dict = None) -> None:
        cfg: dict = config or {}
        i2c_cfg = cfg.get("PINS", {}).get("i2c", {})
        scl_pin = int(i2c_cfg.get("scl", 22))
        sda_pin = int(i2c_cfg.get("sda", 21))
        freq = int(i2c_cfg.get("freq", 100000))

        self.i2c: object = SoftI2C(
            scl=Pin(scl_pin, Pin.IN, Pin.PULL_UP),
            sda=Pin(sda_pin, Pin.IN, Pin.PULL_UP),
            freq=freq,
        )
        self.addr: int = 0x68
        self.i2c.writeto_mem(self.addr, 0x6B, b"\x00")

        fall_cfg = cfg.get("FALL_DETECTION", {})
        self.history_size: int = int(fall_cfg.get("history_size", 5) or 5)
        if self.history_size < 2:
            self.history_size = 2
        if self.history_size > 20:
            self.history_size = 20

        self.movement_threshold_g: float = float(fall_cfg.get("movement_threshold_g", 0.65) or 0.65)
        self.magnitude_delta_threshold_g: float = float(
            fall_cfg.get("magnitude_delta_threshold_g", self.movement_threshold_g)
            or self.movement_threshold_g
        )
        self.impact_threshold_g: float = float(fall_cfg.get("impact_threshold_g", 2.2) or 2.2)
        self.freefall_threshold_g: float = float(fall_cfg.get("freefall_threshold_g", 0.35) or 0.35)

        self.fall_detection_enabled: bool = False
        self.has_moved: bool = False
        self.last_delta_g: float = 0.0
        self.last_magnitude_g: float = 0.0
        self.history: list = []

    def _to_int16(self, msb: int, lsb: int) -> int:
        value = (msb << 8) | lsb
        if value > 32767:
            value -= 65536
        return int(value)

    def enable_fall_detection(self, enable: bool) -> None:
        self.fall_detection_enabled = bool(enable)
        self.has_moved = False
        self.last_delta_g = 0.0
        self.last_magnitude_g = 0.0
        self.history = []

    def clear_movement(self) -> None:
        self.has_moved = False

    def _magnitude(self, item: dict) -> float:
        x = float(item.get("x", 0.0))
        y = float(item.get("y", 0.0))
        z = float(item.get("z", 0.0))
        return float((x * x + y * y + z * z) ** 0.5)

    def _max_axis_delta(self, current: dict, previous: dict) -> float:
        dx = abs(float(current.get("x", 0.0)) - float(previous.get("x", 0.0)))
        dy = abs(float(current.get("y", 0.0)) - float(previous.get("y", 0.0)))
        dz = abs(float(current.get("z", 0.0)) - float(previous.get("z", 0.0)))
        return float(max(dx, dy, dz))

    def _update_history(self, item: dict) -> None:
        self.history.append({
            "x": float(item.get("x", 0.0)),
            "y": float(item.get("y", 0.0)),
            "z": float(item.get("z", 0.0)),
        })
        while len(self.history) > self.history_size:
            self.history.pop(0)

    def _update_fall_detection(self, item: dict) -> None:
        magnitude = self._magnitude(item)
        self.last_magnitude_g = magnitude

        max_axis_delta = 0.0
        max_magnitude_delta = 0.0
        for previous in self.history:
            axis_delta = self._max_axis_delta(item, previous)
            if axis_delta > max_axis_delta:
                max_axis_delta = axis_delta

            magnitude_delta = abs(magnitude - self._magnitude(previous))
            if magnitude_delta > max_magnitude_delta:
                max_magnitude_delta = magnitude_delta

        self.last_delta_g = max(max_axis_delta, max_magnitude_delta)

        if self.fall_detection_enabled and self.history:
            moved = (
                max_axis_delta >= self.movement_threshold_g
                or max_magnitude_delta >= self.magnitude_delta_threshold_g
                or magnitude >= self.impact_threshold_g
                or magnitude <= self.freefall_threshold_g
            )
            if moved:
                self.has_moved = True

    def get_orientation(self) -> dict:
        data = self.i2c.readfrom_mem(self.addr, 0x3B, 6)
        x_raw = self._to_int16(data[0], data[1])
        y_raw = self._to_int16(data[2], data[3])
        z_raw = self._to_int16(data[4], data[5])
        orientation = {
            "x": round(x_raw / 16384, 2),
            "y": round(y_raw / 16384, 2),
            "z": round(z_raw / 16384, 2),
        }
        self._update_fall_detection(orientation)
        self._update_history(orientation)
        orientation["has_moved"] = bool(self.has_moved)
        orientation["fall_detection_enabled"] = bool(self.fall_detection_enabled)
        orientation["movement_delta"] = round(float(self.last_delta_g), 2)
        orientation["accel_magnitude"] = round(float(self.last_magnitude_g), 2)
        return orientation

    def get_fall_detection_state(self) -> dict:
        return {
            "enabled": bool(self.fall_detection_enabled),
            "has_moved": bool(self.has_moved),
            "history_size": int(self.history_size),
            "history_count": int(len(self.history)),
            "movement_threshold_g": float(self.movement_threshold_g),
            "magnitude_delta_threshold_g": float(self.magnitude_delta_threshold_g),
            "impact_threshold_g": float(self.impact_threshold_g),
            "freefall_threshold_g": float(self.freefall_threshold_g),
            "movement_delta": round(float(self.last_delta_g), 2),
            "accel_magnitude": round(float(self.last_magnitude_g), 2),
        }
