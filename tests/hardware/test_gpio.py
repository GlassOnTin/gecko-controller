import pytest
import RPi.GPIO as GPIO
import time

@pytest.fixture(scope="module")
def gpio_setup():
    """Setup GPIO for testing"""
    GPIO.setmode(GPIO.BCM)
    yield
    GPIO.cleanup()

def test_light_relay(gpio_setup):
    """Test the light relay operation"""
    LIGHT_RELAY = 17
    GPIO.setup(LIGHT_RELAY, GPIO.OUT)

    # Test ON
    GPIO.output(LIGHT_RELAY, GPIO.HIGH)
    time.sleep(1)
    # Here you could add actual verification of the relay state

    # Test OFF
    GPIO.output(LIGHT_RELAY, GPIO.LOW)
    time.sleep(1)

def test_heat_relay(gpio_setup):
    """Test the heat relay operation"""
    HEAT_RELAY = 4
    GPIO.setup(HEAT_RELAY, GPIO.OUT)

    # Test ON
    GPIO.output(HEAT_RELAY, GPIO.HIGH)
    time.sleep(1)

    # Test OFF
    GPIO.output(HEAT_RELAY, GPIO.LOW)
    time.sleep(1)
