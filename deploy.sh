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


