import pytest
from datetime import datetime, time
from gecko_controller.controller import GeckoController

def test_parse_time_setting():
    """Test the time parsing utility function"""
    controller = GeckoController(test_mode=True)

    # Test valid HH:MM format
    assert controller.parse_time_setting("14:30") == time(14, 30)
    assert controller.parse_time_setting("08:15") == time(8, 15)
    assert controller.parse_time_setting("00:00") == time(0, 0)

    # Test single-digit hour with minutes
    assert controller.parse_time_setting("9:30") == time(9, 30)

    # Test hour-only backward compatibility
    assert controller.parse_time_setting("14") == time(14, 0)
    assert controller.parse_time_setting("9") == time(9, 0)

    # Test invalid inputs
    assert controller.parse_time_setting("25:00") == time(0, 0)  # Invalid hour
    assert controller.parse_time_setting("14:60") == time(0, 0)  # Invalid minute
    assert controller.parse_time_setting("invalid") == time(0, 0)  # Invalid format
    assert controller.parse_time_setting("") == time(0, 0)  # Empty string

def test_uv_correction_calculation():
    """Test UV correction factor calculation"""
    controller = GeckoController(test_mode=True)

    # The default result should be greater than 1.0 since we're correcting for sensor position
    correction = controller.calculate_uv_correction()
    assert correction > 1.0

    # Result should be a float
    assert isinstance(correction, float)

    # Test specific positions
    # For vertical angle (90°), distance effect should dominate
    close_correction = controller.calculate_uv_correction(
        sensor_height=0.1,    # Closer to source
        lamp_dist=0.3,
        enclosure_height=0.5,
        sensor_angle=90
    )

    far_correction = controller.calculate_uv_correction(
        sensor_height=0.4,    # Further from source
        lamp_dist=0.3,
        enclosure_height=0.5,
        sensor_angle=90
    )

    # Correction factor should be larger when sensor is further from UV source
    # because inverse square law means we need to multiply reading by a larger factor
    assert far_correction > close_correction, \
        f"Far correction ({far_correction}) should be > close correction ({close_correction})"

    # Test angle effect
    direct_correction = controller.calculate_uv_correction(
        sensor_height=0.2,
        lamp_dist=0.3,
        enclosure_height=0.5,
        sensor_angle=45    # Angled more directly at source
    )

    oblique_correction = controller.calculate_uv_correction(
        sensor_height=0.2,
        lamp_dist=0.3,
        enclosure_height=0.5,
        sensor_angle=20    # More oblique angle to source
    )

    # Direct angle should need less correction than oblique angle
    assert direct_correction < oblique_correction, \
        "Direct measurements should need less correction than oblique ones"
