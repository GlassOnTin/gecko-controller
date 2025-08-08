#!/usr/bin/env python3
"""
I2C Resilient Wrapper for Gecko Controller
Handles transient I2C errors caused by relay switching EMI
"""

import time
import logging
import functools
from typing import Any, Callable, Optional, TypeVar, cast

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

T = TypeVar('T')

class I2CErrorFilter:
    """Filter to suppress repeated I2C error messages"""
    def __init__(self, max_errors_per_minute: int = 10):
        self.max_errors = max_errors_per_minute
        self.error_times = []
        self.suppressed_count = 0
        
    def should_log_error(self) -> bool:
        """Check if we should log this error or suppress it"""
        now = time.time()
        # Remove errors older than 1 minute
        self.error_times = [t for t in self.error_times if now - t < 60]
        
        if len(self.error_times) < self.max_errors:
            self.error_times.append(now)
            if self.suppressed_count > 0:
                logger.info(f"Suppressed {self.suppressed_count} similar I2C errors")
                self.suppressed_count = 0
            return True
        else:
            self.suppressed_count += 1
            return False

error_filter = I2CErrorFilter()

def i2c_retry(
    max_attempts: int = 3,
    delay: float = 0.1,
    backoff: float = 2.0,
    exceptions: tuple = (OSError, IOError)
) -> Callable:
    """
    Decorator to retry I2C operations with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
            attempt_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    # Small delay before I2C operations to let bus settle
                    if attempt > 0:
                        time.sleep(attempt_delay)
                    
                    result = func(*args, **kwargs)
                    
                    # If we had retries but succeeded, log recovery
                    if attempt > 0:
                        logger.debug(f"I2C operation {func.__name__} recovered after {attempt} retries")
                    
                    return result
                    
                except exceptions as e:
                    last_exception = e
                    error_msg = str(e)
                    
                    # Check for specific I2C errors
                    if '[Errno 121]' in error_msg:  # Remote I/O error
                        if attempt < max_attempts - 1:
                            if error_filter.should_log_error():
                                logger.warning(f"I2C device not responding, retry {attempt + 1}/{max_attempts}")
                        else:
                            if error_filter.should_log_error():
                                logger.error(f"I2C device not responding after {max_attempts} attempts")
                    
                    elif '[Errno 5]' in error_msg:  # Input/output error
                        if attempt < max_attempts - 1:
                            if error_filter.should_log_error():
                                logger.warning(f"I2C bus error (likely EMI), retry {attempt + 1}/{max_attempts}")
                            # Longer delay for bus errors
                            attempt_delay *= 2
                        else:
                            if error_filter.should_log_error():
                                logger.error(f"I2C bus error persisted after {max_attempts} attempts")
                    
                    else:
                        # Unexpected error, log it
                        if error_filter.should_log_error():
                            logger.error(f"Unexpected I2C error: {e}")
                    
                    # Exponential backoff
                    attempt_delay *= backoff
                    
                    # If this was the last attempt, return None or raise
                    if attempt >= max_attempts - 1:
                        return None  # Or you could re-raise: raise
            
            return None
        
        return wrapper
    return decorator

class ResilientI2CDevice:
    """
    Base class for I2C devices with built-in retry logic
    """
    def __init__(self, bus, address: int, name: str = "I2CDevice"):
        self.bus = bus
        self.address = address
        self.name = name
        self.error_count = 0
        self.last_good_read = time.time()
        
    @i2c_retry(max_attempts=3, delay=0.05)
    def read_byte(self, register: int) -> Optional[int]:
        """Read a byte from a register with retry logic"""
        return self.bus.read_byte_data(self.address, register)
    
    @i2c_retry(max_attempts=3, delay=0.05)
    def write_byte(self, register: int, value: int) -> bool:
        """Write a byte to a register with retry logic"""
        self.bus.write_byte_data(self.address, register, value)
        return True
    
    @i2c_retry(max_attempts=3, delay=0.05)
    def read_block(self, register: int, length: int) -> Optional[list]:
        """Read a block of bytes with retry logic"""
        return self.bus.read_i2c_block_data(self.address, register, length)
    
    def get_health_status(self) -> dict:
        """Get health status of this I2C device"""
        time_since_good = time.time() - self.last_good_read
        return {
            'name': self.name,
            'address': hex(self.address),
            'error_count': self.error_count,
            'time_since_good_read': time_since_good,
            'status': 'healthy' if time_since_good < 60 else 'degraded'
        }

class RelayController:
    """
    Relay controller with EMI mitigation
    """
    def __init__(self, gpio_pins: list):
        self.gpio_pins = gpio_pins
        self.switching = False
        self.switch_delay = 0.1  # Delay after relay switch before I2C operations
        
    def switch_relay(self, relay_num: int, state: bool, i2c_devices: list = None):
        """
        Switch relay with I2C protection
        
        Args:
            relay_num: Relay number to switch
            state: True for ON, False for OFF
            i2c_devices: List of I2C devices to pause during switching
        """
        self.switching = True
        
        try:
            # If we have I2C devices, prepare them for switching
            if i2c_devices:
                logger.debug(f"Preparing I2C devices for relay switch")
                # Could implement device-specific preparation here
            
            # Do the actual relay switch
            logger.info(f"Switching relay {relay_num} to {'ON' if state else 'OFF'}")
            # GPIO switching code here
            # gpio.output(self.gpio_pins[relay_num], state)
            
            # Wait for EMI to settle
            time.sleep(self.switch_delay)
            
            # Small additional delay for sensitive operations
            if i2c_devices:
                time.sleep(0.05)
            
        finally:
            self.switching = False
            logger.debug("Relay switch complete, I2C operations can resume")

# Example of how to integrate with existing code
def protected_i2c_operation(func: Callable[..., T]) -> Callable[..., Optional[T]]:
    """
    Decorator to protect I2C operations from relay EMI
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
        max_wait = 2.0  # Maximum time to wait for relay switching
        wait_start = time.time()
        
        # Wait if relay is switching
        while hasattr(wrapper, 'relay_controller') and wrapper.relay_controller.switching:
            if time.time() - wait_start > max_wait:
                logger.warning("Waited too long for relay switch, proceeding anyway")
                break
            time.sleep(0.01)
        
        # Proceed with I2C operation
        return func(*args, **kwargs)
    
    return wrapper

