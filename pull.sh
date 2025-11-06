#!/bin/bash

set -e  # Exit on error

echo "📥 Pulling latest changes from main branch..."

# Check if Git is installed
if ! command -v git &> /dev/null && [ ! -f /usr/bin/git ]; then
    echo "❌ Error: Git is not installed!"
    echo "Please install Git to enable pulling changes."
    exit 1
fi

# Set git command (use full path if command -v didn't work)
if command -v git &> /dev/null; then
    GIT_CMD="git"
else
    GIT_CMD="/usr/bin/git"
fi

# Check if we're in a git repository
if ! $GIT_CMD rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Error: Not a git repository!"
    echo "Please run this script from within a git repository."
    exit 1
fi

# Fetch latest changes from origin
echo "📡 Fetching latest changes from origin..."
if ! $GIT_CMD fetch origin; then
    echo "❌ Error: Failed to fetch from origin"
    exit 1
fi

# Check if we're on main branch, if not switch to it
current_branch=$($GIT_CMD rev-parse --abbrev-ref HEAD)
if [ "$current_branch" != "main" ]; then
    echo "🔄 Switching to main branch (currently on $current_branch)..."
    if ! $GIT_CMD checkout main; then
        echo "❌ Error: Failed to checkout main branch"
        exit 1
    fi
fi

# Pull latest changes - this must succeed or the pull fails
echo "⬇️  Pulling latest changes from main branch..."
if ! $GIT_CMD pull origin main; then
    echo "❌ Error: Failed to pull latest changes from main branch"
    echo "Please resolve any merge conflicts or check your network connection"
    exit 1
fi

echo "✅ Latest code pulled successfully!"

