#!/bin/bash

set -e  # Exit on error

ENVIRONMENT=${1:-production}

echo "⏳ Waiting 10 seconds before starting build..."
sleep 10

echo "🚀 Building web application image in $ENVIRONMENT mode..."

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

# Check if postgres container exists and is running (needed for build dependencies)
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