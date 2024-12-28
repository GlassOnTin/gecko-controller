import pytest
import os
import sys
import smbus2
from pathlib import Path
import RPi.GPIO as GPIO

# Add test config module to path
test_dir = Path(__file__).parent
sys.path.insert(0, str(test_dir))

# Create mock config for tests
def pytest_configure(config):
    """Create a mock config module for testing"""
    config_path = Path(__file__).parent / "config.py"

    mock_config = """
# Test configuration
DISPLAY_ADDRESS = 0x3c
LIGHT_RELAY = 17
HEAT_RELAY = 4
DISPLAY_RESET = 21
MIN_TEMP = 15.0
DAY_TEMP = 30.0
TEMP_TOLERANCE = 1.0
LIGHT_ON_TIME = "07:30"
LIGHT_OFF_TIME = "19:30"
UVA_THRESHOLDS = {
    'low': 50.0,
    'high': 100.0
}
UVB_THRESHOLDS = {
    'low': 2.0,
    'high': 5.0
}
SENSOR_HEIGHT = 0.2
LAMP_DIST_FROM_BACK = 0.3
ENCLOSURE_HEIGHT = 0.5
SENSOR_ANGLE = 90
"""
    with open(config_path, 'w') as f:
        f.write(mock_config)

def pytest_unconfigure(config):
    """Clean up test config"""
    config_path = Path(__file__).parent / "config.py"
    if config_path.exists():
        config_path.unlink()

# Add test marks
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "requires_display: mark test as requiring display hardware"
    )
    config.addinivalue_line(
        "markers", "requires_hardware: mark test as requiring hardware access"
    )

def check_raspberry_pi():
    """Check if we're running on a Raspberry Pi"""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            return any(line.startswith('Hardware') and 'BCM' in line for line in f)
    except:
        return False

def check_i2c_available():
    """Check if I2C bus is available"""
    try:
        # Try to open I2C bus 1 (typical on Raspberry Pi)
        bus = smbus2.SMBus(1)
        bus.close()
        return True
    except:
        return False

def check_gpio_available():
    """Check if GPIO access is available"""
    try:
        # Try to set up and clean a test GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(18, GPIO.OUT)  # Use GPIO 18 as test pin
        GPIO.cleanup()
        return True
    except:
        return False

def check_hardware_available():
    """
    Check if hardware testing is possible based on available devices,
    not just Pi detection
    """
    has_gpio = os.path.exists('/dev/gpiomem')
    has_i2c = os.path.exists('/dev/i2c-1')
    return has_gpio and has_i2c

def pytest_runtest_setup(item):
    """Skip tests based on actual hardware availability rather than Pi detection"""
    for marker in item.iter_markers():
        if marker.name == 'requires_hardware':
            if not check_hardware_available():
                pytest.skip("Test requires hardware devices (/dev/gpiomem and /dev/i2c-1)")
            if not os.access('/dev/gpiomem', os.W_OK):
                pytest.skip("No write access to /dev/gpiomem - run with sudo or check group permissions")
            if not os.access('/dev/i2c-1', os.R_OK | os.W_OK):
                pytest.skip("No access to /dev/i2c-1 - run with sudo or check group permissions")
