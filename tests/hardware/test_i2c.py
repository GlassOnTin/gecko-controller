import pytest
import smbus2

def test_i2c_devices():
    """Test that all expected I2C devices are present and responding"""
    bus = smbus2.SMBus(1)

    # Test OLED Display
    try:
        bus.write_byte(0x3c, 0)
        assert True, "OLED display found"
    except:
        pytest.fail("OLED display not responding at 0x3c")

    # Test Temperature/Humidity Sensor
    try:
        bus.write_byte(0x44, 0)
        assert True, "SHT31 sensor found"
    except:
        pytest.fail("SHT31 not responding at 0x44")

    # Test UV Sensor
    try:
        bus.write_byte(0x74, 0)
        assert True, "AS7331 sensor found"
    except:
        pytest.fail("AS7331 not responding at 0x74")
