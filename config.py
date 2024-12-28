# Gecko Controller Configuration File
# This file will be installed to /etc/gecko-controller/config.py
# You can modify these values to customize your gecko enclosure settings
# The service must be restarted after changes: sudo systemctl restart gecko-controller

# Display I2C
DISPLAY_ADDRESS = 0x3c

# GPIO Pins
LIGHT_RELAY = 17
HEAT_RELAY = 4
DISPLAY_RESET = 21

# Temperature Settings
MIN_TEMP = 15.0
DAY_TEMP = 30.0
TEMP_TOLERANCE = 1.0

# Time Settings
LIGHT_ON_TIME = "07:30"
LIGHT_OFF_TIME = "19:30"

# UV Thresholds # μW/cm²
UVA_THRESHOLDS = {
    'low': 50.0,
    'high': 100.0
}

UVB_THRESHOLDS = {
    'low': 2.0,
    'high': 5.0
}

# UV View Factor Correction
SENSOR_HEIGHT = 0.2
LAMP_DIST_FROM_BACK = 0.3
ENCLOSURE_HEIGHT = 0.5
SENSOR_ANGLE = 90
