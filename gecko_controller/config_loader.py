# Write this as config_loader.py in the gecko_controller package

from dataclasses import dataclass
from typing import Dict

@dataclass
class Config:
    """Configuration container class"""
    DISPLAY_ADDRESS: int
    LIGHT_RELAY: int
    HEAT_RELAY: int
    DISPLAY_RESET: int
    MIN_TEMP: float
    DAY_TEMP: float
    TEMP_TOLERANCE: float
    LIGHT_ON_TIME: str
    LIGHT_OFF_TIME: str
    UVA_THRESHOLDS: Dict[str, float]
    UVB_THRESHOLDS: Dict[str, float]
    SENSOR_HEIGHT: float
    LAMP_DIST_FROM_BACK: float
    ENCLOSURE_HEIGHT: float
    SENSOR_ANGLE: float

def load_config():
    """Load configuration from appropriate location"""
    try:
        # First try package config
        from gecko_controller.config import (
            DISPLAY_ADDRESS, LIGHT_RELAY, HEAT_RELAY, DISPLAY_RESET,
            MIN_TEMP, DAY_TEMP, TEMP_TOLERANCE, LIGHT_ON_TIME, LIGHT_OFF_TIME,
            UVA_THRESHOLDS, UVB_THRESHOLDS, SENSOR_HEIGHT, LAMP_DIST_FROM_BACK,
            ENCLOSURE_HEIGHT, SENSOR_ANGLE
        )
    except ImportError:
        try:
            # Then try system config
            import sys
            sys.path.append('/etc/gecko-controller')
            from config import (
                DISPLAY_ADDRESS, LIGHT_RELAY, HEAT_RELAY, DISPLAY_RESET,
                MIN_TEMP, DAY_TEMP, TEMP_TOLERANCE, LIGHT_ON_TIME, LIGHT_OFF_TIME,
                UVA_THRESHOLDS, UVB_THRESHOLDS, SENSOR_HEIGHT, LAMP_DIST_FROM_BACK,
                ENCLOSURE_HEIGHT, SENSOR_ANGLE
            )
        except ImportError:
            try:
                # Finally try local/test config
                from tests.config import (
                    DISPLAY_ADDRESS, LIGHT_RELAY, HEAT_RELAY, DISPLAY_RESET,
                    MIN_TEMP, DAY_TEMP, TEMP_TOLERANCE, LIGHT_ON_TIME, LIGHT_OFF_TIME,
                    UVA_THRESHOLDS, UVB_THRESHOLDS, SENSOR_HEIGHT, LAMP_DIST_FROM_BACK,
                    ENCLOSURE_HEIGHT, SENSOR_ANGLE
                )
            except ImportError:
                print("Error: Could not find configuration file")
                print("The file should be at: /etc/gecko-controller/config.py")
                print("Try reinstalling the package with: sudo apt install --reinstall gecko-controller")
                return None

    return Config(
        DISPLAY_ADDRESS=DISPLAY_ADDRESS,
        LIGHT_RELAY=LIGHT_RELAY,
        HEAT_RELAY=HEAT_RELAY,
        DISPLAY_RESET=DISPLAY_RESET,
        MIN_TEMP=MIN_TEMP,
        DAY_TEMP=DAY_TEMP,
        TEMP_TOLERANCE=TEMP_TOLERANCE,
        LIGHT_ON_TIME=LIGHT_ON_TIME,
        LIGHT_OFF_TIME=LIGHT_OFF_TIME,
        UVA_THRESHOLDS=UVA_THRESHOLDS,
        UVB_THRESHOLDS=UVB_THRESHOLDS,
        SENSOR_HEIGHT=SENSOR_HEIGHT,
        LAMP_DIST_FROM_BACK=LAMP_DIST_FROM_BACK,
        ENCLOSURE_HEIGHT=ENCLOSURE_HEIGHT,
        SENSOR_ANGLE=SENSOR_ANGLE
    )
