#!/bin/bash
set -e

# Install build dependencies
sudo apt-get update
sudo apt-get install -y \
    debhelper \
    dh-python \
    python3-all \
    python3-setuptools \
    python3-pip \
    devscripts \
    dh-virtualenv \
    build-essential \
    fakeroot

# Clean any previous build artifacts
rm -f ../gecko-controller_*.deb
rm -rf debian/gecko-controller
rm -rf debian/.debhelper
rm -f debian/files
rm -rf debian/gecko-controller.substvars
rm -rf debian/gecko-controller.debhelper.log

echo "Build dependencies installed and environment cleaned."
