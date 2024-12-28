import pytest
import os
import smbus2

def check_sensor_access():
    """Check if we have access to the required sensors"""
    try:
        # Check I2C access
        if not os.path.exists('/dev/i2c-1'):
            return False
        if not os.access('/dev/i2c-1', os.R_OK | os.W_OK):
            return False

        # Check for specific sensors by address
        bus = smbus2.SMBus(1)

        # Try reading from AS7331 (0x74)
        try:
            bus.read_byte(0x74)
            temp_sensor_present = True
        except:
            temp_sensor_present = False

        bus.close()
        return temp_sensor_present or uv_sensor_present

    except Exception as e:
        print(f"Sensor check error: {e}")
        return False
