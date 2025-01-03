import pytest
import os
from gecko_controller.controller import GeckoController

@pytest.fixture
def controller():
    """Fixture to provide a GeckoController instance"""
    return GeckoController()

def check_sensor_access():
    """Check if we have access to the required sensors"""
    try:
        # Check I2C access
        if not os.path.exists('/dev/i2c-1'):
            return False
        if not os.access('/dev/i2c-1', os.R_OK | os.W_OK):
            return False

        # Check for specific sensors by address
        import smbus2
        bus = smbus2.SMBus(1)

        # Try reading from SHT31 (0x44)
        try:
            bus.read_byte(0x44)
            temp_sensor_present = True
        except:
            temp_sensor_present = False

        bus.close()
        return temp_sensor_present or uv_sensor_present

    except Exception as e:
        print(f"Sensor check error: {e}")
        return False

# Skip all tests if sensors aren't accessible
pytestmark = pytest.mark.skipif(
    not check_sensor_access(),
    reason="Required sensors not accessible on I2C bus"
)

@pytest.mark.timeout(30)  # Add timeout to prevent hanging
def test_temperature_reading(controller):
    """Test temperature sensor reading"""
    temp, _ = controller.read_sensor()
    assert temp is not None, "Temperature reading failed"
    assert isinstance(temp, float), "Temperature should be a float"
    assert 0 <= temp <= 50, f"Temperature {temp}°C outside reasonable range (0-50°C)"
    print(f"Temperature reading: {temp:.1f}°C")

@pytest.mark.timeout(30)
def test_humidity_reading(controller):
    """Test humidity sensor reading"""
    _, humidity = controller.read_sensor()
    assert humidity is not None, "Humidity reading failed"
    assert isinstance(humidity, float), "Humidity should be a float"
    assert 0 <= humidity <= 100, f"Humidity {humidity}% outside valid range (0-100%)"
    print(f"Humidity reading: {humidity:.1f}%")
