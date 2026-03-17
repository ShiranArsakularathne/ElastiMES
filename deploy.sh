#!/bin/bash

# Deploy script for SQL Server Query API
# This script helps users quickly deploy the API using Docker Compose

set -e

echo "=== SQL Server Query API Deployment ==="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env file to set your configuration (API_KEY_HASH, ALLOWED_SERVERS, etc.)"
    echo "You can generate an API key hash using:"
    echo "  echo -n 'your-api-key' | sha256sum"
    exit 1
fi

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose."
    exit 1
fi

echo "Building and starting containers..."
docker-compose up --build -d

echo "Deployment completed!"
echo "API should be running at http://localhost:8000"
echo "Check health endpoint: curl http://localhost:8000/health"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"