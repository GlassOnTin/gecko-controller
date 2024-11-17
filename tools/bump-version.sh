#!/bin/bash
# tools/bump-version.sh - For updating versions
set -e

# Function to extract current version from setup.py
get_current_version() {
    if grep -q 'version="' setup.py; then
        grep 'version="' setup.py | sed 's/.*version="\([^"]*\)".*/\1/'
    else
        grep "version='" setup.py | sed "s/.*version='\([^']*\)'.*/\1/"
    fi
}

# Function to increment patch version
increment_patch_version() {
    local version=$1
    echo "$version" | awk -F. '{$NF = $NF + 1;} 1' | sed 's/ /./g'
}

# Parse command line options
COMMIT_MSG=""
NEW_VERSION=""

while getopts "m:v:h" opt; do
    case $opt in
        m)
            COMMIT_MSG="$OPTARG"
            ;;
        v)
            NEW_VERSION="$OPTARG"
            ;;
        h)
            echo "Usage: $0 [-v version] [-m commit-message]"
            echo "Options:"
            echo "  -v version         Specify new version (if omitted, patch version will be incremented)"
            echo "  -m commit-message  Specify git commit message (default: 'Bump version to <version>')"
            echo "  -h                 Show this help message"
            exit 0
            ;;
        \?)
            echo "Invalid option: -$OPTARG" >&2
            exit 1
            ;;
    esac
done

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

# If no version specified, increment patch version
if [ -z "$NEW_VERSION" ]; then
    CURRENT_VERSION=$(get_current_version)
    NEW_VERSION=$(increment_patch_version "$CURRENT_VERSION")
    echo "No version specified. Incrementing patch version from $CURRENT_VERSION to $NEW_VERSION"
fi

# If no commit message specified, use default
if [ -z "$COMMIT_MSG" ]; then
    COMMIT_MSG="Bump version to $NEW_VERSION"
fi

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
dch --newversion "$NEW_VERSION" --distribution stable --urgency medium "$COMMIT_MSG"
dch --release ""

# Create git commit and tag
git add setup.py debian/changelog
git commit -m "$COMMIT_MSG"
git tag -a "v$NEW_VERSION" -m "Release version $NEW_VERSION"

echo "Version bumped to $NEW_VERSION"
echo "Changes made:"
echo "  - Updated setup.py version"
echo "  - Updated debian/changelog"
echo "  - Created git commit with message: $COMMIT_MSG"
echo "  - Created git tag v$NEW_VERSION"
echo ""
echo "Don't forget to push changes and tags:"
echo "  git push origin main"
echo "  git push origin v$NEW_VERSION"