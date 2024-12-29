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
            try:
                self.bus = smbus2.SMBus(1)
                self._initialized = True
            except Exception as e:
                print(f"Failed to initialize I2C bus: {e}")
                self._initialized = False

    def write_cmd(self, cmd: int, retries: int = 3) -> bool:
        if not self._initialized:
            return False

        for attempt in range(retries):
            try:
                with self._lock:
                    # Set a lower-level timeout using fcntl
                    import fcntl
                    import struct
                    # I2C timing values (100ms timeout)
                    I2C_TIMEOUT = 0x0702  # I2C timeout value define
                    I2C_TIMEOUT_VALUE = struct.pack('I', 100)  # 100 milliseconds
                    fcntl.ioctl(self.bus.fd, I2C_TIMEOUT, I2C_TIMEOUT_VALUE)

                    self.bus.write_byte_data(self.addr, 0x00, cmd)
                    time.sleep(0.001)  # 1ms delay between commands
                    return True
            except Exception as e:
                if attempt == retries - 1:
                    print(f"Error in write_cmd (attempt {attempt + 1}/{retries}): {e}")
                time.sleep(0.01)  # Short delay before retry
        return False

    def __del__(self):
        """Cleanup method to properly close the I2C bus"""
        if hasattr(self, 'bus'):
            try:
                self.bus.close()
            except:
                pass

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
