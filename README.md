# Gecko Controller

A Raspberry Pi-based temperature, light, and UV controller for gecko enclosure monitoring and control.

<div align="center">
  <img src="diablo.jpg" alt="Diablo the Leopard Gecko" width="400"/>
  <p><em>Diablo the Leopard Gecko, for whom this controller was built</em></p>
</div>

## Features

- Real-time temperature and humidity monitoring via SHT31 sensor
- UV spectrum monitoring (UVA/UVB/UVC) via AS7331 sensor
- Automated light cycle control with configurable schedules
- Temperature-based heating control with day/night settings
- OLED status display showing:
  - Current time
  - Temperature and humidity readings
  - Target temperature
  - UV levels with status indicators
  - Light and heat status
  - Time until next light transition
- Logging of environmental conditions

## Hardware Requirements

- Raspberry Pi (any model with GPIO pins)
- SSH1106 OLED Display (I2C interface)
- SHT31 Temperature/Humidity Sensor
- AS7331 Spectral UV Sensor
- 2x Relay modules (for light and heat control)
- Compatible 5V power supply
- I2C-compatible cables and connectors

## Installation

### Method 1: Using the Debian Package (Recommended)

1. Enable I2C on your Raspberry Pi:
   ```bash
   sudo raspi-config
   # Navigate to Interface Options > I2C > Enable
   ```

2. Install the package:
   ```bash
   sudo apt update
   sudo apt install gecko-controller
   ```

3. The service will start automatically. Check its status with:
   ```bash
   sudo systemctl status gecko-controller
   ```

### Method 2: Running from Source

1. Enable I2C as described above

2. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/gecko-controller.git
   cd gecko-controller
   ```

3. Install required packages:
   ```bash
   python3 -m pip install RPi.GPIO smbus2 Pillow
   ```

4. Run the controller:
   ```bash
   python3 gecko_controller/controller.py
   ```

## Configuration

Create or modify `/etc/gecko-controller/config.py` with your settings:

```python
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
```

## GPIO Wiring

| Component          | GPIO Pin | Notes                    |
|-------------------|----------|--------------------------|
| Light Relay       | GPIO 4   | Active HIGH for ON       |
| Heat Relay        | GPIO 17  | Active HIGH for ON       |
| Display Reset     | GPIO 21  | Optional, HIGH for normal|
| I2C SDA           | GPIO 2   | For all I2C devices      |
| I2C SCL           | GPIO 3   | For all I2C devices      |

## Troubleshooting

1. Check I2C devices are detected:
   ```bash
   sudo i2cdetect -y 1
   ```

2. View service logs:
   ```bash
   journalctl -u gecko-controller -f
   ```

3. Common issues:
   - If display shows no data, check I2C connections and addresses
   - If UV readings show as "None", verify AS7331 sensor connection
   - For temperature/humidity errors, check SHT31 sensor wiring

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or contributions, please open an issue on the GitHub repository.