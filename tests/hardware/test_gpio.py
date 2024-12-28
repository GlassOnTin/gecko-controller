import pytest
import RPi.GPIO as GPIO
import time
from gecko_controller.controller import GeckoController

@pytest.fixture
def controller():
    """Fixture to provide a GeckoController instance"""
    return GeckoController()

@pytest.fixture(scope="module")
def gpio_setup():
    """Setup GPIO for testing"""
    GPIO.setwarnings(False)  # Disable warnings
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
    assert GPIO.input(LIGHT_RELAY) == GPIO.HIGH, "Light relay failed to turn ON"

    # Test OFF
    GPIO.output(LIGHT_RELAY, GPIO.LOW)
    time.sleep(1)
    assert GPIO.input(LIGHT_RELAY) == GPIO.LOW, "Light relay failed to turn OFF"

def test_heat_relay(gpio_setup):
    """Test the heat relay operation"""
    HEAT_RELAY = 4
    GPIO.setup(HEAT_RELAY, GPIO.OUT)

    # Test ON
    GPIO.output(HEAT_RELAY, GPIO.HIGH)
    time.sleep(1)
    assert GPIO.input(HEAT_RELAY) == GPIO.HIGH, "Heat relay failed to turn ON"

    # Test OFF
    GPIO.output(HEAT_RELAY, GPIO.LOW)
    time.sleep(1)
    assert GPIO.input(HEAT_RELAY) == GPIO.LOW, "Heat relay failed to turn OFF"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
