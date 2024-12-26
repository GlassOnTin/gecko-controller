#!/usr/bin/env python3
import time
import smbus2

class SSH1106Test:
    def __init__(self, i2c_addr=0x3C):
        self.addr = i2c_addr
        self.bus = smbus2.SMBus(1)

        print(f"Initializing test display on address 0x{i2c_addr:02x}")

        # Initialize display
        self.init_display()

    def write_cmd(self, cmd):
        try:
            self.bus.write_byte_data(self.addr, 0x00, cmd)
            time.sleep(0.001)  # 1ms delay between commands
        except Exception as e:
            print(f"Error writing command 0x{cmd:02x}: {e}")
            raise

    def write_data(self, data):
        try:
            self.bus.write_byte_data(self.addr, 0x40, data)
            time.sleep(0.0001)  # 0.1ms delay between data writes
        except Exception as e:
            print(f"Error writing data 0x{data:02x}: {e}")
            raise

    def init_display(self):
        # Basic initialization sequence
        cmds = [
            0xAE,   # Display off
            0x20,   # Set memory addressing mode
            0x00,   # Horizontal addressing mode
            0xC8,   # Set COM output scan direction
            0x40,   # Set display start line
            0x81,   # Set contrast control
            0xFF,   # Maximum contrast
            0xA1,   # Set segment re-map
            0xA6,   # Normal display
            0xA8,   # Set multiplex ratio
            0x3F,   # 64 COM lines
            0xD3,   # Set display offset
            0x00,   # No offset
            0xD5,   # Set display clock
            0x80,   # Recommended value
            0xDA,   # Set COM pins
            0x12,   # Alternative COM pin configuration
            0x8D,   # Charge pump setting
            0x14,   # Enable charge pump
            0xAF    # Display on
        ]

        print("Initializing display...")
        for cmd in cmds:
            self.write_cmd(cmd)
            time.sleep(0.001)  # 1ms delay between commands
        print("Initialization complete")

    def test_pattern(self):
        """Draw a simple test pattern - alternating columns"""
        print("\nDrawing test pattern...")
        try:
            # Set display position
            self.write_cmd(0x02)  # Set lower column address
            self.write_cmd(0x10)  # Set higher column address

            # Write pattern one page at a time
            for page in range(8):  # 8 pages for 64 pixel height
                print(f"Writing page {page}")
                self.write_cmd(0xB0 + page)  # Set page address

                # Write alternating pattern
                for col in range(132):  # 132 columns
                    # Alternate between all pixels on and all pixels off
                    pattern = 0xFF if col % 2 == 0 else 0x00
                    self.write_data(pattern)
                    time.sleep(0.0001)  # Small delay between columns

                time.sleep(0.001)  # Delay between pages

            print("Test pattern complete")

        except Exception as e:
            print(f"Error drawing test pattern: {e}")
            raise

if __name__ == "__main__":
    display = SSH1106Test()
    time.sleep(0.1)  # Short delay after init
    display.test_pattern()
