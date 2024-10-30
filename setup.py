from setuptools import setup, find_packages

setup(
    name="gecko_controller",
    version="0.2.0",
    packages=find_packages(),
    install_requires=[
        "RPi.GPIO",
        "adafruit-circuitpython-displayio-sh1107",
        "adafruit-circuitpython-display-text",
        "adafruit-circuitpython-bitmap-font",
        "adafruit-blinka",
        "adafruit-circuitpython-busdevice",
        "smbus"
    ],
    package_data={
        'gecko_controller': ['fonts/*.pcf'],
    },
    entry_points={
        'console_scripts': [
            'gecko-controller=gecko_controller.controller:main',
        ],
    },
    python_requires='>=3.9',
    author="Ian Ross Williams",
    author_email="ianrosswilliams@gmail.com",
    description="Raspberry Pi-based temperature, light and UV controller for gecko enclosure",
)
