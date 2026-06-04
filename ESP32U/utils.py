import os
import utime

CONFIG_FILE = "_config.json"
LOGGING_FILE = "logs.txt"
MIN_VALID_YEAR = 2026
_BOOT_TICKS_MS = utime.ticks_ms()

# Automatic logs file maintenance.
LOG_CLEAR_TIMEOUT_SEC = 6 * 60 * 60
LOG_MAINT_INTERVAL_SEC = 15
LOG_MAX_BYTES = 128 * 1024
_LOG_LAST_MAINT_MS = utime.ticks_ms()
_LOG_LAST_CLEAR_MS = utime.ticks_ms()


def _parse_build_date() -> tuple:
    try:
        version = str(os.uname().version)
    except Exception:
        return None

    marker = " on "
    if marker not in version:
        return None

    tail = version.split(marker, 1)[1]
    date_part = tail.split(";", 1)[0].strip()
    if len(date_part) != 10 or date_part[4] != "-" or date_part[7] != "-":
        return None

    try:
        year = int(date_part[0:4])
        month = int(date_part[5:7])
        day = int(date_part[8:10])
        return year, month, day
    except Exception:
        return None


def _mktime_safe(year: int, month: int, day: int, hour: int, minute: int, second: int) -> object:
    try:
        return int(utime.mktime((year, month, day, hour, minute, second, 0, 0)))
    except Exception:
        pass

    try:
        return int(utime.mktime((year, month, day, hour, minute, second, 0, 0, -1)))
    except Exception:
        return None


def _fallback_base_epoch() -> int:
    build = _parse_build_date()
    if build is None:
        build = (MIN_VALID_YEAR, 1, 1)
    elif int(build[0]) < int(MIN_VALID_YEAR):
        build = (MIN_VALID_YEAR, 1, 1)

    base = _mktime_safe(build[0], build[1], build[2], 0, 0, 0)
    if base is not None:
        return int(base)

    base = _mktime_safe(2025, 1, 1, 0, 0, 0)
    return int(base) if base is not None else 0


_FALLBACK_BASE_EPOCH = _fallback_base_epoch()


def _fallback_datetime() -> tuple:
    elapsed_sec = int(utime.ticks_diff(utime.ticks_ms(), _BOOT_TICKS_MS) // 1000)
    try:
        year, month, day, hour, minute, second, _, _ = utime.gmtime(_FALLBACK_BASE_EPOCH + elapsed_sec)
        return year, month, day, hour, minute, second
    except Exception:
        return 2025, 1, 1, 0, 0, int(elapsed_sec % 60)


def get_rfc3339_timestamp() -> str:
    try:
        year, month, day, hour, minute, second, _, _ = utime.gmtime()
        if int(year) < int(MIN_VALID_YEAR):
            year, month, day, hour, minute, second = _fallback_datetime()
            if int(year) < int(MIN_VALID_YEAR):
                year, month, day, hour, minute, second = MIN_VALID_YEAR, 1, 1, 0, 0, 0
    except Exception:
        year, month, day, hour, minute, second = _fallback_datetime()
        if int(year) < int(MIN_VALID_YEAR):
            year, month, day, hour, minute, second = MIN_VALID_YEAR, 1, 1, 0, 0, 0

    return (
        f"{int(year):04d}-{int(month):02d}-{int(day):02d}T"
        f"{int(hour):02d}:{int(minute):02d}:{int(second):02d}Z"
    )


def _file_size_bytes(path: str) -> int:
    try:
        stat_data = os.stat(path)
        if len(stat_data) >= 7:
            size = int(stat_data[6])
            return size if size >= 0 else 0
        if len(stat_data) >= 4:
            size = int(stat_data[3])
            return size if size >= 0 else 0
    except Exception:
        return 0
    return 0


def _truncate_log_file() -> None:
    try:
        with open(LOGGING_FILE, "w") as file_obj:
            file_obj.write("")
    except Exception:
        pass


def _maintain_log_file() -> None:
    global _LOG_LAST_MAINT_MS
    global _LOG_LAST_CLEAR_MS

    now_ms = utime.ticks_ms()
    min_step_ms = int(LOG_MAINT_INTERVAL_SEC * 1000)
    if utime.ticks_diff(now_ms, _LOG_LAST_MAINT_MS) < min_step_ms:
        return
    _LOG_LAST_MAINT_MS = now_ms

    if _file_size_bytes(LOGGING_FILE) > int(LOG_MAX_BYTES):
        _truncate_log_file()
        _LOG_LAST_CLEAR_MS = now_ms
        return

    clear_after_ms = int(LOG_CLEAR_TIMEOUT_SEC * 1000)
    if utime.ticks_diff(now_ms, _LOG_LAST_CLEAR_MS) >= clear_after_ms:
        _truncate_log_file()
        _LOG_LAST_CLEAR_MS = now_ms


def log_console_file(msg: object) -> None:
    text = str(msg)
    time_stamp = get_rfc3339_timestamp()
    log_msg = f"{time_stamp}: {text}"

    _maintain_log_file()
    try:
        with open(LOGGING_FILE, "a") as file_obj:
            file_obj.write(log_msg + "\n")
    except Exception:
        pass

    print(log_msg)
