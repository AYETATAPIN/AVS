import network

class APManager:
    def __init__(self, ssid="ESP32S3-Sensor", password="12345678"):
        self.ssid = ssid
        self.password = password
        self.ap = network.WLAN(network.AP_IF)

    def start(self):
        self.ap.active(True)
        self.ap.config(essid=self.ssid, password=self.password)
        while not self.ap.active():
            pass
        print('AP started')
        print('SSID:', self.ssid)
        print('IP address:', self.ap.ifconfig()[0])  # Usually 192.168.4.1
        return self.ap.ifconfig()[0]