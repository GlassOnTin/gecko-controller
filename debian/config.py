# Gecko Controller Configuration File
# This file will be installed to /etc/gecko-controller/config.py
# You can modify these values to customize your gecko enclosure settings
# The service must be restarted after changes: sudo systemctl restart gecko-controller

# GPIO Pins
LIGHT_RELAY = 4
HEAT_RELAY = 17
DISPLAY_RESET = 21

# Temperature Settings
MIN_TEMP = 15.0
DAY_TEMP = 30.0
TEMP_TOLERANCE = 0.5

# Time Settings
LIGHT_ON_HOUR = 6
LIGHT_OFF_HOUR = 18

# UV Settings
MAX_UVA = 100.0  # μW/cm²
MAX_UVB = 50.0   # μW/cm²

# UV Thresholds
UVA_THRESHOLDS = {
    'low': 50.0,
    'high': 100.0
}

UVB_THRESHOLDS = {
    'low': 2.0,
    'high': 5.0
}
