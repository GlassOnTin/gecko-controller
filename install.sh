#!/bin/bash
set -e

# Ensure required build dependencies are installed
sudo apt-get update
sudo apt-get install -y devscripts debhelper dh-python python3-all python3-setuptools python3-pip

# Clear any previous build artifacts
rm -rf *.tar.gz *.dsc *.changes *.deb
rm -rf build/ dist/ *.egg-info/

# Increase available memory with swap
if [ ! -f /swapfile ]; then
    echo "Creating swap file..."
    sudo fallocate -l 1G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
fi

# Build the debian package. Note that lintian is too slow on a Pi zero!
DEB_BUILD_OPTIONS=noddebs debuild --no-lintian -us -uc -ui

# Move up to parent directory where .deb file will be
cd ..

# Find and install the latest built package
latest_deb=$(ls -t gecko-controller_*.deb | head -n1)
if [ -n "$latest_deb" ]; then
    echo "Installing $latest_deb..."
    sudo apt-get install -y "./$latest_deb"
else
    echo "Error: No .deb package found after build"
    exit 1
fi
