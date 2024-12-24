#!/bin/bash

# Function to check if we're running with sudo
check_sudo() {
    if [ "$EUID" -ne 0 ]; then
        echo "Please run as root (sudo)"
        exit 1
    fi
}

# Function to get the real user who called sudo
get_real_user() {
    if [ -n "$SUDO_USER" ]; then
        echo "$SUDO_USER"
    else
        echo "$USER"
    fi
}

# Main installation
check_sudo

REAL_USER=$(get_real_user)
REAL_HOME=$(eval echo ~$REAL_USER)
PROJECT_DIR=$(pwd)

echo "Installing Gecko Controller..."

# Install system dependencies
echo "Installing system dependencies..."
apt-get update
apt-get install -y python3-pip python3-venv i2c-tools fonts-symbola git

# Create required directories
echo "Creating required directories..."
mkdir -p /etc/gecko-controller
mkdir -p /var/log/gecko-controller
chown -R $REAL_USER:$REAL_USER /var/log/gecko-controller

# Fix ownership of the project directory
echo "Setting correct permissions..."
chown -R $REAL_USER:$REAL_USER "$PROJECT_DIR"

# Create and setup virtualenv as the real user
echo "Setting up Python virtual environment..."
runuser -u $REAL_USER -- python3 -m venv venv
source venv/bin/activate

# Install pip and poetry as the real user
echo "Installing pip and poetry..."
runuser -u $REAL_USER -- venv/bin/pip install --upgrade pip
runuser -u $REAL_USER -- venv/bin/pip install poetry

# Store current keyring backend
OLD_KEYRING_BACKEND=$PYTHON_KEYRING_BACKEND

# Set keyring to null for poetry commands
export PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring

# Run poetry commands as the real user with proper directory ownership
echo "Installing Gecko Controller package..."
cd "$PROJECT_DIR"
runuser -u $REAL_USER -- bash -c "cd '$PROJECT_DIR' && venv/bin/poetry cache clear . --all"
runuser -u $REAL_USER -- bash -c "cd '$PROJECT_DIR' && venv/bin/poetry install --only main"
runuser -u $REAL_USER -- bash -c "cd '$PROJECT_DIR' && venv/bin/poetry build"

# Restore original keyring backend
export PYTHON_KEYRING_BACKEND=$OLD_KEYRING_BACKEND

# Final permission cleanup
chown -R $REAL_USER:$REAL_USER "$PROJECT_DIR"

echo "Installation complete!"
