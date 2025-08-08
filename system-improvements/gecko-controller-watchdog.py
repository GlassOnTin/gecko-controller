#!/usr/bin/env python3
"""
Gecko Controller Watchdog Wrapper
This script wraps the gecko controller and sends periodic watchdog notifications to systemd
"""

import os
import sys
import time
import threading
import subprocess
import signal
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GeckoControllerWatchdog:
    def __init__(self):
        self.controller_process = None
        self.running = True
        self.watchdog_thread = None
        
        # Check if running under systemd with watchdog
        self.watchdog_usec = os.environ.get('WATCHDOG_USEC')
        self.watchdog_pid = os.environ.get('WATCHDOG_PID')
        self.notify_socket = os.environ.get('NOTIFY_SOCKET')
        
        if self.watchdog_usec:
            # Convert microseconds to seconds and use half the interval for safety
            self.watchdog_interval = int(self.watchdog_usec) / 1000000 / 2
            logger.info(f"Systemd watchdog enabled with {self.watchdog_interval}s interval")
        else:
            self.watchdog_interval = None
            logger.info("Running without systemd watchdog")
    
    def notify_systemd(self, message):
        """Send notification to systemd"""
        if not self.notify_socket:
            return
        
        try:
            import socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            sock.sendto(message.encode(), self.notify_socket)
            sock.close()
        except Exception as e:
            logger.error(f"Failed to notify systemd: {e}")
    
    def watchdog_ping(self):
        """Periodically ping systemd watchdog"""
        while self.running and self.watchdog_interval:
            try:
                # Check if main process is still alive
                if self.controller_process and self.controller_process.poll() is None:
                    self.notify_systemd("WATCHDOG=1")
                    logger.debug("Sent watchdog ping")
                else:
                    logger.error("Controller process died, not sending watchdog ping")
                    break
                
                time.sleep(self.watchdog_interval)
            except Exception as e:
                logger.error(f"Watchdog thread error: {e}")
                break
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
        if self.controller_process:
            self.controller_process.terminate()
            try:
                self.controller_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("Controller didn't terminate, killing...")
                self.controller_process.kill()
        
        sys.exit(0)
    
    def run(self):
        """Main run loop"""
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        # Notify systemd we're ready
        self.notify_systemd("READY=1")
        
        # Start watchdog thread if enabled
        if self.watchdog_interval:
            self.watchdog_thread = threading.Thread(target=self.watchdog_ping, daemon=True)
            self.watchdog_thread.start()
        
        # Change to gecko-controller directory
        os.chdir('/home/ian/gecko-controller')
        sys.path.insert(0, '/home/ian/gecko-controller')
        
        # Start the actual controller
        logger.info("Starting gecko controller...")
        try:
            self.controller_process = subprocess.Popen(
                [sys.executable, '-m', 'gecko_controller.controller'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env={**os.environ, 'PYTHONPATH': '/home/ian/gecko-controller'}
            )
            
            # Stream output from the controller
            while self.running:
                line = self.controller_process.stdout.readline()
                if not line:
                    if self.controller_process.poll() is not None:
                        logger.error(f"Controller exited with code {self.controller_process.returncode}")
                        break
                else:
                    # Print controller output (will go to journal)
                    print(line.rstrip())
            
        except Exception as e:
            logger.error(f"Failed to start controller: {e}")
            self.notify_systemd("ERRNO=1")
            sys.exit(1)
        
        # If we get here, the controller died unexpectedly
        if self.running:
            logger.error("Controller died unexpectedly")
            sys.exit(1)

if __name__ == "__main__":
    watchdog = GeckoControllerWatchdog()
    watchdog.run()