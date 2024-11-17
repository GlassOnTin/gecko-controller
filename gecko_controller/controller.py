#!/usr/bin/env python3
import os
import time
import math
import smbus2
import RPi.GPIO as GPIO
import logging
import logging.handlers
from datetime import datetime, timedelta, time as datetime_time
from PIL import Image, ImageDraw, ImageFont
import pathlib
from typing import Tuple, Optional
from pathlib import Path


# Constants for logging
LOG_DIR = "/var/log/gecko-controller"
LOG_FILE = "readings.csv"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB per file
LOG_BACKUP_COUNT = 5  # Keep 5 rotated files
LOG_INTERVAL = 60  # seconds

# Get the directory where the module is installed
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

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


# Font loading helper
def load_font(name: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a font, falling back to default if not found"""
    try:
        font_path = pathlib.Path(MODULE_DIR) / "fonts" / name
        return ImageFont.truetype(str(font_path), size)
    except Exception as e:
        print(f"Warning: Could not load font {name}: {e}")
        return ImageFont.load_default()

class SSH1106Display:
    def __init__(self, i2c_addr=0x3C, width=128, height=64):
        self.addr = i2c_addr
        self.width = width
        self.height = height
        self.pages = height // 8
        self.buffer = [0] * (width * self.pages)
        self.bus = smbus2.SMBus(1)
        self.init_display()

    def init_display(self):
        """Initialize the SSH1106 display with correct rotation"""
        init_sequence = [
            0xAE,   # display off
            0xD5, 0x80,  # set display clock
            0xA8, 0x3F,  # set multiplex ratio
            0xD3, 0x00,  # set display offset
            0x40,   # set start line to 0
            0x8D, 0x14,  # enable charge pump
            0x20, 0x00,  # memory addressing mode
            0xA0,   # segment remap (0xA1 to flip horizontal)
            0xC0,   # COM scan direction (0xC8 to flip vertical)
            0xDA, 0x12,  # set COM pins
            0x81, 0xFF,  # maximum contrast
            0xD9, 0xF1,  # set pre-charge period
            0xDB, 0x20,  # set VCOMH
            0xA4,   # display all on resume
            0xA6,   # normal display (not inverted)
            0xAF    # display on
        ]
        for cmd in init_sequence:
            self.write_cmd(cmd)

    def show_image(self, image: Image.Image):
        """Display a PIL Image object"""
        # Convert image to 1-bit color and rotate if needed
        if image.mode != '1':
            image = image.convert('1')
        
        # Rotate image 90 degrees clockwise
        image = image.rotate(180, expand=True)
        
        # The SSH1106 has a 132x64 display memory, but only 128x64 is visible
        # Create a new image with the full 132x64 size
        full_image = Image.new('1', (132, 64), 255)  # white background
        
        # Paste the rotated image in the center of the 132x64 frame
        paste_x = (132 - image.width) // 2
        paste_y = (64 - image.height) // 2
        full_image.paste(image, (paste_x, paste_y))
        
        # Set the correct position for the SSH1106
        self.write_cmd(0x02)  # Set lower column address (to center the 128 columns in 132 width)
        self.write_cmd(0x10)  # Set higher column address
        
        # Write display buffer
        for page in range(self.pages):
            self.write_cmd(0xB0 + page)  # Set page address
            for x in range(132):  # Write all 132 columns
                bits = 0
                for bit in range(8):
                    y = page * 8 + bit
                    if y < 64 and x < 132:
                        if full_image.getpixel((x, y)) == 0:  # Black pixel
                            bits |= (1 << bit)
                self.write_data(bits)

    def write_cmd(self, cmd: int):
        """Write a command to the display"""
        self.bus.write_byte_data(self.addr, 0x00, cmd)

    def write_data(self, data: int):
        """Write data to the display"""
        self.bus.write_byte_data(self.addr, 0x40, data)

class GeckoController:
    def __init__(self):
        # Convert time settings from config to datetime.time objects
        self.light_on_time = self.parse_time_setting(LIGHT_ON_TIME)
        self.light_off_time = self.parse_time_setting(LIGHT_OFF_TIME)
        print(f"Light on @ {self.light_on_time}, Light off @ {self.light_off_time}\n")
        
        # Use thresholds from config
        self.UVA_THRESHOLDS = UVA_THRESHOLDS
        self.UVB_THRESHOLDS = UVB_THRESHOLDS
        print(f"UVA Thresholds = {self.UVA_THRESHOLDS}, UVB Thresholds = {self.UVB_THRESHOLDS}\n")
 
        # GPIO Setup
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(LIGHT_RELAY, GPIO.OUT)
        GPIO.setup(HEAT_RELAY, GPIO.OUT)
        
        if hasattr(self, 'DISPLAY_RESET'):
            GPIO.setup(DISPLAY_RESET, GPIO.OUT)
            GPIO.output(DISPLAY_RESET, GPIO.HIGH)  # Start with reset inactive

        self.setup_display()
        self.setup_logging()
        self.last_log_time = 0
        self.bus = smbus2.SMBus(1)
        
        # UV sensor configuration with fallback paths
        try:
            # First try relative import (when installed as package)
            from .as7331 import AS7331, INTEGRATION_TIME_256MS, GAIN_16X
        except ImportError:
            try:
                # Try importing from the same directory as this script
                import os
                import sys
                script_dir = os.path.dirname(os.path.abspath(__file__))
                sys.path.append(script_dir)
                from as7331 import AS7331, INTEGRATION_TIME_256MS, GAIN_16X
            except ImportError:
                print("Warning: AS7331 module not found, UV sensing disabled")
                print(f"Looked in: {script_dir}")
                print("Make sure as7331.py is in the same directory as this script")
                self.uv_sensor = None
            else:
                self.uv_sensor = AS7331(1)
                self.uv_sensor.integration_time = INTEGRATION_TIME_256MS
                self.uv_sensor.gain = GAIN_16X
        else:
            self.uv_sensor = AS7331(1)
            self.uv_sensor.integration_time = INTEGRATION_TIME_256MS
            self.uv_sensor.gain = GAIN_16X

        # Calculate UV correction factor
        self.uv_correction_factor = self.calculate_uv_correction()
        print(f"\nUV Correction Factor: {self.uv_correction_factor:.3f}")
        print(f"Sensor Position: {SENSOR_HEIGHT}m height, {LAMP_DIST_FROM_BACK}m from back")
        print(f"Lamp Height: {ENCLOSURE_HEIGHT}m, Sensor Angle: {SENSOR_ANGLE}°\n")

        # Create an image buffer
        self.image = Image.new('1', (128, 64), 255)  # 255 = white background
        self.draw = ImageDraw.Draw(self.image)

        # Load regular font
        self.regular_font = load_font("DejaVuSans.ttf", 10)

        # Load OpenSymbol font
        try:
            self.icon_font = ImageFont.truetype("/usr/share/fonts/truetype/ancient-scripts/Symbola_hint.ttf", 12)
        except Exception as e:
            print(f"Warning: Could not load Symbola font from default path: {e}")
            print(f"Please install the fonts-symbola package")
            self.icon_font = ImageFont.load_default()
            print("Using default font")

        # OpenSymbol Unicode points for relevant symbols
        self.ICON_CLOCK = "⏲"       
        self.ICON_HUMIDITY = "🌢"         # for humidity 
        self.ICON_THERMOMETER = "🌡"  
        self.ICON_TARGET = "🞋"      
        self.ICON_GOOD = "☺"       
        self.ICON_TOO_LOW = "🌜"     
        self.ICON_TOO_HIGH = "⚠"    
        self.ICON_ERROR = "?"

    @staticmethod
    def parse_time_setting(time_str: str) -> datetime_time:
        """Parse time string in HH:MM format into time object"""
        try:
            if ':' in time_str:
                hours, minutes = map(int, time_str.split(':'))
            else:
                # Backward compatibility for hour-only settings
                hours = int(time_str)
                minutes = 0
            return datetime_time(hours, minutes)
        except (ValueError, TypeError) as e:
            print(f"Error parsing time setting {time_str}: {e}")
            # Default to midnight if invalid
            return datetime_time(0, 0)
            
    def setup_logging(self):
        """Configure logging with rotation"""
        os.makedirs(LOG_DIR, exist_ok=True)
        log_file = Path(LOG_DIR + "/" + LOG_FILE)
        
        # Configure main logger
        self.logger = logging.getLogger("gecko_controller")
        self.logger.setLevel(logging.INFO)
        
        # Create rotating file handler
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=MAX_LOG_SIZE,
            backupCount=LOG_BACKUP_COUNT
        )
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s,%(temp).1f,%(humidity).1f,%(uva).4f,%(uvb).4f,%(uvc).4f,%(light)d,%(heat)d'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def setup_display(self):
        """Initialize the display"""
        self.display = SSH1106Display(i2c_addr=DISPLAY_ADDRESS)

    def get_next_transition(self) -> Tuple[str, datetime]:
        """Calculate time until next light state change"""
        now = datetime.now()
        current_time = now.time()
        
        # Create datetime objects for today's on/off times
        today_on = now.replace(
            hour=self.light_on_time.hour,
            minute=self.light_on_time.minute,
            second=0,
            microsecond=0
        )
        today_off = now.replace(
            hour=self.light_off_time.hour,
            minute=self.light_off_time.minute,
            second=0,
            microsecond=0
        )
        
        if self.light_on_time <= current_time < self.light_off_time:
            # Lights are on, calculate time until off
            next_time = today_off
            if next_time < now:
                next_time += timedelta(days=1)
            return "→OFF", next_time
        else:
            # Lights are off, calculate time until on
            next_time = today_on
            if next_time < now:
                next_time += timedelta(days=1)
            return "→ON", next_time

    def format_time_until(self, target_time: datetime) -> str:
        """Format the time until the next transition"""
        now = datetime.now()
        diff = target_time - now
        hours = int(diff.total_seconds() // 3600)
        minutes = int((diff.total_seconds() % 3600) // 60)
        return f"{hours}h{minutes:02d}m"

    def calculate_uv_correction(self):
        """Calculate UV correction factor based on geometry"""       
        # Calculate distances and angles
        sensor_to_lamp_horiz = LAMP_DIST_FROM_BACK  # horizontal distance from sensor to lamp
        sensor_to_lamp_vert = ENCLOSURE_HEIGHT - SENSOR_HEIGHT  # vertical distance
        
        # Direct distance from sensor to lamp
        direct_distance = math.sqrt(sensor_to_lamp_horiz**2 + sensor_to_lamp_vert**2)
        
        # Angle between sensor normal and lamp
        lamp_angle = math.degrees(math.atan2(sensor_to_lamp_vert, sensor_to_lamp_horiz))
        effective_angle = abs(lamp_angle - SENSOR_ANGLE)
        
        # Cosine correction for sensor angle
        cosine_factor = math.cos(math.radians(effective_angle))
        
        # Inverse square law correction for distance
        # Normalize to a reference height of 30cm (typical basking height)
        distance_factor = (0.3 / direct_distance)**2
        
        # Combined correction factor
        correction_factor = 1 / (cosine_factor * distance_factor)
        
        return correction_factor

    def get_uv_status_icon(self, value: Optional[float], is_uvb: bool = False) -> str:
        """Get status icon for UV readings"""
        if value is None:
            return self.ICON_ERROR

        thresholds = self.UVB_THRESHOLDS if is_uvb else self.UVA_THRESHOLDS

        if value < thresholds['low']:
            return self.ICON_TOO_LOW
        elif value > thresholds['high']:
            return self.ICON_TOO_HIGH
        else:
            return self.ICON_GOOD

    def create_display_group(self, temp, humidity, uva, uvb, uvc, light_status, heat_status):
        """Create a new display buffer with all information"""
        # Clear the image
        self.draw.rectangle((0, 0, 128, 64), fill=255)  # White background
        
        # Top row - Time and Humidity
        current_time = datetime.now().strftime("%H:%M")
        self.draw.text((4, 4), self.ICON_CLOCK, font=self.icon_font, fill=0)
        self.draw.text((20, 4), current_time, font=self.regular_font, fill=0)

        # Humidity
        humidity_text = f"{humidity:4.1f}%" if humidity is not None else "--.-%"
        self.draw.text((68, 4), self.ICON_HUMIDITY, font=self.icon_font, fill=0)
        self.draw.text((84, 4), humidity_text, font=self.regular_font, fill=0)

        # Temperature
        if temp is not None:
            target_temp = self.get_target_temp()
            temp_text = f"{temp:4.1f}C"
            target_text = f"{target_temp:4.1f}C"
        else:
            temp_text = "--.-C"
            target_text = "--.-C"

        self.draw.text((4, 20), self.ICON_THERMOMETER, font=self.icon_font, fill=0)
        self.draw.text((20, 20), temp_text, font=self.regular_font, fill=0)
        self.draw.text((68, 20), self.ICON_TARGET, font=self.icon_font, fill=0)
        self.draw.text((84, 20), target_text, font=self.regular_font, fill=0)

        # UV readings
        uva_icon = self.get_uv_status_icon(uva, is_uvb=False)
        uvb_icon = self.get_uv_status_icon(uvb, is_uvb=True)
        
        self.draw.text((4, 36), "UVA", font=self.regular_font, fill=0)
        self.draw.text((36, 36), uva_icon, font=self.icon_font, fill=0)
        self.draw.text((68, 36), "UVB", font=self.regular_font, fill=0)
        self.draw.text((100, 36), uvb_icon, font=self.icon_font, fill=0)

        # Status and Schedule
        status_text = f"{'L:ON ' if light_status else 'L:OFF'} {'H:ON' if heat_status else 'H:OFF'}"
        self.draw.text((4, 52), status_text, font=self.regular_font, fill=0)

        next_state, next_time = self.get_next_transition()
        time_until = self.format_time_until(next_time)
        schedule_text = f"{next_state} {time_until}"
        
        # Right-align the schedule text
        schedule_width = self.draw.textlength(schedule_text, font=self.regular_font)
        self.draw.text((124 - schedule_width, 52), schedule_text, font=self.regular_font, fill=0)

        # Update the display
        self.display.show_image(self.image)

    def log_readings(self, temp, humidity, uva, uvb, uvc, light_status, heat_status):
        """Log readings if enough time has passed"""
        current_time = time.time()
        if current_time - self.last_log_time >= LOG_INTERVAL:
            self.logger.info(
                "",
                extra={
                    'temp': temp if temp is not None else -1,
                    'humidity': humidity if humidity is not None else -1,
                    'uva': uva if uva is not None else -1,
                    'uvb': uvb if uvb is not None else -1,
                    'uvc': uvc if uvc is not None else -1,
                    'light': 1 if light_status else 0,
                    'heat': 1 if heat_status else 0
                }
            )
            self.last_log_time = current_time

    def read_sensor(self) -> Tuple[Optional[float], Optional[float]]:
        """Read temperature and humidity from the sensor"""
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

    def read_uv(self) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Read UV values from the sensor and apply geometric correction"""
        try:
            if self.uv_sensor is None:
                return None, None, None
            uva, uvb, uvc, temp = self.uv_sensor.values
            
            # Apply correction factor
            if uva is not None:
                uva = uva * self.uv_correction_factor
            if uvb is not None:
                uvb = uvb * self.uv_correction_factor
            if uvc is not None:
                uvc = uvc * self.uv_correction_factor
            
            return uva, uvb, uvc
        except Exception as e:
            print(f"UV sensor read error: {e}")
            return None, None, None

    def get_target_temp(self) -> float:
        """Get the current target temperature based on time of day"""
        current_time = datetime.now().time()
        return DAY_TEMP if self.light_on_time <= current_time < self.light_off_time else MIN_TEMP

    def control_light(self) -> bool:
        """Control the light relay based on time"""
        current_time = datetime.now().time()
        should_be_on = self.light_on_time <= current_time < self.light_off_time
        GPIO.output(LIGHT_RELAY, GPIO.HIGH if should_be_on else GPIO.LOW)
        return should_be_on
 
    def control_heat(self, current_temp: Optional[float]) -> bool:
        """Control the heat relay based on temperature"""
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

    def update_display(self, temp, humidity, uva, uvb, uvc, light_status, heat_status):
        """Update the display with current readings"""
        self.create_display_group(temp, humidity, uva, uvb, uvc, light_status, heat_status)

    def run(self):
        """Main control loop"""
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
                    self.log_readings(temp, humidity, uva, uvb, uvc,
                                    light_status, heat_status)
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
