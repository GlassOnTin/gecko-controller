#!/bin/bash

# Gecko Controller Recovery Script
# Use this script to recover from I2C issues or service problems

echo "=== Gecko Controller Recovery Script ==="
echo "This script will attempt to recover the gecko-controller service"
echo ""

# Function to check I2C bus
check_i2c() {
    echo "Checking I2C bus..."
    if i2cdetect -y 1 &>/dev/null; then
        echo "✓ I2C bus is responsive"
        i2cdetect -y 1
        return 0
    else
        echo "✗ I2C bus not responding"
        return 1
    fi
}

# Stop the service
echo "1. Stopping gecko-controller service..."
sudo systemctl stop gecko-controller.service

# Reset I2C if needed
if ! check_i2c; then
    echo ""
    echo "2. Attempting I2C recovery..."
    
    # Try to reset I2C module
    echo "   Reloading I2C modules..."
    sudo modprobe -r i2c_bcm2835 i2c_dev 2>/dev/null || true
    sleep 1
    sudo modprobe i2c_bcm2835 i2c_dev
    sleep 2
    
    # Check again
    if check_i2c; then
        echo "✓ I2C bus recovered"
    else
        echo "✗ I2C bus still not responding - may need a reboot"
        echo ""
        echo "Would you like to reboot now? (y/n)"
        read -r response
        if [[ "$response" == "y" ]]; then
            echo "Rebooting in 5 seconds..."
            sleep 5
            sudo reboot
        fi
    fi
fi

# Clear any stuck processes
echo ""
echo "3. Clearing any stuck processes..."
sudo pkill -f "gecko_controller" 2>/dev/null || true
sleep 2

# Clear journal if it's too large
JOURNAL_SIZE=$(journalctl -u gecko-controller --disk-usage 2>/dev/null | grep -oP '\d+\.\d+[MG]' || echo "0M")
echo ""
echo "4. Journal size for gecko-controller: $JOURNAL_SIZE"
if [[ "$JOURNAL_SIZE" == *"G"* ]] || [[ "${JOURNAL_SIZE%M}" > "100" ]] 2>/dev/null; then
    echo "   Rotating journal..."
    sudo journalctl --rotate
    sudo journalctl --vacuum-time=7d
fi

# Start the service
echo ""
echo "5. Starting gecko-controller service..."
sudo systemctl start gecko-controller.service

# Wait for startup
sleep 3

# Check status
echo ""
echo "6. Checking service status..."
if systemctl is-active --quiet gecko-controller.service; then
    echo "✓ Service is running"
    echo ""
    sudo systemctl status gecko-controller.service --no-pager
else
    echo "✗ Service failed to start"
    echo ""
    echo "Recent logs:"
    sudo journalctl -u gecko-controller.service -n 50 --no-pager
fi

echo ""
echo "Recovery complete!"
echo ""
echo "Monitor the service with:"
echo "  sudo journalctl -u gecko-controller -f"