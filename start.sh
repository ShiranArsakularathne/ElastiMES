#!/bin/bash
# MES System Start Script

set -e

echo "========================================="
echo "Starting MES System for Elastic Manufacturer"
echo "========================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please edit .env file with your configuration and run again."
    exit 1
fi

# Build and start services
echo "Building and starting Docker containers..."
docker-compose up --build -d

echo ""
echo "Services starting..."
echo "  - Web UI: http://localhost:8000"
echo "  - Login: http://localhost:8000/login"
echo "  - API Docs: http://localhost:8000/api/docs"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"
echo ""
echo "========================================="
echo "MES System is starting up..."
echo "Check logs with: docker-compose logs -f web"
echo "========================================="