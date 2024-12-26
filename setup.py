from setuptools import setup, find_packages

setup(
    name="gecko-controller",
    version="0.7.8",
    packages=find_packages(),
    install_requires=[
        "RPi.GPIO>=0.7.1",
        "smbus>=1.1.post2",
        "smbus2>=0.4.3",
        "Pillow>=10.2.0",
        "Flask>=2.2.2",
	"pytest>=8.3.4",
        "adafruit-circuitpython-busdevice>=5.2.6",
    ],
    entry_points={
        'console_scripts': [
            'gecko-controller=gecko_controller.controller:main',
            'gecko-web=gecko_controller.web.app:main',
        ],
    },
    include_package_data=True,
)
