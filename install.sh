#!/bin/bash

# Exit on error
set -e

echo "Installing Gecko Controller..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

# Install system dependencies
echo "Installing system dependencies..."
apt-get update
apt-get install -y \
    python3-pip \
    python3-venv \
    i2c-tools \
    fonts-symbola \
    git

# Install Poetry
echo "Installing Poetry..."
curl -sSL https://install.python-poetry.org | python3 -

# Create directories
echo "Creating required directories..."
mkdir -p /etc/gecko-controller
mkdir -p /var/log/gecko-controller
chmod 755 /etc/gecko-controller
chmod 755 /var/log/gecko-controller

# Install the package
echo "Installing Gecko Controller package..."
poetry config virtualenvs.create false
poetry install

# Copy config file if it doesn't exist
if [ ! -f /etc/gecko-controller/config.py ]; then
    echo "Installing default configuration..."
    cp config.py /etc/gecko-controller/
    chmod 644 /etc/gecko-controller/config.py
fi

# Install and enable systemd services
echo "Installing systemd services..."
cp debian/gecko-controller.service /lib/systemd/system/
cp debian/gecko-web.service /lib/systemd/system/
systemctl daemon-reload
systemctl enable gecko-controller
systemctl enable gecko-web

# Enable I2C if not already enabled
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
    echo "Enabling I2C..."
    echo "dtparam=i2c_arm=on" >> /boot/config.txt
fi

# Start services
echo "Starting services..."
systemctl start gecko-controller
systemctl start gecko-web

echo "Installation complete!"
echo "The web interface should be available at http://localhost"
echo "Check service status with: systemctl status gecko-controller"
echo "View logs with: journalctl -u gecko-controller -f"
