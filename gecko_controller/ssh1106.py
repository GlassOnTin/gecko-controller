import time
import smbus2
from PIL import Image

class SSH1106Display:
    def __init__(self, i2c_addr=0x3C, width=128, height=64):
        self.addr = i2c_addr
        self.width = width
        self.height = height
        self.pages = height // 8
        self.buffer = [0] * (width * self.pages)
        self.consecutive_errors = 0
        self.MAX_RETRY_COUNT = 3
        self.retry_delay = 0.1  # seconds

        print(f"Initializing SSH1106 Display on i2c address 0x{i2c_addr:02x}")
        print(f"Display size: {width}x{height} in {self.pages} pages")

        self.bus = smbus2.SMBus(1)
        time.sleep(0.1)  # Wait after bus initialization
        self.init_display()

    def write_with_retry(self, reg, data, is_cmd=True):
        """Write to I2C with retry logic and bus recovery"""
        for attempt in range(self.MAX_RETRY_COUNT):
            try:
                if attempt > 0:
                    # On retry, try to recover the I2C bus
                    self.recover_i2c_bus()
                    time.sleep(self.retry_delay * (attempt + 1))

                self.bus.write_byte_data(self.addr, 0x00 if is_cmd else 0x40, data)
                self.consecutive_errors = 0  # Reset error counter on success
                return True

            except OSError as e:
                self.consecutive_errors += 1
                print(f"I2C {'command' if is_cmd else 'data'} write error (attempt {attempt + 1}): {e}")

                if attempt == self.MAX_RETRY_COUNT - 1:
                    # If this was our last attempt, check if we need to reinitialize
                    if self.consecutive_errors >= self.MAX_RETRY_COUNT * 2:
                        print("Too many consecutive errors, attempting display reinitialization...")
                        try:
                            self.init_display()
                            self.consecutive_errors = 0
                        except:
                            print("Display reinitialization failed")
                    return False
        return False

    def recover_i2c_bus(self):
        """Attempt to recover the I2C bus"""
        try:
            # Close and reopen the I2C bus
            self.bus.close()
            time.sleep(0.1)
            self.bus = smbus2.SMBus(1)
            time.sleep(0.1)
        except Exception as e:
            print(f"Bus recovery failed: {e}")

    def write_cmd(self, cmd):
        """Write a command to the display with retry logic"""
        success = self.write_with_retry(0x00, cmd, is_cmd=True)
        if success:
            time.sleep(0.001)  # 1ms delay between commands
        return success

    def write_data(self, data):
        """Write data to the display with retry logic"""
        success = self.write_with_retry(0x40, data, is_cmd=False)
        if success:
            time.sleep(0.0001)  # 0.1ms delay between data writes
        return success

    def init_display(self):
        """Initialize the SSH1106 display with delays between commands"""
        print("\nInitializing display...")

        # Turn display off first
        retry_count = 0
        while retry_count < 3:
            try:
                self.write_cmd(0xAE)
                break
            except Exception as e:
                print(f"Init retry {retry_count + 1}: {e}")
                retry_count += 1
                time.sleep(0.5)
                self.recover_i2c_bus()

        # Initialization sequence with proper delays and error handling
        init_sequence = [
            (0xD5, 0.001),  # Set display clock div
            (0x80, 0.001),
            (0xA8, 0.001),  # Set multiplex
            (0x3F, 0.001),
            (0xD3, 0.001),  # Set display offset
            (0x00, 0.001),
            (0x40, 0.001),  # Set start line
            (0x8D, 0.001),  # Enable charge pump
            (0x14, 0.001),
            (0x20, 0.001),  # Memory mode
            (0x00, 0.001),
            (0xA1, 0.001),  # Seg remap
            (0xC8, 0.001),  # COM scan direction
            (0xDA, 0.001),  # Set COM pins
            (0x12, 0.001),
            (0x81, 0.001),  # Set contrast
            (0xFF, 0.001),
            (0xD9, 0.001),  # Set precharge
            (0xF1, 0.001),
            (0xDB, 0.001),  # Set VCOMH
            (0x20, 0.001),
            (0xA4, 0.001),  # Display not all ON
            (0xA6, 0.001),  # Normal display
            (0xAF, 0.1)     # Display on, longer delay
        ]

        for cmd, delay in init_sequence:
            success = self.write_cmd(cmd)
            if not success:
                print(f"Warning: Command 0x{cmd:02X} failed during initialization")
            time.sleep(delay)

        print("Display initialization complete")

    def show_image(self, image):
        """Display a PIL Image object with improved error handling"""
        try:
            # Convert image to 1-bit color
            if image.mode != '1':
                image = image.convert('1')

            # Create a new image with the full 132x64 size
            full_image = Image.new('1', (132, 64), 255)  # white background

            # Paste the image in the center
            paste_x = (132 - image.width) // 2
            paste_y = (64 - image.height) // 2
            full_image.paste(image, (paste_x, paste_y))

            # Reset the display position with retry
            for _ in range(3):
                if self.write_cmd(0x02) and self.write_cmd(0x10):  # Set column address
                    break
                time.sleep(0.1)

            # Write display buffer one page at a time with error checking
            for page in range(self.pages):
                if not self.write_cmd(0xB0 + page):  # Set page address
                    print(f"Failed to set page {page}")
                    continue

                time.sleep(0.001)  # Small delay after page command

                failed_writes = 0
                for x in range(132):  # Write all 132 columns
                    bits = 0
                    for bit in range(8):
                        y = page * 8 + bit
                        if y < 64 and x < 132:
                            if full_image.getpixel((x, y)) == 0:  # Black pixel
                                bits |= (1 << bit)

                    if not self.write_data(bits):
                        failed_writes += 1
                        if failed_writes > 10:  # If too many writes fail, try next page
                            print(f"Too many failed writes on page {page}")
                            break

                time.sleep(0.001)  # Small delay between pages

        except Exception as e:
            print(f"Error in show_image: {e}")
            try:
                self.init_display()  # Try to recover by reinitializing
            except:
                print("Failed to recover display")
