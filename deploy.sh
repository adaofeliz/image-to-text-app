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

# Stop existing containers and clean up all resources
echo "🛑 Stopping existing containers and cleaning up resources..."
$DOCKER_COMPOSE -f $COMPOSE_FILE down --remove-orphans --volumes 2>/dev/null || true

# Force remove any conflicting containers by name pattern (Ubuntu/Linux compatible)
echo "🧹 Force removing any conflicting containers..."
$DOCKER_CMD ps -a --filter "name=postgres" --format "{{.Names}}" 2>/dev/null | while read -r container; do
    [ -n "$container" ] && $DOCKER_CMD rm -f "$container" 2>/dev/null || true
done || true

$DOCKER_CMD ps -a --filter "name=web" --format "{{.Names}}" 2>/dev/null | while read -r container; do
    [ -n "$container" ] && $DOCKER_CMD rm -f "$container" 2>/dev/null || true
done || true

$DOCKER_CMD ps -a --filter "name=project-" --format "{{.Names}}" 2>/dev/null | while read -r container; do
    [ -n "$container" ] && $DOCKER_CMD rm -f "$container" 2>/dev/null || true
done || true

# Stop any containers using port 8000 (Ubuntu/Linux compatible)
echo "🔌 Checking for containers using port 8000..."
$DOCKER_CMD ps --filter "publish=8000" --format "{{.ID}}" 2>/dev/null | while read -r container; do
    if [ -n "$container" ]; then
        echo "⚠️  Found container $container using port 8000, stopping it..."
        $DOCKER_CMD stop "$container" 2>/dev/null || true
        $DOCKER_CMD rm -f "$container" 2>/dev/null || true
    fi
done || true

# Also check stopped containers using port 8000
$DOCKER_CMD ps -a --filter "publish=8000" --format "{{.ID}}" 2>/dev/null | while read -r container; do
    [ -n "$container" ] && $DOCKER_CMD rm -f "$container" 2>/dev/null || true
done || true

# Remove any orphaned networks
echo "🌐 Cleaning up orphaned networks..."
$DOCKER_CMD network prune -f 2>/dev/null || true

# Wait a moment for cleanup to complete
sleep 2

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


