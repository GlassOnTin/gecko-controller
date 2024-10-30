#!/bin/bash
set -e

# Get the absolute path to the project root (where this script is located)
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Go to project root
cd "$PROJECT_ROOT"

echo "Cleaning project in: $PROJECT_ROOT"

# Clean Debian build artifacts
rm -rf "${PROJECT_ROOT}/debian/.debhelper/"
rm -rf "${PROJECT_ROOT}/debian/gecko-controller/"
rm -f "${PROJECT_ROOT}/debian/files"
rm -f "${PROJECT_ROOT}/debian"/*.debhelper.log
rm -f "${PROJECT_ROOT}/debian"/*.substvars
rm -f "${PROJECT_ROOT}/debian/debhelper-build-stamp"

# Clean Python build artifacts
rm -rf "${PROJECT_ROOT}/build/"
rm -rf "${PROJECT_ROOT}/dist/"
rm -rf "${PROJECT_ROOT}/.pybuild/"
rm -rf "${PROJECT_ROOT}"/*.egg-info/
rm -rf "${PROJECT_ROOT}"/__pycache__/
rm -rf "${PROJECT_ROOT}/gecko_controller"/__pycache__/
rm -f "${PROJECT_ROOT}/gecko_controller"/*.pyc

# Clean dpkg build artifacts
rm -f "${PROJECT_ROOT}"/../gecko-controller_*.deb
rm -f "${PROJECT_ROOT}"/../gecko-controller_*.changes
rm -f "${PROJECT_ROOT}"/../gecko-controller_*.build
rm -f "${PROJECT_ROOT}"/../gecko-controller_*.buildinfo
rm -f "${PROJECT_ROOT}"/../gecko-controller_*.tar.xz
rm -f "${PROJECT_ROOT}"/../gecko-controller_*.dsc

echo "Project cleaned successfully!"
