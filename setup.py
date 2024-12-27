from setuptools import setup, find_namespace_packages

setup(
    name="gecko-controller",
    version="0.8.3",
    packages=find_namespace_packages(include=[
        'gecko_controller*',
        'tests*'
    ]),  # Remove the exclude
    package_data={
        "gecko_controller": [
            "fonts/*.pcf",
            "web/templates/*.html",
            "web/static/dist/*",
            "web/static/components/*.jsx"
        ]
    },
    include_package_data=True,
    install_requires=[
        "RPi.GPIO",
        "smbus2",
        "Pillow",
        "Flask>=2.2.2",
        "adafruit-circuitpython-busdevice"
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "gecko-controller=gecko_controller.controller:main",
            "gecko-web=gecko_controller.web.app:main"
        ]
    }
)
