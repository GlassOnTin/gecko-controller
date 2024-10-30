#!/usr/bin/env python3
import os
import time
import board
import busio
import RPi.GPIO as GPIO
import smbus
from datetime import datetime, timedelta
import adafruit_displayio_sh1107
import displayio
import terminalio
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
from .as7331 import AS7331, INTEGRATION_TIME_256MS, GAIN_16X

# Import config
try:
    from gecko_controller.config import *
except ImportError:
    try:
        import sys
        sys.path.append('/etc/gecko-controller')
        from config import *
    except ImportError:
        print("Error: Could not find configuration file")
        print("The file should be at: /etc/gecko-controller/config.py")
        print("Try reinstalling the package with: sudo apt install --reinstall gecko-controller")
        sys.exit(1)

# Get the directory where the module is installed
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(MODULE_DIR, "fonts", "forkawesome-12.pcf")

# GPIO Setup
GPIO.setmode(GPIO.BCM)

# Configure GPIO pins
GPIO.setup(LIGHT_RELAY, GPIO.OUT)
GPIO.setup(HEAT_RELAY, GPIO.OUT)
GPIO.setup(DISPLAY_RESET, GPIO.OUT)
GPIO.output(DISPLAY_RESET, GPIO.HIGH)  # Start with reset inactive

# Icon characters from Fork Awesome
ICON_CLOCK = "\uf017"
ICON_LIGHTBULB = "\uf0eb"
ICON_THERMOMETER = "\uf2c9"
ICON_TINT = "\uf043"
ICON_TARGET = "\uf140"
ICON_GOOD = "\uf118"       # Smiling face
ICON_TOO_LOW = "\uf119"    # Sad face
ICON_TOO_HIGH = "\uf071"   # Warning triangle
ICON_ERROR = "\uf29c"      # Question circle

