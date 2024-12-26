#!/usr/bin/env python3
import time
import smbus2
import pytest

def test_display():
    """Test basic I2C display functionality"""
    print("Starting basic I2C display test")
    bus = smbus2.SMBus(1)
    address = 0x3C

    try:
        print(f"\nTesting basic write to display at address 0x{address:02X}")
        # Write display off command (0xAE)
        bus.write_byte_data(address, 0x00, 0xAE)
        print("Successfully wrote display off command")

        # Wait a moment
        time.sleep(0.1)

        # Try to write display on command (0xAF)
        bus.write_byte_data(address, 0x00, 0xAF)
        print("Successfully wrote display on command")

        print("\nBasic communication test passed!")
        assert True, "Display communication successful"

    except OSError as e:
        print(f"\nError communicating with display: {e}")
        print("\nTroubleshooting suggestions:")
        print("1. Check physical connections (especially SDA, SCL, VCC and GND)")
        print("2. Verify display voltage (should be 3.3V)")
        print("3. Check for pull-up resistors on SDA and SCL")
        print("4. Try lower I2C speed in /boot/config.txt:")
        print("   dtparam=i2c_arm=on,i2c_arm_baudrate=50000")
        pytest.fail("Display communication failed")

if __name__ == "__main__":
    pytest.main(["-v", __file__])
