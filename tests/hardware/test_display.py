import pytest
import time
import smbus2
import signal
from contextlib import contextmanager
from gecko_controller.ssh1106 import SSH1106Display

class TimeoutException(Exception):
    pass

@contextmanager
def timeout(seconds):
    """Context manager for adding timeout to a block of code"""
    def timeout_handler(signum, frame):
        raise TimeoutException(f"Operation timed out after {seconds} seconds")

    # Set the timeout handler
    original_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        # Restore the original handler and cancel alarm
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)

def check_i2c_available():
    """Check if I2C bus is available and not locked"""
    try:
        with timeout(2):  # 2 second timeout
            bus = smbus2.SMBus(1)
            try:
                # Quick read to see if bus responds
                bus.read_byte(0x3c)
                bus.close()
                return True
            except OSError:
                # Device not present is OK - just means no response at this address
                bus.close()
                return True
            except Exception as e:
                print(f"I2C bus error: {e}")
                return False
    except TimeoutException:
        print("I2C bus appears to be locked or unresponsive")
        return False

@pytest.mark.requires_display
def test_display():
    """Test OLED display communication"""
    print("\nTesting SSH1106 Display initialization and communication")

    # First check if I2C is responsive
    if not check_i2c_available():
        pytest.skip("I2C bus is locked or unresponsive - try stopping gecko-controller service")

    display = None
    try:
        with timeout(5):  # 5 second timeout for display initialization
            display = SSH1106Display(i2c_addr=0x3c)
            time.sleep(0.1)  # Brief pause after initialization

            # Test basic display functionality
            print("Testing display commands...")

            # Create a test pattern
            print("Drawing test pattern...")
            for page in range(8):  # 8 pages for 64 pixel height
                display.write_cmd(0xB0 + page)  # Set page address
                display.write_cmd(0x02)         # Set column address (low nibble)
                display.write_cmd(0x10)         # Set column address (high nibble)

                # Fill alternate pages with different patterns
                pattern = 0xAA if page % 2 == 0 else 0x55
                for i in range(128):  # 128 pixels width
                    display.write_data(pattern)

            print("Test pattern displayed successfully")

            # Wait briefly to allow pattern to be visible
            time.sleep(1)

            # Clear display
            print("Clearing display...")
            for page in range(8):
                display.write_cmd(0xB0 + page)
                display.write_cmd(0x02)
                display.write_cmd(0x10)
                for i in range(128):
                    display.write_data(0x00)

            print("Display test completed successfully")

    except TimeoutException as e:
        print(f"\nError: {e}")
        print("\nTroubleshooting steps:")
        print("1. Check if gecko-controller service is running and using the I2C bus")
        print("2. Try stopping the service: sudo systemctl stop gecko-controller")
        print("3. Check I2C speed in /boot/config.txt")
        print("4. Verify all I2C connections")
        pytest.fail("Display test timed out")

    except Exception as e:
        print(f"\nError testing display: {e}")
        print("\nTroubleshooting suggestions:")
        print("1. Check physical connections (especially SDA, SCL, VCC and GND)")
        print("2. Verify display voltage (should be 3.3V)")
        print("3. Check for pull-up resistors on SDA and SCL")
        print("4. Try lower I2C speed in /boot/config.txt:")
        print("   dtparam=i2c_arm=on,i2c_arm_baudrate=50000")
        pytest.fail(f"Display test failed: {str(e)}")

    finally:
        # Clean up
        if display:
            try:
                with timeout(2):  # 2 second timeout for cleanup
                    # Turn display back on and clear it
                    display.init_display()
                    print("Display cleanup completed")
            except TimeoutException:
                print("Warning: Display cleanup timed out")
            except:
                print("Warning: Could not cleanup display")
