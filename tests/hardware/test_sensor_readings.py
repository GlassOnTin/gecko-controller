@pytest.mark.timeout(30)  # Add timeout to prevent hanging
def test_temperature_reading(controller):
    """Test temperature sensor reading"""
    for _ in range(3):  # Try up to 3 times
        temp, humidity = controller.read_sensor()
        if temp is not None:
            assert 10 <= temp <= 40, f"Temperature {temp}°C out of expected range"
            return
        time.sleep(1)
    pytest.fail("Temperature reading failed after 3 attempts")

@pytest.mark.timeout(30)
def test_humidity_reading(controller):
    """Test humidity sensor reading"""
    for _ in range(3):  # Try up to 3 times
        temp, humidity = controller.read_sensor()
        if humidity is not None:
            assert 20 <= humidity <= 80, f"Humidity {humidity}% out of expected range"
            return
        time.sleep(1)
    pytest.fail("Humidity reading failed after 3 attempts")

@pytest.mark.timeout(30)
def test_uv_reading(controller):
    """Test UV sensor reading"""
    if controller.uv_sensor is None:
        pytest.skip("UV sensor not available")

    for _ in range(3):  # Try up to 3 times
        uva, uvb, uvc = controller.read_uv()
        if all(x is not None for x in (uva, uvb, uvc)):
            assert 0 <= uva <= 1000, f"UVA {uva} out of expected range"
            assert 0 <= uvb <= 100, f"UVB {uvb} out of expected range"
            return
        time.sleep(1)
    pytest.fail("UV reading failed after 3 attempts")
