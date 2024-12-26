#!/bin/bash

# Exit on any error
set -e

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root"
    exit 1
fi

# Get the absolute path to the project root (where this script is located)
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Install system dependencies
log "Installing system dependencies..."
apt-get update
apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-setuptools \
    i2c-tools \
    nodejs \
    npm

# Create directories
log "Creating directories..."
mkdir -p /opt/gecko-controller
mkdir -p /etc/gecko-controller
mkdir -p /var/log/gecko-controller

# Set up Python virtual environment
log "Setting up Python virtual environment..."
python3 -m venv /opt/gecko-controller/venv

# Install Python dependencies
log "Installing Python dependencies..."
/opt/gecko-controller/venv/bin/pip install --upgrade pip wheel setuptools
/opt/gecko-controller/venv/bin/pip install \
    RPi.GPIO \
    smbus2 \
    Pillow \
    Flask \
    adafruit-circuitpython-busdevice

# Build and install JavaScript components
log "Building JavaScript components..."
cd gecko_controller/web/static
npm install
npm run build:prod

# Install configuration file if it doesn't exist
if [ ! -f "/etc/gecko-controller/config.py" ]; then
    log "Installing default configuration..."
    cp "${PROJECT_ROOT}/debian/config.py" /etc/gecko-controller/
fi

# Install systemd services
log "Installing systemd services..."
cp "${PROJECT_ROOT}/debian/gecko-controller.service" /etc/systemd/system/
cp "${PROJECT_ROOT}/debian/gecko-web.service" /etc/systemd/system/

# Reload systemd
log "Reloading systemd..."
systemctl daemon-reload

# Enable services
log "Enabling services..."
systemctl enable gecko-controller
systemctl enable gecko-web

# Start services
log "Starting services..."
systemctl start gecko-controller
systemctl start gecko-web

# Configure I2C
log "Configuring I2C..."
sh -c "${PROJECT_ROOT}/set_i2c_baud.sh"

log "Installation complete!"
log "Please check service status with: systemctl status gecko-controller"
log "Web interface should be available at: http://localhost/"
