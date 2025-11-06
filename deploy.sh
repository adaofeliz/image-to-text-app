#!/bin/bash

set -e  # Exit on error

ENVIRONMENT=${1:-production}

echo "⏳ Waiting 10 seconds before starting deployment..."
sleep 10

echo "🚀 Starting deployment in $ENVIRONMENT mode..."

# Determine which compose file to use
if [ "$ENVIRONMENT" = "production" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
else
    COMPOSE_FILE="docker-compose.yml"
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with your configuration."
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null && [ ! -f /usr/bin/docker ]; then
    echo "❌ Error: Docker is not installed!"
    exit 1
fi

# Set docker command (use full path if command -v didn't work)
if command -v docker &> /dev/null; then
    DOCKER_CMD="docker"
else
    DOCKER_CMD="/usr/bin/docker"
fi

# Check if Docker Compose is installed (support both docker-compose and docker compose)
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif $DOCKER_CMD compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE="$DOCKER_CMD compose"
else
    echo "❌ Error: Docker Compose is not installed!"
    echo "Please install Docker Compose (either 'docker-compose' or 'docker compose' plugin)"
    exit 1
fi

# Gracefully stop existing services managed by this compose file
echo "🛑 Gracefully stopping existing services..."
$DOCKER_COMPOSE -f $COMPOSE_FILE down 2>/dev/null || true

# Build and recreate services with latest code
echo "🔨 Building and starting services with latest code..."
$DOCKER_COMPOSE -f $COMPOSE_FILE up -d --build --force-recreate
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


