from setuptools import setup, find_packages

setup(
    name="gecko_controller",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "RPi.GPIO",
        "adafruit-circuitpython-displayio-sh1107",
        "adafruit-circuitpython-display-text",
        "adafruit-circuitpython-bitmap-font",
        "smbus",
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
    description="Raspberry Pi-based temperature and light controller for gecko enclosure",
)
