import network
import time
import machine


class WiFiManager:
    def __init__(self):
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        self.led = machine.Pin(16, machine.Pin.OUT)
        self.led.off()

    def connect(self, ssid, password, timeout=20):
        print(f"Connecting to WiFi: {ssid}")

        if not self.wlan.isconnected():
            self.wlan.connect(ssid, password)

            start_time = time.time()
            while not self.wlan.isconnected():
                if time.time() - start_time > timeout:
                    print("WiFi connection timeout")
                    self.led.off()
                    return False

                self.led.value(not self.led.value())
                time.sleep(0.5)
                print(".", end="")

        self.led.on()
        config = self.wlan.ifconfig()
        print(f"\nWiFi connected!")
        print(f"IP: {config[0]}")
        print(f"Gateway: {config[2]}")
        print(f"Subnet: {config[1]}")
        return True

    def status(self):
        if self.wlan.isconnected():
            config = self.wlan.ifconfig()
            return {
                'connected': True,
                'ip': config[0],
                'gateway': config[2],
                'subnet': config[1]
            }
        return {'connected': False, 'status': self.wlan.status()}

    def disconnect(self):
        self.wlan.disconnect()
        self.led.off()
        print("WiFi disconnected")
