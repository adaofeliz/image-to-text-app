#!/bin/bash

set -e  # Exit on error

ENVIRONMENT=${1:-production}

echo "🚀 Starting deployment in $ENVIRONMENT mode..."

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

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Error: Docker Compose is not installed!"
    exit 1
fi

# Stop existing containers
echo "🛑 Stopping existing containers..."
if [ "$ENVIRONMENT" = "production" ]; then
    docker-compose -f docker-compose.prod.yml down 2>/dev/null || true
else
    docker-compose down 2>/dev/null || true
fi

# Build and start services
echo "🔨 Building and starting services..."
if [ "$ENVIRONMENT" = "production" ]; then
    docker-compose -f docker-compose.prod.yml up -d --build
    echo "✅ Production deployment complete!"
    echo "📊 Checking service status..."
    docker-compose -f docker-compose.prod.yml ps
else
    docker-compose up -d --build
    echo "✅ Development deployment complete!"
    echo "📊 Checking service status..."
    docker-compose ps
fi

# Wait a moment for services to start
sleep 5

# Check health
echo "🏥 Checking service health..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API is healthy and running!"
    echo "🌐 API available at: http://localhost:8000"
else
    echo "⚠️  Warning: Health check failed. Check logs with:"
    if [ "$ENVIRONMENT" = "production" ]; then
        echo "   docker-compose -f docker-compose.prod.yml logs"
    else
        echo "   docker-compose logs"
    fi
fi


