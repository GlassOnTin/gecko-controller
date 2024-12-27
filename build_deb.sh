#!/bin/bash
set -euo pipefail

# Script configuration
PACKAGE_NAME="gecko-controller"
MIN_MEMORY_MB=512
REQUIRED_SPACE_MB=1024

# Function to log messages with timestamps
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check system requirements
check_requirements() {
    log "Checking system requirements..."

    # Check available memory
    local available_mem=$(free -m | awk '/^Mem:/ {print $7}')
    if [ "$available_mem" -lt "$MIN_MEMORY_MB" ]; then
        log "Low memory detected ($available_mem MB). Setting up swap..."
        if [ ! -f /swapfile ]; then
            sudo fallocate -l 1G /swapfile
            sudo chmod 600 /swapfile
            sudo mkswap /swapfile
            sudo swapon /swapfile
        fi
    fi

    # Check available disk space
    local available_space=$(df -m . | awk 'NR==2 {print $4}')
    if [ "$available_space" -lt "$REQUIRED_SPACE_MB" ]; then
        log "Error: Insufficient disk space. Need at least ${REQUIRED_SPACE_MB}MB"
        exit 1
    fi
}

# Install build dependencies
install_dependencies() {
    log "Installing build dependencies..."
    sudo apt-get update
    sudo apt-get install -y \
        devscripts \
        debhelper \
        dh-python \
        python3-all \
        python3-setuptools \
        python3-pip \
        nodejs \
        npm \
        git-buildpackage
}

# Clean build environment
clean_environment() {
    log "Cleaning build environment..."
    rm -rf debian/${PACKAGE_NAME} debian/.debhelper debian/*.log debian/*.substvars
    rm -rf *.tar.gz *.dsc *.changes *.deb *.buildinfo
    rm -rf build/ dist/ *.egg-info/
    rm -rf gecko_controller/web/static/node_modules gecko_controller/web/static/dist
}

# Build package
build_package() {
    log "Building Debian package..."

    # Build with recommended options for Raspberry Pi
    DEB_BUILD_OPTIONS="noddebs nocheck" \
    DEBUILD_DPKG_BUILDPACKAGE_OPTS="-us -uc -ui" \
    debuild --no-lintian ${DEBUILD_EXTRA_OPTS:-}
}

# Install built package
install_package() {
    log "Looking for built package..."
    cd ..
    local latest_deb=$(ls -t ${PACKAGE_NAME}_*.deb 2>/dev/null | head -n1)

    if [ -n "$latest_deb" ]; then
        log "Installing $latest_deb..."
        sudo apt-get install -y "./$latest_deb"
        log "Restarting service..."
        sudo systemctl restart gecko-controller
    else
        log "Error: No .deb package found after build"
        exit 1
    fi
}

# Main execution
main() {
    log "Starting build process for ${PACKAGE_NAME}"

    check_requirements
    install_dependencies
    clean_environment

    build_package
    install_package

    log "Build and installation completed successfully!"
}

# Execute main function
main "$@"
