import os
import time
import subprocess
import smbus2
from PIL import Image
import threading
from typing import Optional

class SSH1106Display:
    """
    Singleton implementation of SSH1106 OLED display driver with resilient I2C handling.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, i2c_addr=0x3C):
        if self._initialized:
            return

        with self._lock:
            self.addr = i2c_addr
            self.pages = 8
            self.width = 128
            self.height = 64
            self._initialized = True

    def show_image(self, image: Image.Image) -> bool:
        """Display a PIL Image object with thread safety and error handling"""
        if not self._initialized:
            return False

        try:
            with self._lock:
                # Convert image to 1-bit color
                if image.mode != '1':
                    image = image.convert('1')

                # Create a new image with the full 132x64 size
                full_image = Image.new('1', (132, 64), 255)  # white background

                # Paste the image in the center
                paste_x = (132 - image.width) // 2
                paste_y = (64 - image.height) // 2
                full_image.paste(image, (paste_x, paste_y))

                # Reset the display position
                if not (self.write_cmd(0x02) and self.write_cmd(0x10)):
                    return False

                # Write display buffer one page at a time
                for page in range(self.pages):
                    if not self.write_cmd(0xB0 + page):
                        return False

                    for x in range(132):
                        bits = 0
                        for bit in range(8):
                            y = page * 8 + bit
                            if y < 64 and x < 132:
                                if full_image.getpixel((x, y)) == 0:
                                    bits |= (1 << bit)

                        if not self.write_data(bits):
                            return False

                return True

        except Exception as e:
            print(f"Error in show_image: {e}")
            return False
