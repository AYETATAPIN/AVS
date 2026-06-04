import utime

CONFIG_FILE: str = "_config.json"
LOGGING_FILE: str = "_logs.txt"


def get_rfc3339_timestamp() -> str:
    y, mo, d, h, m, s, *_ = utime.gmtime()
    return f"{y:04d}-{mo:02d}-{d:02d}T{h:02d}:{m:02d}:{s:02d}Z"


def log_console_file(msg: str) -> None:
    time_stamp = get_rfc3339_timestamp()
    log_msg = f"{time_stamp}: {msg}"
    with open(LOGGING_FILE, "a") as f:
        f.write(log_msg)
    print(log_msg)
