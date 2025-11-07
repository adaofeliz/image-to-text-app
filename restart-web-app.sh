#!/bin/bash

set -e  # Exit on error

ENVIRONMENT=${1:-production}

echo "🔄 Restarting web container in $ENVIRONMENT mode..."

# Determine which compose file to use
if [ "$ENVIRONMENT" = "production" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
else
    COMPOSE_FILE="docker-compose.yml"
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed!"
    exit 1
fi

DOCKER_CMD="docker"

# Check if Docker Compose is installed
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif $DOCKER_CMD compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE="$DOCKER_CMD compose"
else
    echo "❌ Error: Docker Compose is not installed!"
    exit 1
fi

# Stop and remove the existing web container
echo "🛑 Stopping existing web container..."
if $DOCKER_CMD ps --filter "name=image-to-text-app-web" --format "{{.Names}}" | grep -q "^image-to-text-app-web$"; then
    $DOCKER_CMD stop image-to-text-app-web
    echo "   ✅ Container stopped"
else
    echo "   ℹ️  Container was not running"
fi

if $DOCKER_CMD ps -a --filter "name=image-to-text-app-web" --format "{{.Names}}" | grep -q "^image-to-text-app-web$"; then
    $DOCKER_CMD rm -f image-to-text-app-web
    echo "   ✅ Container removed"
else
    echo "   ℹ️  Container did not exist"
fi

# Create and start the new web container with the latest image
echo "🚀 Creating and starting web container with latest image..."
$DOCKER_COMPOSE -f $COMPOSE_FILE up -d --no-deps web

echo "✅ Web container restarted successfully!"

# Wait a moment for the container to start
echo "⏳ Waiting for container to start..."
sleep 3

# Check if container is running
if $DOCKER_CMD ps --filter "name=image-to-text-app-web" --format "{{.Names}}" | grep -q "^image-to-text-app-web$"; then
    echo "✅ Container is running"
    
    # Check health (only if curl is available)
    if command -v curl &> /dev/null; then
        echo "🏥 Checking service health..."
        sleep 2
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            echo "✅ API is healthy and running!"
            echo "🌐 API available at: http://localhost:8000"
        else
            echo "⚠️  Health check failed, but container is running"
            echo "   Check logs with: $DOCKER_COMPOSE -f $COMPOSE_FILE logs web"
        fi
    fi
else
    echo "❌ Error: Container failed to start"
    echo "   Check logs with: $DOCKER_COMPOSE -f $COMPOSE_FILE logs web"
    exit 1
fi

