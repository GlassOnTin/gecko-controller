#!/bin/bash
# tools/verify-versions.sh - For verifying version consistency
set -e

# Extract version from setup.py
SETUP_VERSION=$(grep -Po "version='\K[^']+" setup.py)

# Extract version from debian/changelog
CHANGELOG_VERSION=$(dpkg-parsechangelog --show-field Version)

# Extract latest git tag (if any)
LATEST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "no tag")
GIT_VERSION=${LATEST_TAG#v}

echo "Checking version consistency..."
echo "  setup.py version:    $SETUP_VERSION"
echo "  changelog version:   $CHANGELOG_VERSION"
echo "  git tag version:    $GIT_VERSION"

if [ "$SETUP_VERSION" != "$CHANGELOG_VERSION" ]; then
    echo "ERROR: Version mismatch between setup.py ($SETUP_VERSION) and debian/changelog ($CHANGELOG_VERSION)"
    exit 1
fi

if [ "$LATEST_TAG" != "no tag" ] && [ "$GIT_VERSION" != "$CHANGELOG_VERSION" ]; then
    echo "WARNING: Latest git tag ($GIT_VERSION) doesn't match package version ($CHANGELOG_VERSION)"
fi