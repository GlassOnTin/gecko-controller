#!/bin/bash
# tools/bump-version.sh - For updating versions
set -e

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <new-version>"
    exit 1
fi

NEW_VERSION="$1"

# Get user info from git config
GIT_NAME=$(git config user.name)
GIT_EMAIL=$(git config user.email)

if [ -z "$GIT_NAME" ] || [ -z "$GIT_EMAIL" ]; then
    echo "Error: Git user.name or user.email not set"
    echo "Please set them using:"
    echo "  git config --global user.name 'Your Name'"
    echo "  git config --global user.email 'your.email@example.com'"
    exit 1
fi

# Set environment variables for dch
export DEBEMAIL="$GIT_EMAIL"
export DEBFULLNAME="$GIT_NAME"

echo "Updating version to $NEW_VERSION..."

# Update setup.py - preserving quote style
if grep -q 'version="' setup.py; then
    # Using double quotes
    sed -i "s/version=\"[^\"]*\"/version=\"$NEW_VERSION\"/" setup.py
else
    # Using single quotes
    sed -i "s/version='[^']*'/version='$NEW_VERSION'/" setup.py
fi

# Update debian/changelog
dch --newversion "$NEW_VERSION" --distribution stable --urgency medium "Release $NEW_VERSION"
dch --release ""

# Create git commit and tag
git add setup.py debian/changelog
git commit -m "Bump version to $NEW_VERSION"
git tag -a "v$NEW_VERSION" -m "Release version $NEW_VERSION"

echo "Version bumped to $NEW_VERSION"
echo "Changes made:"
echo "  - Updated setup.py version"
echo "  - Updated debian/changelog"
echo "  - Created git commit"
echo "  - Created git tag v$NEW_VERSION"
echo ""
echo "Don't forget to push changes and tags:"
echo "  git push origin main"
echo "  git push origin v$NEW_VERSION"