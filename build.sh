#!/bin/bash
set -e

echo "Starting build process..."

echo "Checking for required tools..."
sudo apt-get update
sudo apt-get install -y debhelper dh-python python3-all python3-setuptools python3-pip devscripts

echo "Verifying versions..."
if ! ./tools/verify-versions.sh; then
    echo "Error: Version verification failed"
    exit 1
fi

echo "Setting up web interface structure..."
mkdir -p gecko_controller/web/templates
[ ! -f gecko_controller/web/__init__.py ] && touch gecko_controller/web/__init__.py

echo "Building Debian package..."
if ! dpkg-buildpackage -us -uc; then
    echo "Error: Package build failed"
    exit 1
fi

echo "Build completed successfully!"
echo "Package files created in parent directory:"
ls -l ../*.deb ../*.buildinfo ../*.changes

echo
echo "Next steps:"
echo "1. Install the package: sudo dpkg -i ../gecko-controller_*.deb"
echo "2. Install dependencies: sudo apt-get install -f"
echo "3. Start the web interface: sudo systemctl start gecko-web"
echo "4. Enable web interface autostart: sudo systemctl enable gecko-web"
echo "5. Check status: sudo systemctl status gecko-web"
echo
echo "The web interface will be available at http://localhost/"