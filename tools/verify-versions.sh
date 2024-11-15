#!/bin/bash
# tools/verify-versions.sh - For verifying version consistency
set -e

# Enable more verbose error reporting
set -x  # Print commands as they execute

# Extract version from setup.py
if [ ! -f setup.py ]; then
    echo "ERROR: setup.py not found"
    exit 1
fi
SETUP_VERSION=$(grep -Po 'version=["'"'"']\K[^"'"'"']+' setup.py)
if [ -z "$SETUP_VERSION" ]; then
    echo "ERROR: Could not extract version from setup.py"
    exit 1
fi

# Extract version from debian/changelog
if [ ! -f debian/changelog ]; then
    echo "ERROR: debian/changelog not found"
    exit 1
fi
CHANGELOG_VERSION=$(dpkg-parsechangelog --show-field Version)
if [ -z "$CHANGELOG_VERSION" ]; then
    echo "ERROR: Could not extract version from debian/changelog"
    exit 1
fi

# Extract latest git tag (if any)
LATEST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "no tag")
GIT_VERSION=${LATEST_TAG#v}

echo "Version information:"
echo "  setup.py version:    $SETUP_VERSION"
echo "  changelog version:   $CHANGELOG_VERSION"
echo "  git tag version:    $GIT_VERSION"

# Check version consistency
if [ "$SETUP_VERSION" != "$CHANGELOG_VERSION" ]; then
    echo "ERROR: Version mismatch between setup.py ($SETUP_VERSION) and debian/changelog ($CHANGELOG_VERSION)"
    exit 1
fi

if [ "$LATEST_TAG" != "no tag" ] && [ "$GIT_VERSION" != "$CHANGELOG_VERSION" ]; then
    echo "WARNING: Latest git tag ($GIT_VERSION) doesn't match package version ($CHANGELOG_VERSION)"
    # Don't exit with error for tag mismatch - this is just a warning
fi

echo "Version verification passed"
exit 0