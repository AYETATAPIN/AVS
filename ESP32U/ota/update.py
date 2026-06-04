import gc

try:
    import usocket as socket
except ImportError:
    import socket

try:
    import ussl as ssl
except ImportError:
    try:
        import ssl
    except ImportError:
        ssl = None

try:
    import uhashlib as hashlib
except ImportError:
    import hashlib

try:
    import ubinascii as binascii
except ImportError:
    import binascii

from esp32 import Partition


BLOCK_SIZE = 4096
READ_SIZE = 512
ESP_IMAGE_MAGIC = 0xE9
MAX_REDIRECTS = 3
BODY_TIMEOUT_SEC = 60
OTA_DOWNLOAD_ATTEMPTS = 3
IOCTL_BLOCK_ERASE = 6


class OTAError(Exception):
    pass


def _parse_url(url: str) -> tuple:
    marker = "://"
    if marker not in url:
        raise OTAError("URL must include scheme")

    scheme, rest = url.split(marker, 1)
    scheme = scheme.lower()
    if scheme not in ("http", "https"):
        raise OTAError("Unsupported URL scheme: " + scheme)

    if "/" in rest:
        host_port, path = rest.split("/", 1)
        path = "/" + path
    else:
        host_port = rest
        path = "/"

    if not host_port:
        raise OTAError("URL host is empty")

    if ":" in host_port:
        host, port_text = host_port.rsplit(":", 1)
        port = int(port_text)
    else:
        host = host_port
        port = 443 if scheme == "https" else 80

    return scheme, host, port, path


def _join_location(current_url: str, location: str) -> str:
    if location.startswith("http://") or location.startswith("https://"):
        return location
    scheme, host, port, _ = _parse_url(current_url)
    default_port = 443 if scheme == "https" else 80
    port_text = "" if port == default_port else ":" + str(port)
    if not location.startswith("/"):
        location = "/" + location
    return f"{scheme}://{host}{port_text}{location}"


def _readline(sock: object) -> bytes:
    data: bytearray = bytearray()
    while True:
        b = sock.read(1)
        if not b:
            break
        data.extend(b)
        if b == b"\n":
            break
    return bytes(data)


def _hex_prefix(data: bytes, limit: int = 16) -> str:
    return binascii.hexlify(data[:limit]).decode()


def _decode_http_line(data: bytes) -> str:
    chars: list = []
    for value in data:
        if value in (9, 10, 13) or 32 <= value <= 126:
            chars.append(chr(value))
        else:
            chars.append("?")
    return "".join(chars)


def _set_timeout(sock: object, timeout_sec: int) -> None:
    try:
        sock.settimeout(timeout_sec)
    except Exception:
        pass


def _emit_status(status_cb: object, message: str) -> None:
    if status_cb is None:
        return
    try:
        status_cb(message)
    except Exception:
        pass


def _open_http(url: str) -> tuple:
    scheme, host, port, path = _parse_url(url)
    addr = socket.getaddrinfo(host, port)[0][-1]
    sock = socket.socket()
    try:
        _set_timeout(sock, 15)
        sock.connect(addr)
        if scheme == "https":
            if ssl is None:
                raise OTAError("SSL module is unavailable")
            try:
                sock = ssl.wrap_socket(sock, server_hostname=host)
            except TypeError:
                sock = ssl.wrap_socket(sock)

        request = (
            f"GET {path} HTTP/1.0\r\n"
            f"Host: {host}\r\n"
            "User-Agent: avs-esp32-ota\r\n"
            "Accept-Encoding: identity\r\n"
            "Connection: close\r\n\r\n"
        )
        sock.write(request.encode())

        raw_status_line = _readline(sock)
        status_line = _decode_http_line(raw_status_line).strip()
        if not status_line:
            raise OTAError("Empty HTTP response")
        if not status_line.startswith("HTTP/"):
            raise OTAError("Invalid HTTP status bytes: " + _hex_prefix(raw_status_line))
        parts = status_line.split()
        if len(parts) < 2:
            raise OTAError("Invalid HTTP status: " + status_line)
        status = int(parts[1])

        headers: dict = {}
        while True:
            line = _readline(sock)
            if not line or line in (b"\r\n", b"\n"):
                break
            text = _decode_http_line(line).strip()
            if ":" in text:
                key, value = text.split(":", 1)
                headers[key.strip().lower()] = value.strip()

        return sock, status, headers
    except Exception:
        try:
            sock.close()
        except Exception:
            pass
        raise


def _open_with_redirects(url: str) -> tuple:
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        sock, status, headers = _open_http(current)
        if status in (301, 302, 303, 307, 308):
            location = headers.get("location")
            try:
                sock.close()
            except Exception:
                pass
            if not location:
                raise OTAError("HTTP redirect without Location")
            current = _join_location(current, location)
            continue
        return sock, status, headers, current
    raise OTAError("Too many HTTP redirects")


