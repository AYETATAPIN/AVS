import gc
import json
import os

from utils import log_console_file

try:
    import ota.rollback as ota_rollback
except ImportError:
    ota_rollback = None

try:
    import ota.update as ota_update
except ImportError:
    ota_update = None


OTA_REQUEST_FILE = "ota_request.json"


class OTAService:
    def __init__(self) -> None:
        self.has_update_module: bool = ota_update is not None
        self.has_rollback_module: bool = ota_rollback is not None

    def cancel_pending_rollback(self) -> None:
        if ota_rollback is None:
            log_console_file("ota.rollback module not found; rollback cancel skipped")
            return
        try:
            ota_rollback.cancel()
            log_console_file("OTA rollback cancellation requested on boot")
        except Exception as err:
            log_console_file("OTA rollback cancel skipped: " + str(err))

    def save_update_request(self, url: str, sha256: str, length: int) -> tuple:
        if not url:
            return False, "Missing URL parameter"
        request = {
            "url": str(url),
            "sha256": str(sha256 or ""),
            "length": int(length or 0),
        }
        try:
            with open(OTA_REQUEST_FILE, "w") as file_obj:
                json.dump(request, file_obj)
            log_console_file("OTA request saved for boot-time update")
            return True, "OTA request saved, rebooting to OTA mode"
        except Exception as err:
            log_console_file("OTA request save failed: " + str(err))
            return False, str(err)

    def load_update_request(self) -> object:
        try:
            with open(OTA_REQUEST_FILE, "r") as file_obj:
                data = json.load(file_obj)
            if not isinstance(data, dict):
                return None
            return data
        except Exception:
            return None

    def clear_update_request(self) -> None:
        try:
            os.remove(OTA_REQUEST_FILE)
        except Exception:
            pass

    def run_update(self, url: str, sha256: str, length: int) -> tuple:
        if ota_update is None:
            return False, "ota.update module is not installed"
        if not url:
            return False, "Missing URL parameter"

        try:
            def progress_cb(done: int, expected: int) -> None:
                if expected:
                    log_console_file(f"OTA progress: {done}/{expected} bytes")
                else:
                    log_console_file(f"OTA progress: {done} bytes")

            def status_cb(message: str) -> None:
                log_console_file(str(message))

            sha_text = str(sha256 or "").strip()
            kwargs = {
                "verify": bool(sha_text),
                "reboot": False,
                "progress_cb": progress_cb,
                "status_cb": status_cb,
            }
            if sha_text:
                kwargs["sha"] = sha_text
            else:
                log_console_file("OTA update without sha256 verification")
            if length:
                kwargs["length"] = int(length)

            log_console_file("Starting OTA update from: " + str(url))
            gc.collect()
            try:
                log_console_file(f"OTA free heap before download: {gc.mem_free()}")
            except Exception:
                pass
            result = ota_update.from_file(url, **kwargs)
            if isinstance(result, dict):
                log_console_file(
                    f"OTA image staged: bytes={result.get('bytes', 'unknown')}, "
                    f"sha256={result.get('sha256', 'unknown')}"
                )
            else:
                log_console_file("OTA image staged successfully")
            return True, "OTA image staged, reboot required"
        except Exception as err:
            gc.collect()
            try:
                log_console_file(f"OTA free heap after failure: {gc.mem_free()}")
            except Exception:
                pass
            log_console_file("OTA update failed: " + str(err))
            return False, str(err)

    def run_rollback(self) -> tuple:
        if ota_rollback is None:
            return False, "ota.rollback module is not installed"
        if not hasattr(ota_rollback, "force"):
            return False, "ota.rollback.force() unavailable"
        try:
            ota_rollback.force()
            log_console_file("OTA rollback force requested")
            return True, "Rollback requested, reboot required"
        except Exception as err:
            log_console_file("OTA rollback failed: " + str(err))
            return False, str(err)
