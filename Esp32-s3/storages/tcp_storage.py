import socket
import json
import utime

def get_rfc3339_timestamp():
    y, mo, d, h, m, s, *_ = utime.gmtime()
    return f"{y:04d}-{mo:02d}-{d:02d}T{h:02d}:{m:02d}:{s:02d}Z"


class TCPStorage:
    def __init__(self, port=12345):
        self.port = port
        self.server_socket = None
        self.client_conn = None
        self.client_addr = None

    def start_server(self):
        addr = socket.getaddrinfo('0.0.0.0', self.port)[0][-1]
        self.server_socket = socket.socket()
        self.server_socket.bind(addr)
        self.server_socket.listen(1)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print('TCP server listening on port', self.port)

        # Wait for PC client to connect
        print('Waiting for PC client connection...')
        self.client_conn, self.client_addr = self.server_socket.accept()
        print('PC client connected from', self.client_addr)

    def send_measurement(self, measurement_data):
        if not self.client_conn:
            print("No client connected")
            return False

        try:
            # Add timestamp and raw payload
            payload = measurement_data.copy()
            payload['timestamp'] = get_rfc3339_timestamp()

            message = json.dumps(payload) + '\n'  # Line delimiter for easy parsing on PC
            self.client_conn.send(message.encode('utf-8'))
            print("Data sent to PC:", payload)
            return True
        except Exception as e:
            print("Send error:", e)
            self.client_conn = None
            return False

    def receive_command(self, timeout_ms=100):
        if not self.client_conn:
            return None

        try:
            self.client_conn.settimeout(timeout_ms / 1000)
            data = self.client_conn.recv(1024)
            if data:
                cmd = data.decode('utf-8').strip()
                print("Received command from PC:", cmd)
                return cmd
        except:
            pass  # Timeout or no data
        return None

    def close(self):
        if self.client_conn:
            self.client_conn.close()
        if self.server_socket:
            self.server_socket.close()