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

echo "Building Debian package..."
if ! dpkg-buildpackage -us -uc; then
    echo "Error: Package build failed"
    exit 1
fi

echo "Build completed successfully!"
echo "Package files created in parent directory:"
ls -l ../*.deb ../*.buildinfo ../*.changes