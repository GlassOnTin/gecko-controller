#!/bin/bash
# build.sh - For building packages
set -e

# Ensure we have the necessary tools
sudo apt-get update
sudo apt-get install -y debhelper dh-python python3-all python3-setuptools python3-pip devscripts

# Verify version consistency before building
./tools/verify-versions.sh

# Build the package
dpkg-buildpackage -us -uc

# The .deb file will be created in the parent directory
echo "Package built successfully! You can find the .deb file in the parent directory."