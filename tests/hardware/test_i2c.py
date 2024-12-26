import pytest
import smbus2
import time

def test_i2c_devices():
    """Test that all expected I2C devices are present and responding"""
    bus = smbus2.SMBus(1)

    # Test OLED Display
    try:
        bus.write_byte(0x3c, 0)
        assert True, "OLED display found"
    except:
        pytest.fail("OLED display not responding at 0x3c")

    # Test Temperature/Humidity Sensor - Modified for SHT31
    try:
        # SHT31 requires a specific command sequence
        bus.write_i2c_block_data(0x44, 0x2C, [0x06])
        time.sleep(0.5)  # Wait for measurement
        data = bus.read_i2c_block_data(0x44, 0x00, 6)
        assert len(data) == 6, "SHT31 sensor found"
    except Exception as e:
        pytest.fail(f"SHT31 not responding at 0x44: {str(e)}")

    # Test UV Sensor
    try:
        # AS7331 specific command
        bus.write_byte(0x74, 0x00)  # Read OSR register
        assert True, "AS7331 sensor found"
    except:
        pytest.fail("AS7331 not responding at 0x74")
