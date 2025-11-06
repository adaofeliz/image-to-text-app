#!/bin/bash

set -e  # Exit on error

ENVIRONMENT=${1:-production}

echo "🚀 Starting deployment in $ENVIRONMENT mode..."

# Determine which compose file to use
if [ "$ENVIRONMENT" = "production" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
else
    COMPOSE_FILE="docker-compose.yml"
fi

# Pull latest changes from main branch
# Git is required for deployment
if ! command -v git &> /dev/null && [ ! -f /usr/bin/git ]; then
    echo "❌ Error: Git is not installed!"
    echo "Please install Git to enable deployment."
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
    echo "Deployment requires a git repository."
    exit 1
fi

echo "📥 Pulling latest changes from main branch..."

# Fetch latest changes from origin
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

# Pull latest changes - this must succeed or deployment fails
if ! $GIT_CMD pull origin main; then
    echo "❌ Error: Failed to pull latest changes from main branch"
    echo "Please resolve any merge conflicts or check your network connection"
    exit 1
fi

echo "✅ Latest code pulled successfully"

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with your configuration."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed!"
    exit 1
fi

# Check if Docker Compose is installed (support both docker-compose and docker compose)
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    echo "❌ Error: Docker Compose is not installed!"
    echo "Please install Docker Compose (either 'docker-compose' or 'docker compose' plugin)"
    exit 1
fi

# Stop existing containers
echo "🛑 Stopping existing containers..."
$DOCKER_COMPOSE -f $COMPOSE_FILE down 2>/dev/null || true

# Build and start services
echo "🔨 Building and starting services..."
$DOCKER_COMPOSE -f $COMPOSE_FILE up -d --build
echo "✅ $ENVIRONMENT deployment complete!"
echo "📊 Checking service status..."
$DOCKER_COMPOSE -f $COMPOSE_FILE ps

# Wait a moment for services to start
sleep 5

# Check health (only if curl is available)
echo "🏥 Checking service health..."
if command -v curl &> /dev/null; then
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ API is healthy and running!"
        echo "🌐 API available at: http://localhost:8000"
    else
        echo "⚠️  Warning: Health check failed. Check logs with:"
        echo "   $DOCKER_COMPOSE -f $COMPOSE_FILE logs"
    fi
else
    echo "ℹ️  curl not available, skipping health check"
    echo "   Check service status with: $DOCKER_COMPOSE -f $COMPOSE_FILE ps"
    echo "   View logs with: $DOCKER_COMPOSE -f $COMPOSE_FILE logs"
fi


