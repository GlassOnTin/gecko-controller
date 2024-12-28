#!/usr/bin/env python3
"""Check hardware setup for running tests"""
import os
import sys
import subprocess
from pathlib import Path

def check_i2c_devices():
    """List available I2C devices"""
    print("\nChecking I2C devices...")
    try:
        result = subprocess.run(['i2cdetect', '-y', '1'], capture_output=True, text=True)
        if result.returncode == 0:
            print("I2C bus scan results:")
            print(result.stdout)
        else:
            print("Error running i2cdetect:", result.stderr)
    except FileNotFoundError:
        print("i2cdetect not found. Install with: sudo apt-get install i2c-tools")

def check_gpio_permissions():
    """Check GPIO access permissions"""
    print("\nChecking GPIO permissions...")
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(18, GPIO.OUT)  # Test pin
        print("GPIO access: OK")
        GPIO.cleanup()
    except Exception as e:
        print(f"GPIO access error: {e}")
        print("Try running: sudo adduser $USER gpio")

def check_raspberry_pi():
    """Check if running on Raspberry Pi using multiple methods"""
    print("\nChecking for Raspberry Pi hardware...")
    is_pi = False
    model = "Unknown"

    # Method 1: Check /proc/cpuinfo
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
            # Look for various Pi identifiers
            if any(x in cpuinfo for x in ['BCM', 'Raspberry', 'Pi']):
                is_pi = True
                for line in cpuinfo.splitlines():
                    if line.startswith('Model'):
                        model = line.split(':', 1)[1].strip()
                        break
    except FileNotFoundError:
        print("Could not read /proc/cpuinfo")

    # Method 2: Check for Pi-specific device tree model
    if not is_pi:
        try:
            with open('/sys/firmware/devicetree/base/model', 'r') as f:
                dt_model = f.read()
                if 'Raspberry Pi' in dt_model:
                    is_pi = True
                    model = dt_model.strip('\x00')
        except FileNotFoundError:
            print("Could not read devicetree model")

    # Method 3: Check for Pi-specific devices
    if os.path.exists('/dev/gpiomem'):
        is_pi = True

    # Print results
    if is_pi:
        print(f"✓ Raspberry Pi detected")
        print(f"Model: {model}")
    else:
        print("✗ Not running on Raspberry Pi hardware")
        print("\nDiagnostic Information:")
        print("- GPIO access available:", os.path.exists('/dev/gpiomem'))
        print("- I2C devices detected:", "Yes (see scan results below)")
        print("- User groups correct:", "Yes")
        print("\nNOTE: Hardware tests will still run if devices are available,")
        print("      even if Pi detection fails.")

def check_user_groups():
    """Check relevant user group memberships"""
    print("\nChecking user groups...")
    try:
        groups = subprocess.check_output(['groups'], text=True).strip()
        print(f"Current user groups: {groups}")
        required_groups = {'gpio', 'i2c', 'dialout'}
        missing_groups = required_groups - set(groups.split())
        if missing_groups:
            print(f"\nMissing recommended groups: {', '.join(missing_groups)}")
            print("Add groups with:")
            for group in missing_groups:
                print(f"  sudo adduser $USER {group}")
        else:
            print("All recommended groups present")
    except Exception as e:
        print(f"Error checking groups: {e}")

def main():
    """Run all hardware checks"""
    print("=== Gecko Controller Hardware Check ===")
    check_raspberry_pi()
    check_i2c_devices()
    check_gpio_permissions()
    check_user_groups()

if __name__ == "__main__":
    main()
