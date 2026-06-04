import machine
import network
import utime as time
import gc

from utils import log_console_file

try:
    import ntptime
except ImportError:
    ntptime = None


class WiFiService:
    def __init__(self, config: dict) -> None:
        self.config: dict = config
        wifi_cfg = self.config.get("WIFI", {})
        power_cfg = self.config.get("POWER", {})
        time_cfg = self.config.get("TIME", {})

        self.timeout: int = max(1, int(wifi_cfg.get("connect_timeout_sec", 20)))
        self.profiles_priority = wifi_cfg.get("profiles_priority", [])
        self.profiles = wifi_cfg.get("profiles", {})
        self.legacy_ssid: str = str(wifi_cfg.get("ssid", "") or "").strip()
        self.legacy_password: str = str(wifi_cfg.get("password", "") or "")
        self.wifi_pm_active: str = str(power_cfg.get("wifi_pm_active", "PM_PERFORMANCE"))
        self.wifi_pm_standby: str = str(power_cfg.get("wifi_pm_standby", "PM_POWERSAVE"))
        self.time_min_year: int = int(time_cfg.get("min_year", 2026))
        self.ntp_hosts = time_cfg.get(
            "ntp_hosts",
            ["pool.ntp.org", "time.google.com", "time.cloudflare.com"],
        )
        self.ntp_retries_per_host: int = max(1, int(time_cfg.get("ntp_retries_per_host", 2)))
        self.ntp_retry_pause_ms: int = max(100, int(time_cfg.get("ntp_retry_pause_ms", 250)))
        self.ntp_resync_interval_sec: int = max(300, int(time_cfg.get("resync_interval_sec", 6 * 60 * 60)))
        self.last_ntp_sync_ms: int = 0
        self.connected_profile_name: str = ""
        self.connected_profile_type: str = ""

        gc.collect()
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.connection_plan = self._build_connection_plan()

    def supports_eduroam(self) -> bool:
        return bool(hasattr(self.wlan, "eap_enable") or hasattr(network, "AUTH_WPA2_ENT"))

    def _to_str(self, value: object, default: str = "") -> str:
        return str(value if value is not None else default)

    def _build_connection_plan(self) -> list:
        plan = []
        if isinstance(self.profiles_priority, list) and isinstance(self.profiles, dict):
            for profile_name in self.profiles_priority:
                profile = self.profiles.get(profile_name)
                if isinstance(profile, dict):
                    item = dict(profile)
                    item["name"] = self._to_str(profile_name, "").strip()
                    plan.append(item)

        if plan:
            return plan

        if self.legacy_ssid:
            return [
                {
                    "name": "legacy_wpa2",
                    "type": "wpa2",
                    "ssid": self.legacy_ssid,
                    "password": self.legacy_password,
                    "connect_timeout_sec": self.timeout,
                }
            ]
        return []

    def _clear_enterprise_state(self) -> None:
        try:
            if hasattr(self.wlan, "eap_disable"):
                self.wlan.eap_disable()
        except Exception:
            pass

    def _disconnect_if_needed(self) -> None:
        try:
            self.wlan.disconnect()
        except Exception:
            pass

    def _wait_until_connected(self, timeout_sec: int) -> bool:
        deadline = time.ticks_add(time.ticks_ms(), int(max(1, timeout_sec) * 1000))
        while not self.wlan.isconnected():
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                return False
            machine.idle()
        return self.wlan.isconnected()

    def _connect_wpa2(self, profile: dict) -> bool:
        ssid = self._to_str(profile.get("ssid"), "").strip()
        password = self._to_str(profile.get("password"), "")
        timeout_sec = int(profile.get("connect_timeout_sec", self.timeout) or self.timeout)
        if not ssid:
            return False

        log_console_file(f"Connecting Wi-Fi profile={profile.get('name', 'wpa2')} type=wpa2 ssid={ssid}")
        self._disconnect_if_needed()
        self._clear_enterprise_state()
        try:
            self.wlan.connect(ssid, password)
        except Exception as err:
            log_console_file(f"WPA2 connect() failed for {ssid}: {err}")
            return False

        if self._wait_until_connected(timeout_sec):
            self.connected_profile_name = self._to_str(profile.get("name", "wpa2"), "wpa2")
            self.connected_profile_type = "wpa2"
            log_console_file(f"Wi-Fi connected via {profile.get('name', 'wpa2')}: {self.wlan.ifconfig()}")
            return True

        try:
            status = self.wlan.status()
        except Exception:
            status = "unknown"
        log_console_file(f"WPA2 connection timeout for {ssid}, status={status}")
        return False

    def _connect_eduroam(self, profile: dict) -> bool:
        if not self.supports_eduroam():
            log_console_file("Eduroam profile skipped: enterprise API not available")
            return False

        ssid = self._to_str(profile.get("ssid", "eduroam"), "eduroam").strip()
        identity = self._to_str(profile.get("identity"), "").strip()
        username = self._to_str(profile.get("username"), "").strip()
        password = self._to_str(profile.get("password"), "")
        timeout_sec = int(profile.get("connect_timeout_sec", self.timeout) or self.timeout)
        use_ca_cert = bool(profile.get("use_ca_cert", False))
        ca_cert_path = self._to_str(profile.get("ca_cert_path"), "").strip()

        if not ssid or not username or not password:
            log_console_file("Eduroam profile invalid: ssid/username/password required")
            return False
        if not identity:
            identity = username

        auth_wpa2_ent = getattr(network, "AUTH_WPA2_ENT", getattr(network, "AUTH_WPA2_ENTERPRISE", None))
        if auth_wpa2_ent is None:
            log_console_file("Eduroam profile skipped: AUTH_WPA2_ENT missing")
            return False

        log_console_file(f"Connecting Wi-Fi profile={profile.get('name', 'eduroam')} type=eduroam ssid={ssid}")
        self.wlan.active(True)
        self._disconnect_if_needed()
        self._clear_enterprise_state()
        gc.collect()
        try:
            log_console_file("Free heap before eduroam connect: " + str(gc.mem_free()))
        except Exception:
            pass

        try:
            log_console_file("Eduroam: eap_set_identity")
            self.wlan.eap_set_identity(identity.encode())
            log_console_file("Eduroam: eap_set_username")
            self.wlan.eap_set_username(username.encode())
            log_console_file("Eduroam: eap_set_password")
            self.wlan.eap_set_password(password.encode())
            if use_ca_cert and ca_cert_path:
                log_console_file("Eduroam: eap_set_ca_cert from " + ca_cert_path)
                with open(ca_cert_path, "rb") as cert_file:
                    self.wlan.eap_set_ca_cert(cert_file.read())
            log_console_file("Eduroam: eap_enable")
            self.wlan.eap_enable()
            log_console_file("Eduroam: wlan.connect authmode=AUTH_WPA2_ENT")
            self.wlan.connect(ssid, authmode=auth_wpa2_ent)
        except Exception as err:
            log_console_file(f"Eduroam connect() failed for {ssid}: {err}")
            return False

        if self._wait_until_connected(timeout_sec):
            self.connected_profile_name = self._to_str(profile.get("name", "eduroam"), "eduroam")
            self.connected_profile_type = "eduroam"
            log_console_file(f"Wi-Fi connected via {profile.get('name', 'eduroam')}: {self.wlan.ifconfig()}")
            return True

        try:
            status = self.wlan.status()
        except Exception:
            status = "unknown"
        log_console_file(f"Eduroam connection timeout for {ssid}, status={status}")
        return False

    def configure_pm(self, standby: bool) -> None:
        pm_name = self.wifi_pm_standby if standby else self.wifi_pm_active
        try:
            pm_value = getattr(network.WLAN, pm_name)
            self.wlan.config(pm=pm_value)
            log_console_file("Wi-Fi PM set to " + pm_name)
        except Exception as err:
            log_console_file(f"Wi-Fi PM not applied ({pm_name}): {err}")

    def get_rssi(self) -> int:
        try:
            if self.wlan.isconnected():
                return int(self.wlan.status("rssi"))
        except Exception:
            pass
        return -100

    def connect(self) -> bool:
        if self.wlan.isconnected():
            self._sync_time_ntp()
            return True

        if not self.connection_plan:
            log_console_file("Wi-Fi profile list is empty")
            return False

        for profile in self.connection_plan:
            gc.collect()
            profile_type = self._to_str(profile.get("type", "wpa2"), "wpa2").strip().lower()
            connected = False
            if profile_type == "eduroam":
                # TODO remove
                connected = self._connect_eduroam(profile)
                # continue
            else:
                connected = self._connect_wpa2(profile)
            if connected:
                self._sync_time_ntp(force=True)
                return True

        log_console_file("Wi-Fi connection failed for all profiles")
        return False

    def ensure_connected(self) -> bool:
        if self.wlan.isconnected():
            self._sync_time_ntp()
            return True
        return self.connect()

    def _clock_year(self) -> int:
        try:
            return int(time.gmtime()[0])
        except Exception:
            return 0

    def _time_sane(self) -> bool:
        return self._clock_year() >= self.time_min_year

    def _sync_time_ntp(self, force: bool = False) -> bool:
        if ntptime is None:
            return self._time_sane()

        now_ms = time.ticks_ms()
        if not force and self._time_sane() and self.last_ntp_sync_ms:
            if time.ticks_diff(now_ms, self.last_ntp_sync_ms) < int(self.ntp_resync_interval_sec * 1000):
                return True

        if not self.wlan.isconnected():
            return False

        for host in self.ntp_hosts:
            if not host:
                continue
            for _ in range(self.ntp_retries_per_host):
                try:
                    ntptime.host = str(host)
                except Exception:
                    pass

                try:
                    ntptime.settime()
                    if self._time_sane():
                        self.last_ntp_sync_ms = now_ms
                        log_console_file("NTP synced via " + str(host) + "; now=" + str(time.gmtime()))
                        return True
                except Exception as err:
                    log_console_file(f"NTP sync failed via {host}: {err}")

                try:
                    time.sleep_ms(self.ntp_retry_pause_ms)
                except Exception:
                    pass

        if not self._time_sane():
            log_console_file("NTP sync failed; current year=" + str(self._clock_year()))
        return self._time_sane()
