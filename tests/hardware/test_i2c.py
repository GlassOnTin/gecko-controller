import pytest
import smbus2
import time

@pytest.mark.requires_hardware
def test_i2c_devices():
    """Test I2C device detection and basic communication"""
    print("\nScanning I2C bus for devices...")

    expected_devices = {
        0x3c: "OLED Display (SSH1106)",
        0x44: "Temperature/Humidity Sensor (SHT31)",
        0x74: "UV Sensor (AS7331)"
    }

    found_devices = []
    bus = smbus2.SMBus(1)

    try:
        # Scan through possible I2C addresses
        for addr in range(0x03, 0x77):
            try:
                bus.read_byte(addr)
                found_devices.append(addr)
                print(f"Found device at 0x{addr:02x}: {expected_devices.get(addr, 'Unknown device')}")
            except OSError:  # No device at this address
                pass
            except Exception as e:
                print(f"Error accessing device at 0x{addr:02x}: {e}")

        # Check for expected devices
        for addr in expected_devices:
            if addr not in found_devices:
                print(f"\nWarning: Expected device not found: {expected_devices[addr]} (0x{addr:02x})")
                print("Please check:")
                print("1. Physical connections")
                print("2. Power supply")
                print("3. Device address configuration")

        # Verify at least one expected device is present
        if not any(addr in found_devices for addr in expected_devices):
            pytest.fail("No expected I2C devices found")

    except Exception as e:
        print(f"\nError during I2C scan: {e}")
        pytest.fail(f"I2C bus error: {str(e)}")

    finally:
        bus.close()
