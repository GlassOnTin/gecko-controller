import pytest
import os
import smbus2
import RPi.GPIO as GPIO

def pytest_configure(config):
    """Check hardware and add markers"""
    is_raspberry_pi = check_raspberry_pi()
    has_i2c = check_i2c_available()
    has_gpio = check_gpio_available()

    # Register custom markers
    config.addinivalue_line(
        "markers", "requires_raspberry_pi: mark test that needs Raspberry Pi hardware"
    )
    config.addinivalue_line(
        "markers", "requires_i2c: mark test that needs I2C bus"
    )
    config.addinivalue_line(
        "markers", "requires_gpio: mark test that needs GPIO access"
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
