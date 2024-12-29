#!/usr/bin/env python3
import asyncio
import os
import sys
import signal
import time
import math
import pwd
import grp
import smbus2
import RPi.GPIO as GPIO
import traceback
import logging
import logging.handlers
from datetime import datetime, timedelta, time as datetime_time
from PIL import Image, ImageDraw, ImageFont
import pathlib
from typing import Tuple, Optional
from pathlib import Path

# Add the project root to the Python path
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from gecko_controller.ssh1106 import SSH1106Display
from gecko_controller.display_socket import DisplaySocketServer
from gecko_controller.config_loader import load_config

# Constants for logging
LOG_DIR = "/var/log/gecko-controller"
LOG_FILE = "readings.csv"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB per file
LOG_BACKUP_COUNT = 5  # Keep 5 rotated files
LOG_INTERVAL = 60  # seconds

# Get the directory where the module is installed
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load config before class definition
config = load_config()
if config is None:
    if __name__ == "__main__":
        sys.exit(1)
    else:
        raise ImportError("No configuration found")

class GeckoController:
    def __init__(self, test_mode=False):
        self.config = config
        self.test_mode = test_mode
        self.display_socket = None

        self.logger = logging.getLogger(__name__)

        if not self.test_mode:
            self.setup_gpio()
            self.setup_display()
            self.setup_logging()
            self.last_log_time = 0
            self.bus = smbus2.SMBus(1)
            self.setup_uv_sensor()
            self.image = Image.new('1', (128, 64), 255)
            self.draw = ImageDraw.Draw(self.image)
            self.regular_font = self.load_font("DejaVuSans.ttf", 10)
            self.icon_font = self.load_font("Symbola_hint.ttf", 12)

        self.light_on_time = self.parse_time_setting(self.config.LIGHT_ON_TIME)
        self.light_off_time = self.parse_time_setting(self.config.LIGHT_OFF_TIME)
        self.UVA_THRESHOLDS = self.config.UVA_THRESHOLDS
        self.UVB_THRESHOLDS = self.config.UVB_THRESHOLDS
        self.uv_correction_factor = self.calculate_uv_correction()

        self.ICON_CLOCK = "⏲"
        self.ICON_HUMIDITY = "🌢"
        self.ICON_THERMOMETER = "🌡"
        self.ICON_TARGET = "🞋"
        self.ICON_GOOD = "☺"
        self.ICON_TOO_LOW = "🌜"
        self.ICON_TOO_HIGH = "⚠"
        self.ICON_ERROR = "?"

    def setup_gpio(self):
        """Set up GPIO with proper error handling"""
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            # Check GPIO access
            if not os.access("/dev/gpiomem", os.R_OK | os.W_OK):
                raise PermissionError("No access to /dev/gpiomem. Ensure user is in gpio group.")

            # Set up pins
            for pin in [self.config.LIGHT_RELAY, self.config.HEAT_RELAY]:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)  # Initialize to OFF

            if hasattr(self.config, 'DISPLAY_RESET'):
                GPIO.setup(self.config.DISPLAY_RESET, GPIO.OUT)
                GPIO.output(self.config.DISPLAY_RESET, GPIO.HIGH)

        except Exception as e:
            self.logger.error(f"GPIO setup failed: {e}")
            raise

    def setup_display(self):
        """Initialize the OLED display"""
        try:
            self.display = SSH1106Display(i2c_addr=self.config.DISPLAY_ADDRESS)
        except Exception as e:
            self.logger.error(f"Failed to initialize display: {e}")
            raise

    async def update_display(self, temp, humidity, uva, uvb, uvc, light_status, heat_status):
        """Update display with proper async handling"""
        if not hasattr(self, 'last_display_update'):
            self.last_display_update = 0

        current_time = time.time()
        if current_time - self.last_display_update < 0.1:
            return

        try:
            self.logger.info("Creating display buffer...")

            # Run display group creation in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.create_display_group,
                temp, humidity, uva, uvb, uvc, light_status, heat_status
            )

            # Update physical display with timeout protection
            if self.display:
                self.logger.info("Updating physical display...")
                try:
                    async with asyncio.timeout(1.0):
                        await loop.run_in_executor(
                            None,
                            lambda: self.display.show_image(self.image)
                        )
                        self.logger.info("Physical display updated")
                except asyncio.TimeoutError:
                    self.logger.error("Physical display update timed out")
                    self.display = None

            # Update web interface
            if self.display_socket:
                self.logger.info("Sending to web interface...")
                await self.display_socket.send_image(self.image)
                self.logger.info("Web interface updated")

            self.last_display_update = current_time

        except Exception as e:
            self.logger.error(f"Display update failed: {e}", exc_info=True)
            if current_time - self.last_display_update > 5:
                try:
                    self.setup_display()
                except Exception as setup_error:
                    self.logger.error(f"Display setup retry failed: {setup_error}")

    # Font loading helper
    def load_font(self, name: str, size: int) -> ImageFont.FreeTypeFont:
        """Load a font, falling back to default if not found"""
        try:
            font_path = pathlib.Path(MODULE_DIR) / "fonts" / name
            return ImageFont.truetype(str(font_path), size)
        except Exception as e:
            print(f"Warning: Could not load font {name}: {e}")
            return ImageFont.load_default()

    def setup_uv_sensor(self):
        """Set up the AS7331 UV sensor with appropriate configuration"""
        try:
            # First attempt to import the module
            try:
                from gecko_controller.as7331 import (
                    AS7331,
                    INTEGRATION_TIME_256MS,
                    GAIN_16X,
                    MEASUREMENT_MODE_CONTINUOUS,
                    MEASUREMENT_MODE_COMMAND
                )
            except ImportError as e:
                self.logger.error(f"Failed to import AS7331 module: {e}")
                self.uv_sensor = None
                return

            # Try to detect sensor on I2C bus
            try:
                # Try to scan I2C bus first
                import subprocess
                result = subprocess.run(['i2cdetect', '-y', '1'],
                                    capture_output=True, text=True)
                self.logger.debug(f"I2C bus scan:\n{result.stdout}")
            except Exception as e:
                self.logger.warning(f"Could not scan I2C bus: {e}")

            # Initialize sensor
            try:
                self.logger.info("Initializing UV sensor...")
                self.uv_sensor = AS7331(1)  # Initialize with I2C bus 1

                # Configure sensor
                self.uv_sensor.integration_time = INTEGRATION_TIME_256MS
                self.uv_sensor.gain = GAIN_16X
                self.uv_sensor.measurement_mode = MEASUREMENT_MODE_COMMAND  #MEASUREMENT_MODE_CONTINUOUS

                # Save configuration
                self.int_time = INTEGRATION_TIME_256MS
                self.gain = GAIN_16X
                self.meas_mode = MEASUREMENT_MODE_CONTINUOUS

                # Verify configuration
                self.logger.info(
                    f"UV Sensor initialized successfully:\n"
                    f"  Measurement mode: {self.uv_sensor.measurement_mode_as_string}\n"
                    f"  Integration time: {self.uv_sensor.integration_time_as_string}\n"
                    f"  Gain: {self.uv_sensor.gain_as_string}\n"
                    f"  Standby state: {self.uv_sensor.standby_state}"
                )

                # Test read
                uva, uvb, uvc, temp = self.uv_sensor.values
                self.logger.info(f"Initial readings - UVA: {uva}, UVB: {uvb}, UVC: {uvc}, Temp: {temp}")

            except Exception as e:
                self.logger.error(f"Failed to initialize UV sensor: {e}")
                self.logger.debug(f"Stack trace: {traceback.format_exc()}")
                self.logger.info("Please check:\n"
                            "1. I2C connections\n"
                            "2. Sensor power\n"
                            "3. I2C address conflicts\n"
                            "4. Bus speed settings")
                self.uv_sensor = None
                self.int_time = None
                self.gain = None
                self.meas_mode = None

        except Exception as e:
            self.logger.error(f"Unexpected error in UV sensor setup: {e}")
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")
            self.uv_sensor = None

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
        """Configure logging with rotation and proper permissions"""
        try:
            # Get user/group IDs first
            uid = pwd.getpwnam("gecko-controller").pw_uid
            gid = grp.getgrnam("gpio").gr_gid

            # Ensure log directory exists with proper permissions
            if not os.path.exists(LOG_DIR):
                os.makedirs(LOG_DIR, mode=0o755)
                # Set ownership
                os.chown(LOG_DIR, uid, gid)

            log_file = Path(LOG_DIR + "/" + LOG_FILE)

            # If log file exists, ensure proper permissions
            if log_file.exists():
                os.chown(log_file, uid, gid)
                os.chmod(log_file, 0o644)

            # Rest of the logging setup remains the same...
            # Configure main logger for system messages
            self.logger = logging.getLogger("gecko_controller")
            self.logger.setLevel(logging.INFO)

            # Configure readings logger for sensor data
            self.readings_logger = logging.getLogger("gecko_controller.readings")
            self.readings_logger.setLevel(logging.INFO)

            # Create rotating file handler for readings
            readings_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=MAX_LOG_SIZE,
                backupCount=LOG_BACKUP_COUNT,
                mode='a'  # append mode
            )

            # Create formatter for readings
            readings_formatter = logging.Formatter(
                '%(asctime)s,%(temp).1f,%(humidity).1f,%(uva).4f,%(uvb).4f,%(uvc).4f,%(light)d,%(heat)d'
            )
            readings_handler.setFormatter(readings_formatter)
            self.readings_logger.addHandler(readings_handler)

            # Create console handler for system messages
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

            # Ensure all new log files get correct permissions
            if log_file.exists():
                os.chown(log_file, uid, gid)
                os.chmod(log_file, 0o644)

        except Exception as e:
            print(f"Error setting up logging: {e}")
            raise

    async def setup_socket(self):
        """Initialize display socket server if not already running"""
        try:
            if self.display_socket is None:
                self.display_socket = DisplaySocketServer()
                await self.display_socket.start()
                self.logger.info("Display socket server initialized and started")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize display socket: {e}", exc_info=True)
            self.display_socket = None
            return False

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

    def calculate_uv_correction(self, sensor_height=None, lamp_dist=None, enclosure_height=None, sensor_angle=None):
        """
        Calculate UV correction factor based on geometry

        Args:
            sensor_height (float, optional): Height of sensor in meters
            lamp_dist (float, optional): Distance from back wall in meters
            enclosure_height (float, optional): Height of enclosure in meters
            sensor_angle (float, optional): Angle of sensor in degrees

        Returns:
            float: Correction factor for UV readings
        """
        # Use provided values or fall back to config values
        sensor_height = sensor_height if sensor_height is not None else self.config.SENSOR_HEIGHT
        lamp_dist = lamp_dist if lamp_dist is not None else self.config.LAMP_DIST_FROM_BACK
        enclosure_height = enclosure_height if enclosure_height is not None else self.config.ENCLOSURE_HEIGHT
        sensor_angle = sensor_angle if sensor_angle is not None else self.config.SENSOR_ANGLE

        # Calculate distances and angles
        sensor_to_lamp_horiz = lamp_dist  # horizontal distance from sensor to lamp
        sensor_to_lamp_vert = enclosure_height - sensor_height  # vertical distance

        # Direct distance from sensor to lamp
        direct_distance = math.sqrt(sensor_to_lamp_horiz**2 + sensor_to_lamp_vert**2)

        # Angle between sensor normal and lamp
        lamp_angle = math.degrees(math.atan2(sensor_to_lamp_vert, sensor_to_lamp_horiz))
        effective_angle = abs(lamp_angle - sensor_angle)

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

    def log_readings(self, temp, humidity, uva, uvb, uvc, light_status, heat_status):
        """Log readings if enough time has passed"""
        current_time = time.time()
        if current_time - self.last_log_time >= LOG_INTERVAL:
            self.readings_logger.info(
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
            # First check if bus is accessible at all
            if not hasattr(self, 'bus') or self.bus is None:
                self.logger.error("I2C bus not initialized")
                return None, None

            # Read with timeout protection
            try:
                # Try to write measurement command
                self.bus.write_i2c_block_data(0x44, 0x2C, [0x06])

                # Use shorter sleep - 100ms is typically enough for SHT31
                time.sleep(0.1)

                # Read data with retry
                retries = 3
                for attempt in range(retries):
                    try:
                        data = self.bus.read_i2c_block_data(0x44, 0x00, 6)
                        break
                    except OSError as e:
                        if attempt == retries - 1:
                            raise
                        time.sleep(0.1)

                # Convert raw data to temperature and humidity
                temp = data[0] * 256 + data[1]
                cTemp = -45 + (175 * temp / 65535.0)
                humidity = 100 * (data[3] * 256 + data[4]) / 65535.0

                # Basic sanity check on values
                if not (-40 <= cTemp <= 125) or not (0 <= humidity <= 100):
                    self.logger.warning(f"Sensor values out of range: T={cTemp}°C, RH={humidity}%")
                    return None, None

                self.logger.debug(f"Read sensor: T={cTemp:.1f}°C, RH={humidity:.1f}%")
                return cTemp, humidity

            except OSError as e:
                self.logger.error(f"I2C communication error: {e}")
                # Try to reset the I2C bus if we get repeated errors
                try:
                    self.bus.close()
                    time.sleep(0.1)
                    self.bus = smbus2.SMBus(1)
                except Exception as reset_error:
                    self.logger.error(f"Failed to reset I2C bus: {reset_error}")
                return None, None

        except Exception as e:
            self.logger.error(f"Sensor read error: {e}")
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")
            return None, None

    async def read_uv(self) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """Read UV values from AS7331 sensor and apply geometric correction."""
        try:
            if self.uv_sensor is None:
                self.logger.error("UV sensor not initialized")
                return None, None, None

            # Maximum retries for sensor read
            retries = 3
            last_error = None

            for attempt in range(retries):
                try:
                    # Use async version with timeout
                    async with asyncio.timeout(5.0):  # 5 second overall timeout
                        uva, uvb, uvc, temp = await self.uv_sensor.async_get_values()

                    # Validate raw readings
                    if any(v is not None and (v < 0 or v > 1000000) for v in (uva, uvb, uvc)):
                        self.logger.warning(f"UV values out of expected range: UVA={uva}, UVB={uvb}, UVC={uvc}")
                        continue

                    # Apply geometric correction and round to reasonable precision
                    corrected_values = []
                    for value in (uva, uvb, uvc):
                        if value is not None:
                            # Apply correction and round to 3 decimal places
                            corrected = round(value * self.uv_correction_factor, 3)
                            # Sanity check on corrected values
                            if corrected > 100000:  # Unreasonably high UV
                                self.logger.warning(f"Corrected UV value too high: {corrected} μW/cm²")
                                corrected = None
                        else:
                            corrected = None
                        corrected_values.append(corrected)

                    return tuple(corrected_values)

                except asyncio.TimeoutError:
                    last_error = "Timeout reading UV sensor"
                    self.logger.warning(f"UV sensor read attempt {attempt + 1}/{retries} timed out")
                    await asyncio.sleep(0.5)  # Short delay between retries
                    continue

                except Exception as e:
                    last_error = str(e)
                    self.logger.warning(f"UV sensor read attempt {attempt + 1}/{retries} failed: {e}")
                    if attempt < retries - 1:
                        await asyncio.sleep(0.5)
                    continue

            # If we get here, all retries failed
            if last_error:
                self.logger.error(f"UV sensor read failed after {retries} attempts: {last_error}")
                # Try to recover sensor
                try:
                    self.setup_uv_sensor()
                    self.logger.info("UV sensor reinitialized after failures")
                except Exception as reinit_error:
                    self.logger.error(f"Failed to reinitialize UV sensor: {reinit_error}")

            return None, None, None

        except Exception as e:
            self.logger.error(f"Unexpected error reading UV sensor: {e}")
            self.logger.debug(f"Stack trace: {traceback.format_exc()}")
            return None, None, None

    def get_target_temp(self) -> float:
        """Get the current target temperature based on time of day"""
        current_time = datetime.now().time()
        return self.config.DAY_TEMP if self.light_on_time <= current_time < self.light_off_time else self.config.MIN_TEMP

    def control_light(self) -> bool:
        """Control the light relay based on time"""
        current_time = datetime.now().time()
        should_be_on = self.light_on_time <= current_time < self.light_off_time
        GPIO.output(self.config.LIGHT_RELAY, GPIO.HIGH if should_be_on else GPIO.LOW)
        return should_be_on
 
    def control_heat(self, current_temp: Optional[float]) -> bool:
        """Control the heat relay based on temperature"""
        if current_temp is None:
            return False

        target_temp = self.get_target_temp()

        if current_temp < (target_temp - self.config.TEMP_TOLERANCE):
            GPIO.output(self.config.HEAT_RELAY, GPIO.HIGH)
            return True
        elif current_temp > (target_temp + self.config.TEMP_TOLERANCE):
            GPIO.output(self.config.HEAT_RELAY, GPIO.LOW)
            return False
        return GPIO.input(self.config.HEAT_RELAY)

    async def cleanup(self):
        """Cleanup resources before shutdown"""
        try:
            self.logger.info("Starting cleanup...")

            # Cancel all running tasks if they exist
            if hasattr(self, 'tasks'):
                for task in self.tasks:
                    if not task.done():
                        self.logger.info(f"Cancelling task: {task.get_name()}")
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass

            # The display singleton will handle its own cleanup
            self.display = None

            # Stop the socket server if it exists
            if hasattr(self, 'display_socket') and self.display_socket:
                self.logger.info("Stopping display socket...")
                await self.display_socket.stop()
                self.display_socket = None

            # Cleanup GPIO
            self.logger.info("Cleaning up GPIO...")
            GPIO.cleanup()

            self.logger.info("Cleanup completed")

        except Exception as e:
            self.logger.error(f"Cleanup error: {e}", exc_info=True)

    async def run(self):
        """Main run loop with concurrent task handling"""
        try:
            # Initialize display socket
            socket_initialized = await self.setup_socket()
            if not socket_initialized:
                self.logger.warning("Running without display socket")
                self.tasks = [
                    asyncio.create_task(self.control_loop(), name='control_loop')
                ]
            else:
                self.logger.info("Starting control and display tasks")
                self.tasks = [
                    asyncio.create_task(self.display_socket.serve_forever(), name='socket_server'),
                    asyncio.create_task(self.control_loop(), name='control_loop')
                ]

            # Run until cancelled
            await asyncio.gather(*self.tasks)

        except asyncio.CancelledError:
            self.logger.info("Received shutdown signal")
        except Exception as e:
            self.logger.error(f"Fatal error in main loop: {e}", exc_info=True)
            raise
        finally:
            await self.cleanup()

    async def control_loop(self):
        """Separated control loop for clarity"""
        self.logger.info("Starting control loop")
        while True:
            try:
                self.logger.info("=== Starting control loop iteration ===")

                # Temperature/Humidity read
                try:
                    self.logger.info("Reading temperature sensor...")
                    start_time = time.time()
                    temp, humidity = self.read_sensor()
                    self.logger.info(f"Temperature read took {time.time() - start_time:.2f}s")
                    if temp is None or humidity is None:
                        self.logger.error("Failed to read temperature/humidity")
                    else:
                        self.logger.info(f"Temperature: {temp:.2f}°C, Humidity: {humidity:.2f}%")
                except Exception as e:
                    self.logger.error(f"Temperature sensor error: {e}")
                    temp, humidity = None, None

                # UV read
                try:
                    self.logger.info("Reading UV sensors...")
                    start_time = time.time()
                    uva, uvb, uvc = await self.read_uv()
                    self.logger.info(f"UV read took {time.time() - start_time:.2f}s")
                    self.logger.info(f"UV levels - A: {uva}, B: {uvb}, C: {uvc}")
                except Exception as e:
                    self.logger.error(f"UV sensor error: {e}", exc_info=True)
                    uva, uvb, uvc = None, None, None

                # Control state updates
                try:
                    self.logger.info("Updating control states...")
                    light_status = self.control_light()
                    heat_status = self.control_heat(temp)
                    self.logger.info(f"Light: {'ON' if light_status else 'OFF'}, Heat: {'ON' if heat_status else 'OFF'}")
                except Exception as e:
                    self.logger.error(f"Control state error: {e}", exc_info=True)
                    light_status = heat_status = False

                # Display update
                try:
                    self.logger.info("Updating display...")
                    start_time = time.time()
                    await self.update_display(temp, humidity, uva, uvb, uvc,
                                        light_status, heat_status)
                    self.logger.info(f"Display update took {time.time() - start_time:.2f}s")
                except Exception as e:
                    self.logger.error(f"Display update error: {e}", exc_info=True)

                self.logger.info("=== Control loop iteration complete, waiting 10s ===")
                await asyncio.sleep(10)

            except Exception as e:
                self.logger.error(f"Critical error in control loop: {e}", exc_info=True)
                await asyncio.sleep(1)  # Brief pause before retry

    async def cleanup(self):
        """Cleanup resources before shutdown with proper task cancellation"""
        try:
            self.logger.info("Starting cleanup...")

            # Set longer timeout for cleanup operations
            cleanup_timeout = 10.0  # 10 seconds total timeout

            async with asyncio.timeout(cleanup_timeout):
                # Cancel all tasks
                pending = [task for task in self.tasks if not task.done()]
                if pending:
                    self.logger.info(f"Cancelling {len(pending)} pending tasks...")
                    for task in pending:
                        task.cancel()

                    # Wait for all tasks to complete or be cancelled
                    await asyncio.gather(*pending, return_exceptions=True)

                # Stop the display socket server if it exists
                if self.display_socket:
                    self.logger.info("Stopping display socket...")
                    try:
                        await asyncio.wait_for(self.display_socket.stop(), timeout=2.0)
                    except asyncio.TimeoutError:
                        self.logger.warning("Display socket stop timed out")

                # Cleanup GPIO
                self.logger.info("Cleaning up GPIO...")
                GPIO.cleanup()

            self.logger.info("Cleanup completed successfully")

        except asyncio.TimeoutError:
            self.logger.error("Cleanup timed out")
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}", exc_info=True)

async def main():
    """Main entry point with proper signal handling"""
    try:
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger('gecko_controller')

        # Create controller
        controller = GeckoController()

        # Set up signal handling
        loop = asyncio.get_running_loop()
        shutdown_event = asyncio.Event()

        def signal_handler(signame):
            logger.info(f"Received signal {signame}")
            # Use call_soon_threadsafe to safely set event from signal handler
            loop.call_soon_threadsafe(shutdown_event.set)

        # Register signal handlers
        for signame in ('SIGINT', 'SIGTERM'):
            loop.add_signal_handler(
                getattr(signal, signame),
                lambda s=signame: signal_handler(s)
            )

        try:
            # Start controller
            control_task = asyncio.create_task(controller.run())

            # Wait for shutdown signal
            await shutdown_event.wait()

            # Cancel control task
            logger.info("Initiating shutdown...")
            control_task.cancel()

            try:
                await control_task
            except asyncio.CancelledError:
                pass

            # Run cleanup with timeout
            logger.info("Running cleanup...")
            await asyncio.wait_for(controller.cleanup(), timeout=15.0)

        except asyncio.TimeoutError:
            logger.error("Shutdown timed out")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)
            raise

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Service stopped")
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