def _hex_sha256(digest: bytes) -> str:
    return binascii.hexlify(digest).decode().lower()


def _normal_sha(value: object) -> str:
    return str(value or "").strip().lower().replace(":", "")


def _partition_size(partition: object) -> int:
    return int(partition.info()[3])


def _write_image(
    sock: object,
    partition: object,
    expected_sha: str,
    expected_length: int,
    max_length: int,
    progress_cb: object = None,
) -> dict:
    block_index: int = 0
    block_offset: int = 0
    total: int = 0
    image_hash: object = hashlib.sha256()
    magic_checked: bool = False
    next_progress: int = 64 * 1024

    while True:
        read_size = READ_SIZE
        if expected_length:
            remaining = expected_length - total
            if remaining <= 0:
                break
            if remaining < read_size:
                read_size = remaining

        try:
            chunk = sock.read(read_size)
        except Exception as err:
            raise OTAError(f"Body read failed after {total} bytes: {err}")
        if not chunk:
            break

        if not magic_checked:
            if chunk[0] != ESP_IMAGE_MAGIC:
                raise OTAError("Invalid ESP image magic")
            magic_checked = True

        image_hash.update(chunk)
        total += len(chunk)
        if expected_length and total > expected_length:
            raise OTAError("Image larger than expected length")
        if max_length and total > max_length:
            raise OTAError("Image does not fit OTA partition")

        if progress_cb is not None and total >= next_progress:
            try:
                progress_cb(total, expected_length)
            except Exception:
                pass
            while total >= next_progress:
                next_progress += 64 * 1024

        if block_offset == 0:
            try:
                partition.ioctl(IOCTL_BLOCK_ERASE, block_index)
            except Exception:
                pass

        partition.writeblocks(block_index, chunk, block_offset)
        block_offset += len(chunk)

        if block_offset >= BLOCK_SIZE:
            block_index += 1
            block_offset = 0
            gc.collect()

        if expected_length and total >= expected_length:
            break

    if not magic_checked:
        raise OTAError("Empty image")

    actual_sha = _hex_sha256(image_hash.digest())
    if expected_sha and actual_sha != _normal_sha(expected_sha):
        raise OTAError(f"SHA256 mismatch: got {actual_sha}, expected {expected_sha}")

    if expected_length and total != expected_length:
        raise OTAError(f"Length mismatch: got {total}, expected {expected_length}")

    if progress_cb is not None:
        try:
            progress_cb(total, expected_length)
        except Exception:
            pass

    return {
        "bytes": total,
        "sha256": actual_sha,
        "partition": partition.info(),
    }


def from_file(
    url: str,
    sha: object = None,
    sha256: object = None,
    verify: bool = True,
    reboot: bool = False,
    length: int = 0,
    progress_cb: object = None,
    status_cb: object = None,
) -> dict:
    expected_sha = _normal_sha(sha256 or sha)
    if verify and not expected_sha:
        raise OTAError("Expected sha256 is required")

    running = Partition(Partition.RUNNING)
    update_partition = running.get_next_update()
    partition_size = _partition_size(update_partition)
    expected_length = int(length or 0)
    if expected_length and expected_length > partition_size:
        raise OTAError("Image does not fit OTA partition")

    last_error = None
    for attempt in range(1, OTA_DOWNLOAD_ATTEMPTS + 1):
        sock = None
        try:
            _emit_status(status_cb, f"OTA HTTP attempt {attempt}/{OTA_DOWNLOAD_ATTEMPTS}")
            sock, status, headers, final_url = _open_with_redirects(str(url))
            if status != 200:
                raise OTAError("HTTP status " + str(status))
            if headers.get("transfer-encoding", "").lower() == "chunked":
                raise OTAError("Chunked transfer is not supported")

            header_length = int(headers.get("content-length", "0") or 0)
            if expected_length and header_length and header_length != expected_length:
                raise OTAError("Content-Length does not match expected length")
            if not expected_length:
                expected_length = header_length
            if expected_length and expected_length > partition_size:
                raise OTAError("Image does not fit OTA partition")
            if progress_cb is not None:
                try:
                    progress_cb(0, expected_length)
                except Exception:
                    pass

            _set_timeout(sock, BODY_TIMEOUT_SEC)
            result = _write_image(
                sock,
                update_partition,
                expected_sha if verify else "",
                expected_length,
                partition_size,
                progress_cb,
            )
            result["url"] = final_url
            update_partition.set_boot()

            if reboot:
                import machine
                machine.reset()

            return result
        except Exception as err:
            last_error = err
            _emit_status(status_cb, "OTA attempt failed: " + str(err))
            gc.collect()
            if attempt >= OTA_DOWNLOAD_ATTEMPTS:
                raise
        finally:
            if sock is not None:
                try:
                    sock.close()
                except Exception:
                    pass

    if last_error is not None:
        raise last_error
    raise OTAError("OTA download failed")
