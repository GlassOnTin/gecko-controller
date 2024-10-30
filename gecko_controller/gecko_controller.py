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

# Get the directory where the module is installed
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(MODULE_DIR, "fonts", "forkawesome-12.pcf")

# GPIO Setup
GPIO.setmode(GPIO.BCM)
LIGHT_RELAY = 4
HEAT_RELAY = 17
DISPLAY_RESET = 21

# Configure GPIO pins
GPIO.setup(LIGHT_RELAY, GPIO.OUT)
GPIO.setup(HEAT_RELAY, GPIO.OUT)
GPIO.setup(DISPLAY_RESET, GPIO.OUT)
GPIO.output(DISPLAY_RESET, GPIO.HIGH)  # Start with reset inactive

# Temperature Settings
MIN_TEMP = 15.0
DAY_TEMP = 30.0
TEMP_TOLERANCE = 0.5

# Time Settings
LIGHT_ON_HOUR = 6
LIGHT_OFF_HOUR = 18

# Icon characters from Fork Awesome
ICON_CLOCK = "\uf017"
ICON_LIGHTBULB = "\uf0eb"
ICON_THERMOMETER = "\uf2c9"
ICON_TINT = "\uf043"  # Water drop for humidity
ICON_TARGET = "\uf140"  # Target/bullseye for target temperature

class GeckoController:
    def __init__(self):
        self.setup_display()
        self.bus = smbus.SMBus(1)
        # Load the Fork Awesome font from the package directory
        self.icon_font = bitmap_font.load_font(FONT_PATH)
        self.regular_font = terminalio.FONT

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

    def create_display_group(self, temp, humidity, light_status, heat_status):
        """Create a fresh display group with current values"""
        group = displayio.Group()

        # Current time with clock icon
        current_time = datetime.now().strftime("%H:%M")
        clock_icon = label.Label(
            self.icon_font,
            text=ICON_CLOCK,
            color=0xFFFFFF,
            anchor_point=(0.0, 0.0),
            anchored_position=(4, 4),
            base_alignment=True
        )
        time_label = label.Label(
            self.regular_font,
            text=current_time,
            color=0xFFFFFF,
            anchor_point=(0.0, 0.0),
            anchored_position=(20, 4),
            base_alignment=True
        )

        # Temperature with current and target values
        if temp is not None:
            target_temp = self.get_target_temp()
            temp_text = f"{temp:4.1f}C"
            target_text = f"→{target_temp:4.1f}C"
        else:
            temp_text = "--.-C"
            target_text = "→--.-C"

        temp_icon = label.Label(
            self.icon_font,
            text=ICON_THERMOMETER,
            color=0xFFFFFF,
            anchor_point=(0.0, 0.0),
            anchored_position=(4, 20),
            base_alignment=True
        )
        temp_label = label.Label(
            self.regular_font,
            text=temp_text,
            color=0xFFFFFF,
            anchor_point=(0.0, 0.0),
            anchored_position=(20, 20),
            base_alignment=True
        )
        target_icon = label.Label(
            self.icon_font,
            text=ICON_TARGET,
            color=0xFFFFFF,
            anchor_point=(0.0, 0.0),
            anchored_position=(65, 20),
            base_alignment=True
        )
        target_label = label.Label(
            self.regular_font,
            text=target_text,
            color=0xFFFFFF,
            anchor_point=(0.0, 0.0),
            anchored_position=(81, 20),
            base_alignment=True
        )

        # Humidity
        humidity_text = f"{humidity:4.1f}%" if humidity is not None else "--.-%"
        humidity_icon = label.Label(
            self.icon_font,
            text=ICON_TINT,
            color=0xFFFFFF,
            anchor_point=(0.0, 0.0),
            anchored_position=(4, 36),
            base_alignment=True
        )
        humidity_label = label.Label(
            self.regular_font,
            text=humidity_text,
            color=0xFFFFFF,
            anchor_point=(0.0, 0.0),
            anchored_position=(20, 36),
            base_alignment=True
        )

        # Light and heat status
        light_icon = label.Label(
            self.icon_font,
            text=ICON_LIGHTBULB,
            color=0xFFFFFF,
            anchor_point=(0.0, 0.0),
            anchored_position=(65, 36),
            base_alignment=True
        )
        status_text = f"{'ON ' if light_status else 'OFF'}"
        light_label = label.Label(
            self.regular_font,
            text=status_text,
            color=0xFFFFFF,
            anchor_point=(0.0, 0.0),
            anchored_position=(81, 36),
            base_alignment=True
        )

        # Heat status on its own line
        heat_label = label.Label(
            self.regular_font,
            text=f"{'ON ' if heat_status else 'OFF'}",
            color=0xFFFFFF,
            anchor_point=(0.0, 0.0),
            anchored_position=(4, 52),
            base_alignment=True
        )

        # Next transition time
        next_state, next_time = self.get_next_transition()
        time_until = self.format_time_until(next_time)
        schedule_text = f"{next_state} in {time_until}"
        schedule_label = label.Label(
            self.regular_font,
            text=schedule_text,
            color=0xFFFFFF,
            anchor_point=(0.0, 0.0),
            anchored_position=(32, 52),
            base_alignment=True
        )

        # Add all elements to the group
        group.append(clock_icon)
        group.append(time_label)
        group.append(temp_icon)
        group.append(temp_label)
        group.append(target_icon)
        group.append(target_label)
        group.append(humidity_icon)
        group.append(humidity_label)
        group.append(light_icon)
        group.append(light_label)
        group.append(heat_label)
        group.append(schedule_label)

        return group

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

    def update_display(self, temp, humidity, light_status, heat_status):
        new_group = self.create_display_group(temp, humidity, light_status, heat_status)
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

    def run(self):
        try:
            self.update_display(None, None, False, False)

            while True:
                temp, humidity = self.read_sensor()
                if temp is not None and humidity is not None:
                    light_status = self.control_light()
                    heat_status = self.control_heat(temp)
                    self.update_display(temp, humidity, light_status, heat_status)
                time.sleep(2)

        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            GPIO.cleanup()

def main():
    controller = GeckoController()
    controller.run()

if __name__ == "__main__":
    main()
