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
rm -f "${PROJECT_ROOT}/debian"/*.debhelper
rm -f "${PROJECT_ROOT}/debian"/*.debhelper.log
rm -f "${PROJECT_ROOT}/debian"/*.substvars
rm -f "${PROJECT_ROOT}/debian/debhelper-build-stamp"

# Clean Python build artifacts
rm -rf "${PROJECT_ROOT}/dist/"
rm -rf "${PROJECT_ROOT}/.pybuild/"
rm -rf "${PROJECT_ROOT}"/*.egg-info/
find "${PROJECT_ROOT}" -type d -name "__pycache__" -exec rm -rf {} +
find "${PROJECT_ROOT}" -type f -name "*.pyc" -delete

# Clean Node.js build artifacts
rm -rf "${PROJECT_ROOT}"/gecko_controller/web/static/node_modules/
rm -rf "${PROJECT_ROOT}"/gecko_controller/web/static/dist/
rm -rf "${PROJECT_ROOT}"/gecko_controller/web/static/package-lock.json
find "${PROJECT_ROOT}" -type f -name ".npm" -delete
find "${PROJECT_ROOT}" -type d -name ".npm" -exec rm -rf {} +
find "${PROJECT_ROOT}" -type f -name ".npmrc" -delete
find "${PROJECT_ROOT}" -type f -name ".node_repl_history" -delete
rm -rf "${PROJECT_ROOT}"/.npm/
rm -rf "${PROJECT_ROOT}"/.node-gyp/

# Clean dpkg build artifacts
rm -f "${PROJECT_ROOT}"/../gecko-controller_*.deb
rm -f "${PROJECT_ROOT}"/../gecko-controller_*.changes
rm -f "${PROJECT_ROOT}"/../gecko-controller_*.build
rm -f "${PROJECT_ROOT}"/../gecko-controller_*.buildinfo
rm -f "${PROJECT_ROOT}"/../gecko-controller_*.tar.xz
rm -f "${PROJECT_ROOT}"/../gecko-controller_*.dsc

# Clean editor temporary files
find "${PROJECT_ROOT}" -type f -name "*.swp" -delete
find "${PROJECT_ROOT}" -type f -name ".*.swp" -delete
find "${PROJECT_ROOT}" -type f -name "*.swo" -delete
find "${PROJECT_ROOT}" -type f -name ".*.swo" -delete
find "${PROJECT_ROOT}" -type f -name "*~" -delete
find "${PROJECT_ROOT}" -type f -name ".#*" -delete
find "${PROJECT_ROOT}" -type f -name "*.bak" -delete

# Clean IDE specific files
rm -rf "${PROJECT_ROOT}"/.idea/
rm -rf "${PROJECT_ROOT}"/.vscode/
rm -rf "${PROJECT_ROOT}"/*.sublime-workspace
rm -rf "${PROJECT_ROOT}"/*.sublime-project

# Clean test cache
rm -rf "${PROJECT_ROOT}"/.pytest_cache/
rm -rf "${PROJECT_ROOT}"/.coverage
rm -rf "${PROJECT_ROOT}"/htmlcov/

echo "Project cleaned successfully!"
