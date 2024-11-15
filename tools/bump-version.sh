#!/bin/bash
# tools/bump-version.sh - For updating versions
set -e

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <new-version>"
    exit 1
fi

NEW_VERSION="$1"
TIMESTAMP=$(date -R)
MAINTAINER="Ian Ross Williams <ianrosswilliams@gmail.com>"

# Update setup.py
sed -i "s/version='[^']*'/version='$NEW_VERSION'/" setup.py

# Update debian/changelog
dch --newversion "$NEW_VERSION" --distribution stable --urgency medium "Release $NEW_VERSION"
dch --release ""

# Create git commit and tag
git add setup.py debian/changelog
git commit -m "Bump version to $NEW_VERSION"
git tag -a "v$NEW_VERSION" -m "Release version $NEW_VERSION"

echo "Version bumped to $NEW_VERSION"
echo "Don't forget to push changes and tags:"
echo "  git push origin main"
echo "  git push origin v$NEW_VERSION"