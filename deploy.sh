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

# Set docker command
if command -v docker &> /dev/null; then
    DOCKER_CMD="docker"
else
    DOCKER_CMD="/usr/bin/docker"
fi

# Check if Docker Compose is installed
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif $DOCKER_CMD compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE="$DOCKER_CMD compose"
else
    echo "❌ Error: Docker Compose is not installed!"
    echo "Please install Docker Compose (either 'docker-compose' or 'docker compose' plugin)"
    exit 1
fi

# Check if postgres container exists and is running
echo "🔍 Checking postgres container status..."
if $DOCKER_CMD ps --filter "name=postgres" --format "{{.Names}}" | grep -q "^postgres$"; then
    echo "✅ Postgres container is running"
elif $DOCKER_CMD ps -a --filter "name=postgres" --format "{{.Names}}" | grep -q "^postgres$"; then
    echo "🔄 Starting existing postgres container..."
    $DOCKER_CMD start postgres
else
    echo "📦 Creating postgres container..."
    $DOCKER_COMPOSE -f $COMPOSE_FILE up -d postgres
fi

# Check if watchtower container exists and is running
echo "🔍 Checking watchtower container status..."
if $DOCKER_CMD ps --filter "name=watchtower" --format "{{.Names}}" | grep -q "^watchtower$"; then
    echo "✅ Watchtower container is running"
elif $DOCKER_CMD ps -a --filter "name=watchtower" --format "{{.Names}}" | grep -q "^watchtower$"; then
    echo "🔄 Starting existing watchtower container..."
    $DOCKER_CMD start watchtower
else
    echo "📦 Creating watchtower container..."
    $DOCKER_COMPOSE -f $COMPOSE_FILE up -d watchtower
fi

# Wait for postgres to be healthy
echo "⏳ Checking postgres health..."
if ! $DOCKER_CMD exec postgres pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-postgres} > /dev/null 2>&1; then
    echo "⏳ Waiting for postgres to become healthy..."
    timeout=60
    elapsed=0
    while ! $DOCKER_CMD exec postgres pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-postgres} > /dev/null 2>&1; do
        if [ $elapsed -ge $timeout ]; then
            echo "❌ Error: Postgres failed to become healthy within ${timeout} seconds"
            exit 1
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        echo "   Waiting for postgres... (${elapsed}/${timeout}s)"
    done
fi
echo "✅ Postgres is healthy"

# Build only the web service image
echo "🔨 Building FastAPI application image..."
$DOCKER_COMPOSE -f $COMPOSE_FILE build web

echo "✅ Image built successfully!"
echo "🔄 Watchtower will automatically detect the new image and update the web container"
echo "   (This typically happens within 30 seconds due to Watchtower's polling interval)"

# Wait a moment for watchtower to detect and update
echo "⏳ Waiting for Watchtower to update the container (up to 35 seconds)..."
sleep 35

echo "📊 Checking service status..."
$DOCKER_COMPOSE -f $COMPOSE_FILE ps

# Check health (only if curl is available)
echo "🏥 Checking service health..."
if command -v curl &> /dev/null; then
    max_attempts=6
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            echo "✅ API is healthy and running!"
            echo "🌐 API available at: http://localhost:8000"
            exit 0
        else
            if [ $attempt -lt $max_attempts ]; then
                echo "   Health check attempt $attempt/$max_attempts failed, retrying in 5 seconds..."
                sleep 5
            fi
            attempt=$((attempt + 1))
        fi
    done
    echo "⚠️  Warning: Health check failed after $max_attempts attempts."
    echo "   The container may still be updating. Check status with:"
    echo "   $DOCKER_COMPOSE -f $COMPOSE_FILE ps"
    echo "   $DOCKER_COMPOSE -f $COMPOSE_FILE logs web"
    echo "   $DOCKER_CMD logs watchtower"
else
    echo "ℹ️  curl not available, skipping health check"
    echo "   Check service status with: $DOCKER_COMPOSE -f $COMPOSE_FILE ps"
    echo "   View logs with: $DOCKER_COMPOSE -f $COMPOSE_FILE logs web"
fi
