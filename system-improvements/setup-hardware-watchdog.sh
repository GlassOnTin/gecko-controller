#!/bin/bash

# Hardware Watchdog Setup for Raspberry Pi
# This enables the BCM2835 hardware watchdog for automatic system recovery

set -e

echo "=== Setting up Hardware Watchdog for Raspberry Pi ==="
echo ""

# Check if we're on a Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "Warning: This doesn't appear to be a Raspberry Pi"
    echo "Continue anyway? (y/n)"
    read -r response
    [[ "$response" != "y" ]] && exit 1
fi

# Enable watchdog module at boot
echo "1. Enabling watchdog module at boot..."
if ! grep -q "dtparam=watchdog=on" /boot/firmware/config.txt 2>/dev/null; then
    # Try different config locations for different Raspbian versions
    if [ -f /boot/firmware/config.txt ]; then
        CONFIG_FILE="/boot/firmware/config.txt"
    elif [ -f /boot/config.txt ]; then
        CONFIG_FILE="/boot/config.txt"
    else
        echo "Error: Could not find config.txt"
        exit 1
    fi
    
    echo "   Adding watchdog to $CONFIG_FILE..."
    echo "" | sudo tee -a "$CONFIG_FILE"
    echo "# Enable hardware watchdog" | sudo tee -a "$CONFIG_FILE"
    echo "dtparam=watchdog=on" | sudo tee -a "$CONFIG_FILE"
else
    echo "   Watchdog already enabled in boot config"
fi

# Load the watchdog module now
echo ""
echo "2. Loading watchdog module..."
sudo modprobe bcm2835_wdt 2>/dev/null || sudo modprobe bcm2835-wdt 2>/dev/null || echo "   Module may already be loaded"

# Install watchdog daemon
echo ""
echo "3. Installing watchdog daemon..."
sudo apt-get update
sudo apt-get install -y watchdog

# Configure watchdog daemon
echo ""
echo "4. Configuring watchdog daemon..."
sudo tee /etc/watchdog.conf > /dev/null << 'EOF'
# Hardware watchdog configuration for Raspberry Pi
# This will reboot the system if it becomes unresponsive

# Device to use
watchdog-device = /dev/watchdog

# Watchdog timeout in seconds (how long before reboot if not pinged)
watchdog-timeout = 15

# How often to write to watchdog device (in seconds)
interval = 5

# Maximum system load (1 minute average)
max-load-1 = 24

# Maximum system load (5 minute average)
max-load-5 = 18

# Maximum system load (15 minute average)
max-load-15 = 12

# Minimum free memory (pages)
min-memory = 1

# Check if these processes are running (optional)
# pidfile = /var/run/gecko-controller.pid

# Check network interface
interface = wlan0

# Ping test (optional - uncomment to enable)
# ping = 8.8.8.8
# ping-count = 3

# Temperature monitoring (Celsius)
temperature-sensor = /sys/class/thermal/thermal_zone0/temp
max-temperature = 85000

# What to do when the watchdog triggers
repair-binary = /home/ian/gecko-recovery.sh
repair-timeout = 60

# Realtime priority (helps ensure watchdog runs even under high load)
realtime = yes
priority = 1

# Log verbose messages
verbose = yes
log-dir = /var/log/watchdog

# Test mode (set to yes to test without actually rebooting)
# test-binary = /bin/true
# test-timeout = 60
EOF

# Create log directory
sudo mkdir -p /var/log/watchdog
sudo chmod 755 /var/log/watchdog

# Configure systemd service for watchdog
echo ""
echo "5. Configuring watchdog systemd service..."
sudo systemctl enable watchdog.service

# Create a script to test the watchdog
echo ""
echo "6. Creating watchdog test script..."
cat > /home/ian/test-watchdog.sh << 'EOF'
#!/bin/bash

echo "=== Hardware Watchdog Test ==="
echo "WARNING: This will cause a system reboot in ~15 seconds!"
echo "Press Ctrl+C now to cancel..."
echo ""

for i in {5..1}; do
    echo "Starting test in $i seconds..."
    sleep 1
done

echo ""
echo "Stopping watchdog daemon (system should reboot in ~15 seconds)..."
sudo systemctl stop watchdog.service

echo "Watchdog stopped. If configured correctly, system will reboot soon."
echo "If system doesn't reboot within 30 seconds, watchdog is not working."

# Create a fork bomb to ensure system hangs (commented out for safety)
# :(){ :|:& };:
EOF
chmod +x /home/ian/test-watchdog.sh

# Start the watchdog service
echo ""
echo "7. Starting watchdog service..."
sudo systemctl start watchdog.service || true

# Check status
echo ""
echo "8. Checking watchdog status..."
sudo systemctl status watchdog.service --no-pager || true

echo ""
echo "=== Hardware Watchdog Setup Complete ==="
echo ""
echo "The hardware watchdog is now configured and will:"
echo "  ✓ Automatically reboot if system hangs"
echo "  ✓ Monitor system load and reboot if too high"
echo "  ✓ Monitor free memory and reboot if too low"
echo "  ✓ Monitor CPU temperature and reboot if too high"
echo "  ✓ Monitor network interface"
echo "  ✓ Run recovery script before rebooting (if possible)"
echo ""
echo "Important notes:"
echo "  - A reboot is required to fully enable the hardware watchdog"
echo "  - After reboot, the system will auto-reboot if it hangs for >15 seconds"
echo "  - Logs are available at: /var/log/watchdog/"
echo ""
echo "Commands:"
echo "  - Check status: sudo systemctl status watchdog"
echo "  - View logs: sudo journalctl -u watchdog -f"
echo "  - Test watchdog: /home/ian/test-watchdog.sh (WILL REBOOT!)"
echo ""
echo "Would you like to reboot now to enable the hardware watchdog? (y/n)"
read -r response
if [[ "$response" == "y" ]]; then
    echo "Rebooting in 5 seconds..."
    sleep 5
    sudo reboot
else
    echo "Please reboot when convenient to fully enable the hardware watchdog."
fi