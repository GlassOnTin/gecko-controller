#!/usr/bin/env bash
source ./venv/bin/activate

pip install pytest pytest-timeout

# Run all hardware tests
pytest tests/hardware --hardware -v

# Run specific test file
pytest tests/hardware/test_i2c.py --hardware -v

# Run specific test function
pytest tests/hardware/test_sensor_readings.py::test_temperature_reading --hardware -v

deactivate
