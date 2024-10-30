#!/bin/bash
set -e

# Check if version parameter is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 0.2.1"
    exit 1
fi

VERSION=$1

# Remove 'v' prefix if provided
VERSION="${VERSION#v}"

# Update version.py
echo "Updating version.py..."
cat > gecko_controller/version.py << EOF
"""Single source of truth for version number"""
VERSION = "$VERSION"
EOF

# Update debian/changelog
echo "Updating debian/changelog..."
dch --newversion "$VERSION" "New release $VERSION"

# Commit changes
echo "Committing version changes..."
git add gecko_controller/version.py debian/changelog
git commit -m "Release version $VERSION"

# Create and push tag
echo "Creating and pushing tag..."
git tag -a "v$VERSION" -m "Release version $VERSION"
git push origin main "v$VERSION"

echo "Release v$VERSION initiated!"
echo "Check GitHub Actions to monitor the build and release process."
