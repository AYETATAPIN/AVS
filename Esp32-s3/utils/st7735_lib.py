import machine
import time


class ST7735:
    def __init__(self, spi, cs, dc, rst, width=128, height=160):
        self.spi = spi
        self.cs = cs
        self.dc = dc
        self.rst = rst
        self.width = width
        self.height = height

        # Initialize pins
        self.cs.init(self.cs.OUT, value=1)
        self.dc.init(self.dc.OUT, value=0)
        self.rst.init(self.rst.OUT, value=1)

        self._init_display()

    def _write_cmd(self, cmd):
        self.cs.value(0)
        self.dc.value(0)
        self.spi.write(bytearray([cmd]))
        self.cs.value(1)

    def _write_data(self, data):
        self.cs.value(0)
        self.dc.value(1)
        self.spi.write(data)
        self.cs.value(1)

    def _init_display(self):
        # Hardware reset
        self.rst.value(1)
        time.sleep_ms(5)
        self.rst.value(0)
        time.sleep_ms(20)
        self.rst.value(1)
        time.sleep_ms(150)

        # Initialization commands
        self._write_cmd(0x01)  # SWRESET
        time.sleep_ms(120)
        self._write_cmd(0x11)  # SLPOUT
        time.sleep_ms(120)
        self._write_cmd(0x3A)  # COLMOD
        self._write_data(bytearray([0x05]))  # 16bit color
        self._write_cmd(0x29)  # DISPON
        time.sleep_ms(120)

    def _set_window(self, x, y, w, h):
        x1 = x + w - 1
        y1 = y + h - 1
        self._write_cmd(0x2A)  # CASET
        self._write_data(bytearray([x >> 8, x & 0xFF, x1 >> 8, x1 & 0xFF]))
        self._write_cmd(0x2B)  # RASET
        self._write_data(bytearray([y >> 8, y & 0xFF, y1 >> 8, y1 & 0xFF]))
        self._write_cmd(0x2C)  # RAMWR

    def fill(self, color):
        self._set_window(0, 0, self.width, self.height)
        data = bytearray([color >> 8, color & 0xFF])
        self.cs.value(0)
        self.dc.value(1)
        for _ in range(self.width * self.height):
            self.spi.write(data)
        self.cs.value(1)

    def text(self, text, x, y, color):
        # Simple character drawing
        for i, char in enumerate(text[:16]):  # Max 16 chars
            self._draw_char(char, x + i * 8, y, color)

    def _draw_char(self, char, x, y, color):
        # Basic 5x7 font for uppercase and numbers
        font = {
            'A': [0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
            'B': [0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E],
            'C': [0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E],
            'D': [0x1C, 0x12, 0x11, 0x11, 0x11, 0x12, 0x1C],
            'E': [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F],
            'F': [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10],
            'G': [0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F],
            'H': [0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
            'I': [0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E],
            'L': [0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F],
            'M': [0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11],
            'N': [0x11, 0x19, 0x19, 0x15, 0x13, 0x13, 0x11],
            'O': [0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
            'P': [0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10],
            'R': [0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11],
            'S': [0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E],
            'T': [0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04],
            'U': [0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E],
            'V': [0x11, 0x11, 0x11, 0x11, 0x0A, 0x0A, 0x04],
            'Y': [0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04],
            '0': [0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E],
            '1': [0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E],
            '2': [0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F],
            '3': [0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E],
            '4': [0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02],
            '5': [0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E],
            '6': [0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E],
            '7': [0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08],
            '8': [0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E],
            '9': [0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C],
            ' ': [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
            ':': [0x00, 0x04, 0x00, 0x00, 0x00, 0x04, 0x00],
            '/': [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x00],
        }

        char = char.upper()
        if char in font:
            char_data = font[char]
            for row in range(7):
                for col in range(5):
                    if char_data[row] & (1 << (4 - col)):
                        self._draw_pixel(x + col, y + row, color)

    def _draw_pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            self._set_window(x, y, 1, 1)
            self.cs.value(0)
            self.dc.value(1)
            self.spi.write(bytearray([color >> 8, color & 0xFF]))
            self.cs.value(1)