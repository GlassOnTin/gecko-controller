#!/bin/bash
set -e

# Ensure required build dependencies are installed
sudo apt-get update
sudo apt-get install -y devscripts debhelper dh-python python3-all python3-setuptools python3-pip nodejs npm

# Clear any previous build artifacts
rm -rf *.tar.gz *.dsc *.changes *.deb
rm -rf build/ dist/ *.egg-info/

# Build JavaScript components
echo "Building JavaScript components..."
cd gecko_controller/web/static
npm install
NODE_ENV=production npm run build:prod
cd ../../..

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

# Restart services to ensure new web interface is loaded
echo "Restarting services..."
sudo systemctl restart gecko-controller gecko-web

echo "Installation complete!"