# Health monitoring for I2C bus
class I2CBusMonitor:
    """Monitor I2C bus health and recover from errors"""
    
    def __init__(self, bus_number: int = 1):
        self.bus_number = bus_number
        self.error_threshold = 50  # Errors before attempting bus reset
        self.recent_errors = []
        
    def log_error(self, error: Exception):
        """Log an I2C error for monitoring"""
        self.recent_errors.append({
            'time': time.time(),
            'error': str(error)
        })
        
        # Keep only recent errors (last 5 minutes)
        cutoff = time.time() - 300
        self.recent_errors = [e for e in self.recent_errors if e['time'] > cutoff]
        
        # Check if we need to attempt recovery
        if len(self.recent_errors) > self.error_threshold:
            logger.error(f"I2C bus has {len(self.recent_errors)} errors in 5 minutes, attempting recovery")
            self.attempt_recovery()
    
    def attempt_recovery(self):
        """Attempt to recover the I2C bus"""
        logger.info("Attempting I2C bus recovery...")
        
        try:
            # Method 1: Try to reset the I2C bus using i2cdetect
            import subprocess
            result = subprocess.run(
                ['i2cdetect', '-y', str(self.bus_number)],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info("I2C bus scan successful, bus may have recovered")
                self.recent_errors.clear()
            else:
                logger.error("I2C bus scan failed")
                
        except Exception as e:
            logger.error(f"Failed to recover I2C bus: {e}")
            
    def get_status(self) -> dict:
        """Get current bus health status"""
        error_rate = len(self.recent_errors) / 5.0  # errors per minute
        
        if error_rate < 1:
            status = 'healthy'
        elif error_rate < 10:
            status = 'degraded'
        else:
            status = 'critical'
            
        return {
            'bus_number': self.bus_number,
            'status': status,
            'error_rate': error_rate,
            'recent_error_count': len(self.recent_errors)
        }

# Example usage in main application
if __name__ == "__main__":
    logger.info("I2C Resilient Wrapper Example")
    
    # Initialize bus monitor
    bus_monitor = I2CBusMonitor(bus_number=1)
    
    # Example of protected I2C read
    @i2c_retry(max_attempts=5, delay=0.1)
    def read_sensor():
        # Simulated I2C read that might fail
        import random
        if random.random() < 0.3:  # 30% chance of failure
            raise OSError("[Errno 121] Remote I/O error")
        return 42
    
    # Test the retry logic
    for i in range(10):
        value = read_sensor()
        if value:
            logger.info(f"Read value: {value}")
        else:
            logger.error("Failed to read sensor")
        time.sleep(1)