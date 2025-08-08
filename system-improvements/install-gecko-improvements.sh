#!/bin/bash

# Installation script for Gecko Controller improvements
# This script installs enhanced systemd service with watchdog and health monitoring

set -e

echo "Installing Gecko Controller service improvements..."

# Stop the current service if running
echo "Stopping current gecko-controller service..."
sudo systemctl stop gecko-controller.service || true

# Backup current service file
if [ -f /etc/systemd/system/gecko-controller.service ]; then
    echo "Backing up current service file..."
    sudo cp /etc/systemd/system/gecko-controller.service /etc/systemd/system/gecko-controller.service.backup
fi

# Install the enhanced service file
echo "Installing enhanced service configuration..."
sudo cp /home/ian/gecko-controller.service.enhanced /etc/systemd/system/gecko-controller.service

# Install health check service and timer
echo "Installing health check service and timer..."
sudo cp /home/ian/gecko-health-check.service /etc/systemd/system/
sudo cp /home/ian/gecko-health-check.timer /etc/systemd/system/

# Create log file for health checks
sudo touch /var/log/gecko-health-check.log
sudo chmod 644 /var/log/gecko-health-check.log

# Reload systemd daemon
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable services
echo "Enabling services..."
sudo systemctl enable gecko-controller.service
sudo systemctl enable gecko-health-check.timer

# Start the services
echo "Starting services..."
sudo systemctl start gecko-controller.service
sudo systemctl start gecko-health-check.timer

# Wait a moment for services to start
sleep 3

# Check status
echo ""
echo "=== Service Status ==="
sudo systemctl status gecko-controller.service --no-pager
echo ""
echo "=== Health Check Timer Status ==="
sudo systemctl status gecko-health-check.timer --no-pager
echo ""
echo "=== Next Health Check ==="
sudo systemctl list-timers gecko-health-check.timer --no-pager

echo ""
echo "Installation complete!"
echo ""
echo "Useful commands:"
echo "  - View service status: sudo systemctl status gecko-controller"
echo "  - View service logs: sudo journalctl -u gecko-controller -f"
echo "  - View health check logs: sudo tail -f /var/log/gecko-health-check.log"
echo "  - Restart service: sudo systemctl restart gecko-controller"
echo "  - Run health check manually: sudo /home/ian/gecko-health-check.sh"
echo ""
echo "The service now includes:"
echo "  ✓ Automatic restart on failure"
echo "  ✓ Memory and CPU limits to prevent resource exhaustion"
echo "  ✓ Health checks every 5 minutes"
echo "  ✓ I2C error monitoring and recovery"
echo "  ✓ Enhanced logging"
echo ""
echo "To use the watchdog-enabled version (optional):"
echo "  1. Edit /etc/systemd/system/gecko-controller.service"
echo "  2. Change ExecStart to: /home/ian/gecko-controller-watchdog.py"
echo "  3. Run: sudo systemctl daemon-reload && sudo systemctl restart gecko-controller"