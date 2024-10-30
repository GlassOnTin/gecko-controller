# Gecko Controller

A Raspberry Pi-based temperature and light controller for gecko enclosure monitoring and control.

## Features

- Real-time temperature and humidity monitoring
- Automated light cycle control
- Temperature-based heating control
- OLED display showing:
  - Current time
  - Temperature and humidity readings
  - Target temperature
  - Light and heat status
  - Time until next light transition

## Hardware Requirements

- Raspberry Pi (any model with GPIO pins)
- SH1107 OLED Display
- SHT31 Temperature/Humidity Sensor
- Relay modules for light and heat control
- Compatible power supply

## Installation

1. Install Poetry if you haven't already:
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Clone the repository and install dependencies:
```bash
git clone https://github.com/yourusername/gecko-controller.git
cd gecko-controller
poetry install
```

3. Copy the Fork Awesome font to the fonts directory:
```bash
mkdir -p gecko_controller/fonts
cp forkawesome-12.pcf gecko_controller/fonts/
```

## Usage

Run the controller:
```bash
poetry run gecko-controller
```

## Configuration

The following parameters can be adjusted in `controller.py`:

- `MIN_TEMP`: Minimum (night) temperature
- `DAY_TEMP`: Target daytime temperature
- `TEMP_TOLERANCE`: Temperature control deadband
- `LIGHT_ON_HOUR`: Hour to turn lights on (24-hour format)
- `LIGHT_OFF_HOUR`: Hour to turn lights off (24-hour format)

## GPIO Pin Configuration

- Light Relay: GPIO 4
- Heat Relay: GPIO 17
- Display Reset: GPIO 21

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
