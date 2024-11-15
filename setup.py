from setuptools import setup, find_packages

setup(
    name="gecko_controller",
    version="0.4.5",
    packages=find_packages(),
    install_requires=[
        "RPi.GPIO",
        "smbus2",
        "Pillow",  # Added for display functionality
    ],
    entry_points={
        'console_scripts': [
            'gecko-controller=gecko_controller.controller:main',
        ],
    },
    python_requires='>=3.9',
    author="Ian Ross Williams",
    author_email="ianrosswilliams@gmail.com",
    description="Raspberry Pi-based temperature, light and UV controller for gecko enclosure",
    long_description="Automated temperature and light controller for gecko enclosure with OLED display support. "
                     "Features include temperature and humidity monitoring, light cycle control, "
                     "heat management, and OLED status display.",
)