import machine
import time

print("ESP32U Booting...")

led = machine.Pin(16, machine.Pin.OUT)
for i in range(3):
    led.on()
    time.sleep(0.2)
    led.off()
    time.sleep(0.2)

print("Boot complete")