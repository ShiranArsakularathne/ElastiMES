@echo off
echo =========================================
echo Starting MES System for Elastic Manufacturer
echo =========================================

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo Docker is not running. Please start Docker and try again.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo Creating .env file from .env.example...
    copy .env.example .env >nul
    echo Please edit .env file with your configuration and run again.
    pause
    exit /b 1
)

REM Build and start services
echo Building and starting Docker containers...
docker-compose up --build -d

echo.
echo Services starting...
echo   - Web UI: http://localhost:8000
echo   - Login: http://localhost:8000/login
echo   - API Docs: http://localhost:8000/api/docs
echo.
echo To view logs: docker-compose logs -f
echo To stop: docker-compose down
echo.
echo =========================================
echo MES System is starting up...
echo Check logs with: docker-compose logs -f web
echo =========================================
pause