class GeckoController:
    def __init__(self):
        self.setup_display()
        self.bus = smbus.SMBus(1)
        self.icon_font = bitmap_font.load_font(FONT_PATH)
        self.regular_font = terminalio.FONT

        # Initialize UV sensor
        self.uv_sensor = AS7331(1)
        self.uv_sensor.integration_time = INTEGRATION_TIME_256MS
        self.uv_sensor.gain = GAIN_16X

        # Use thresholds from config
        self.UVA_THRESHOLDS = UVA_THRESHOLDS
        self.UVB_THRESHOLDS = UVB_THRESHOLDS

    def setup_display(self):
        """Initialize the display"""
        displayio.release_displays()
        i2c = busio.I2C(board.SCL, board.SDA)
        display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
        self.display = adafruit_displayio_sh1107.SH1107(
            display_bus,
            width=128,
            height=64,
            rotation=0
        )

    def get_next_transition(self):
        """Calculate time until next light state change"""
        now = datetime.now()
        current_hour = now.hour

        if LIGHT_ON_HOUR <= current_hour < LIGHT_OFF_HOUR:
            # Lights are on, calculate time until off
            next_time = now.replace(hour=LIGHT_OFF_HOUR, minute=0, second=0)
            if next_time < now:
                next_time += timedelta(days=1)
            return "→OFF", next_time
        else:
            # Lights are off, calculate time until on
            next_time = now.replace(hour=LIGHT_ON_HOUR, minute=0, second=0)
            if next_time < now:
                next_time += timedelta(days=1)
            return "→ON", next_time

    def format_time_until(self, target_time):
        """Format the time until the next transition"""
        now = datetime.now()
        diff = target_time - now
        hours = int(diff.total_seconds() // 3600)
        minutes = int((diff.total_seconds() % 3600) // 60)
        return f"{hours}h{minutes:02d}m"

    def get_target_temp(self):
        """Get the current target temperature based on time of day"""
        current_hour = datetime.now().hour
        return DAY_TEMP if LIGHT_ON_HOUR <= current_hour < LIGHT_OFF_HOUR else MIN_TEMP


    def get_uv_status_icon(self, value, is_uvb=False):
        """
        Get status icon for UV readings with sunglasses for too high.

        Args:
            value (float): UV reading
            is_uvb (bool): True if reading is UVB, False if UVA

        Returns:
            str: Icon character representing the status
        """
        if value is None:
            return ICON_ERROR  # Sensor error or no reading

        thresholds = self.UVB_THRESHOLDS if is_uvb else self.UVA_THRESHOLDS

        if value < thresholds['low']:
            return ICON_TOO_LOW    # Arrow pointing up - needs more UV
        elif value > thresholds['high']:
            return ICON_TOO_HIGH   # Sunglasses - too bright/high UV
        else:
            return ICON_GOOD       # Just right - happy face

    def create_display_group(self, temp, humidity, uva, uvb, uvc, light_status, heat_status):
        group = displayio.Group()

        # Top row - Time and Humidity
        current_time = datetime.now().strftime("%H:%M")
        clock_icon = label.Label(self.icon_font, text=ICON_CLOCK, color=0xFFFFFF,
                            anchor_point=(0.0, 0.0), anchored_position=(4, 4))
        time_label = label.Label(self.regular_font, text=current_time, color=0xFFFFFF,
                            anchor_point=(0.0, 0.0), anchored_position=(20, 4))

        # Humidity on top right
        humidity_text = f"{humidity:4.1f}%" if humidity is not None else "--.-%"
        humidity_icon = label.Label(self.icon_font, text=ICON_TINT, color=0xFFFFFF,
                                anchor_point=(0.0, 0.0), anchored_position=(68, 4))
        humidity_label = label.Label(self.regular_font, text=humidity_text, color=0xFFFFFF,
                                anchor_point=(0.0, 0.0), anchored_position=(84, 4))

        # Second row - Current and Target Temperature
        if temp is not None:
            target_temp = self.get_target_temp()
            temp_text = f"{temp:4.1f}C"
            target_text = f"{target_temp:4.1f}C"
        else:
            temp_text = "--.-C"
            target_text = "--.-C"

        temp_icon = label.Label(self.icon_font, text=ICON_THERMOMETER, color=0xFFFFFF,
                            anchor_point=(0.0, 0.0), anchored_position=(4, 20))
        temp_label = label.Label(self.regular_font, text=temp_text, color=0xFFFFFF,
                            anchor_point=(0.0, 0.0), anchored_position=(20, 20))

        target_icon = label.Label(self.icon_font, text=ICON_TARGET, color=0xFFFFFF,
                                anchor_point=(0.0, 0.0), anchored_position=(68, 20))
        target_label = label.Label(self.regular_font, text=target_text, color=0xFFFFFF,
                                anchor_point=(0.0, 0.0), anchored_position=(84, 20))

        # Third row - UV readings side by side
        # UVA on left, UVB on right
        # UV status display with clear directional indicators
        uva_icon = self.get_uv_status_icon(uva, is_uvb=False)
        uvb_icon = self.get_uv_status_icon(uvb, is_uvb=True)

        # UVA Display
        uva_label = label.Label(
            self.regular_font,
            text="UVA",
            color=0xFFFFFF,
            anchor_point=(0.0, 0.0),
            anchored_position=(4, 36)
        )
        uva_status = label.Label(
            self.icon_font,
            text=uva_icon,
            color=0xFFFFFF,
            anchor_point=(0.0, 0.0),
            anchored_position=(36, 36)
        )

        # UVB Display
        uvb_label = label.Label(
            self.regular_font,
            text="UVB",
            color=0xFFFFFF,
            anchor_point=(0.0, 0.0),
            anchored_position=(68, 36)
        )
        uvb_status = label.Label(
            self.icon_font,
            text=uvb_icon,
            color=0xFFFFFF,
            anchor_point=(0.0, 0.0),
            anchored_position=(100, 36)
        )

        # Bottom row - Status and Schedule
        status_text = f"{'L:ON ' if light_status else 'L:OFF'} {'H:ON' if heat_status else 'H:OFF'}"
        status_label = label.Label(self.regular_font, text=status_text, color=0xFFFFFF,
                                anchor_point=(0.0, 0.0), anchored_position=(4, 52))

        next_state, next_time = self.get_next_transition()
        time_until = self.format_time_until(next_time)
        schedule_text = f"{next_state} {time_until}"
        schedule_label = label.Label(self.regular_font, text=schedule_text, color=0xFFFFFF,
                                anchor_point=(1.0, 0.0),
                                anchored_position=(124, 52))

        # Add all elements to group
        for element in [
            clock_icon, time_label,         # Top left
            humidity_icon, humidity_label,  # Top right
            temp_icon, temp_label,          # Second row left
            target_icon, target_label,      # Second row right
            uva_label, uva_status,          # Third row left
            uvb_label, uvb_status,          # Third row right
            status_label, schedule_label    # Bottom row
        ]:
            group.append(element)

        return group

    def run(self):
        try:
            self.update_display(None, None, None, None, None, False, False)

            while True:
                temp, humidity = self.read_sensor()
                uva, uvb, uvc = self.read_uv()

                if temp is not None and humidity is not None:
                    light_status = self.control_light()
                    heat_status = self.control_heat(temp)
                    self.update_display(temp, humidity, uva, uvb, uvc,
                                      light_status, heat_status)
                time.sleep(2)

        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            GPIO.cleanup()

    def read_sensor(self):
        try:
            self.bus.write_i2c_block_data(0x44, 0x2C, [0x06])
            time.sleep(0.5)
            data = self.bus.read_i2c_block_data(0x44, 0x00, 6)

            temp = data[0] * 256 + data[1]
            cTemp = -45 + (175 * temp / 65535.0)
            humidity = 100 * (data[3] * 256 + data[4]) / 65535.0

            return cTemp, humidity
        except Exception as e:
            print(f"Sensor read error: {e}")
            return None, None

    def read_uv(self):
        try:
            uva, uvb, uvc, temp = self.uv_sensor.values
            return uva, uvb, uvc
        except Exception as e:
            print(f"UV sensor read error: {e}")
            return None, None, None

    def update_display(self, temp, humidity, uva, uvb, uvc, light_status, heat_status):
        """
        Update the display with current sensor readings and status.

        Args:
            temp (float): Temperature reading
            humidity (float): Humidity reading
            uva (float): UVA reading
            uvb (float): UVB reading
            uvc (float): UVC reading
            light_status (bool): Light relay status
            heat_status (bool): Heat relay status
        """
        new_group = self.create_display_group(temp, humidity, uva, uvb, uvc,
                                            light_status, heat_status)
        self.display.root_group = new_group

    def control_light(self):
        current_hour = datetime.now().hour
        should_be_on = LIGHT_ON_HOUR <= current_hour < LIGHT_OFF_HOUR
        GPIO.output(LIGHT_RELAY, GPIO.HIGH if should_be_on else GPIO.LOW)
        return should_be_on

    def control_heat(self, current_temp):
        if current_temp is None:
            return False

        target_temp = self.get_target_temp()

        if current_temp < (target_temp - TEMP_TOLERANCE):
            GPIO.output(HEAT_RELAY, GPIO.HIGH)
            return True
        elif current_temp > (target_temp + TEMP_TOLERANCE):
            GPIO.output(HEAT_RELAY, GPIO.LOW)
            return False
        return GPIO.input(HEAT_RELAY)



def main():
    controller = GeckoController()
    controller.run()

if __name__ == "__main__":
    main()
