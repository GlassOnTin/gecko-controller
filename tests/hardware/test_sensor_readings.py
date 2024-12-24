from gecko_controller.controller import GeckoController
import pytest

@pytest.fixture(scope="module")
def controller():
    """Create a controller instance for testing"""
    return GeckoController()

def test_temperature_reading(controller):
    """Test temperature sensor reading"""
    temp, humidity = controller.read_sensor()
    assert temp is not None, "Temperature reading failed"
    assert 10 <= temp <= 40, f"Temperature {temp}°C out of expected range"

def test_humidity_reading(controller):
    """Test humidity sensor reading"""
    temp, humidity = controller.read_sensor()
    assert humidity is not None, "Humidity reading failed"
    assert 20 <= humidity <= 80, f"Humidity {humidity}% out of expected range"

def test_uv_reading(controller):
    """Test UV sensor reading"""
    uva, uvb, uvc = controller.read_uv()
    assert uva is not None, "UVA reading failed"
    assert uvb is not None, "UVB reading failed"
    assert uvc is not None, "UVC reading failed"
    assert 0 <= uva <= 1000, f"UVA {uva} out of expected range"
    assert 0 <= uvb <= 100, f"UVB {uvb} out of expected range"
