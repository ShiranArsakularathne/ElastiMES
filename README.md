# Industry 4.0 MES System for Elastic Manufacturer

A complete Manufacturing Execution System (MES) designed for elastic manufacturers with touch panel interfaces, built with FastAPI, dual-database architecture (SQLite + SQL Server), Redis, Celery, and modern frontend based on Figma design.

## Features

- **Touch Panel Frontend**: Modern UI based on Figma design with login page (RFID login support), sidebar navigation, and responsive layout
- **WRP Module**: Complete Warp Preparation module with three sequential pages: Beam Loading, Warp, and Unload
- **Dual Database Architecture**: Local SQLite for offline operation + Central SQL Server for synchronization
- **Real-time Hardware Integration**: PLC (Modbus TCP), RFID readers, and barcode scanner drivers
- **ERP Integration**: API client for communicating with ERP system for production plans
- **Intelligent Sync**: Automatic 20-minute sync + event-based immediate sync with retry queue
- **Real-time Communication**: WebSocket support for live updates and sensor data streaming
- **Touch Panel Integration**: Dedicated endpoints for Linux-based touch panels with hardware drivers
- **Scalable Architecture**: Microservices orchestrated with Docker Compose (Redis, FastAPI, Celery workers, Celery beat)
- **Industry 4.0 Ready**: Supports IoT integration, real‑time monitoring, and flexible manufacturing workflows

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                              │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────────┤
│   Web       │   Worker    │    Beat     │   Redis     │   SQLite    │
│ (FastAPI)   │  (Celery)   │  (Celery)   │             │   (Local)   │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘
       │             │             │            │              │
       └─────────────┼─────────────┼────────────┼──────────────┘
                     │             │            │
              ┌──────▼─────────────▼────────────▼─────────────────────┐
              │           MES Business Logic                           │
              │  • WRP Module (Beam Loading, Warp, Unload)             │
              │  • Dual Database Sync (SQLite ↔ SQL Server)            │
              │  • Hardware Drivers (PLC, RFID, Barcode)               │
              │  • ERP Integration                                     │
              │  • Real‑time WebSocket Events                          │
              └────────────────────────────────────────────────────────┘
                              │
                     ┌────────▼────────┐
                     │  Central SQL    │
                     │  Server (ERP)   │
                     └─────────────────┘
```

### Dual Database Architecture
- **Local SQLite**: Each touch panel has its own SQLite database for offline operation
- **Central SQL Server**: Centralized database for enterprise-wide data consolidation
- **Smart Sync**: 
  - Every 20 minutes: Full database synchronization
  - Event-based: Immediate transaction sync with retry queue on network failure
  - Sequence: Write to SQLite first, then attempt SQL Server sync

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Git (optional)

### 1. Clone and Configure

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings:
# - SQL Server connection (if using central database)
# - ERP API credentials
# - PLC, RFID, and barcode scanner settings
# - Redis configuration
```

### 2. Start the Stack

```bash
docker compose up --build
```

Wait for all services to become healthy. The web application will be available at `http://localhost:8000`.

### 3. Access the Application

1. **Login Page**: `http://localhost:8000/login`
   - Username/password login
   - RFID login button (simulated if no RFID reader)

2. **Main Dashboard**: `http://localhost:8000/`
   - Sidebar navigation with all modules (Home, WRP, LOOM, RANGE, etc.)
   - WRP module with Beam Loading, Warp, and Unload pages

### 4. Verify API

```bash
# Health check
curl http://localhost:8000/health

# API documentation
curl http://localhost:8000/api/docs
```

### 5. Open API Documentation

Visit `http://localhost:8000/api/docs` for interactive Swagger UI.

## Service Overview

| Service     | Port  | Description                          |
|-------------|-------|--------------------------------------|
| **web**     | 8000  | FastAPI application (REST + WebSocket + Frontend) |
| **redis**   | 6379  | Redis broker for Celery              |
| **worker**  | –     | Celery worker for async tasks        |
| **beat**    | –     | Celery beat for periodic tasks       |

## Core API Endpoints

- **Frontend**: `GET /` – Main application UI
- **Frontend**: `GET /login` – Login page with RFID support
- **Health**: `GET /health` – System health check
- **Users**: `GET /api/users` – manage operators and supervisors
- **Machines**: `GET /api/machines` – register and monitor machines
- **Work Orders**: `GET /api/work‑orders` – create and track production orders
- **Sensor Data**: `POST /api/sensor‑data` – submit sensor readings (sync/async)
- **RFID**: `GET /api/rfid` – manage RFID tags and scan events
- **Touch Panel**: `GET /api/touch` – simplified endpoints for touch panels
- **WRP Module**: `GET /api/wrp` – Warp Preparation module endpoints
- **Hardware**: `POST /api/touch/barcode/scan` – Simulate barcode scan
- **Hardware**: `POST /api/rfid/scan` – Simulate RFID scan

## Touch Panel Integration

Linux‑based touch panels with hardware integration can interact with the system via:

### Hardware Integration
- **PLC (Load Cells)**: Modbus TCP communication for weight readings
- **RFID Reader**: TCP socket communication for operator identification
- **Barcode Scanner**: Serial port communication for beam and machine scanning

### API Endpoints
- `GET /api/touch/machine/{id}/status` – get current machine status
- `POST /api/touch/machine/{id}/status` – update machine status
- `GET /api/touch/machine/{id}/work‑orders` – retrieve assigned work orders
- `POST /api/touch/rfid/scan` – report an RFID scan
- `POST /api/touch/barcode/scan` – simulate barcode scan
- `POST /api/touch/log` – submit a machine log entry

### WRP Module Flow (Beam Loading)
1. **Machine Code Scan**: Barcode scan to identify machine
2. **Plan Retrieval**: API call to ERP to get production plans
3. **Beam Code Scan**: Barcode scan to identify beam
4. **Weight Reading**: PLC load cell reading for beam weight
5. **Data Entry**: Auto-population of yarn code, beam size, ends, etc.
6. **Save & Sync**: Save to local SQLite, then sync to central SQL Server

## Database Sync Flow

1. **Local Write**: All transactions first written to local SQLite database
2. **Immediate Sync**: Attempt immediate sync to central SQL Server
3. **Queue on Failure**: If network error, transaction queued in Redis
4. **Retry**: Celery task retries failed syncs
5. **Periodic Sync**: Full database sync every 20 minutes
6. **Cleanup**: Old data cleanup daily

## Development

### Local Python Environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set environment variables (copy from .env.example)
# Configure SQL Server connection if using central database
export REDIS_HOST=localhost
# ... etc.

# Run Redis (required for Celery)
docker run -d -p 6379:6379 redis:7-alpine

# Run the application
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# In another terminal - Celery worker
celery -A app.tasks.celery_app worker --loglevel=info

# In another terminal - Celery beat (for scheduled tasks)
celery -A app.tasks.celery_app beat --loglevel=info
```

### Database Migrations

The application automatically creates tables on startup via `init_db()`. For production SQL Server synchronization, ensure proper table structures exist in the central database.

## Environment Variables

See `.env.example` for full list. Key variables:

| Variable                | Default                      | Purpose                               |
|-------------------------|------------------------------|---------------------------------------|
| `SQLITE_PATH`           | local_mes.db                 | Local SQLite database file            |
| `SQL_SERVER_HOST`       |                              | Central SQL Server host               |
| `SQL_SERVER_DATABASE`   |                              | Central SQL Server database           |
| `SQL_SERVER_USER`       |                              | Central SQL Server username           |
| `SQL_SERVER_PASSWORD`   |                              | Central SQL Server password           |
| `SYNC_ENABLED`          | true                         | Enable database synchronization       |
| `SYNC_INTERVAL_MINUTES` | 20                           | Sync interval in minutes              |
| `REDIS_*`               | redis/6379                   | Redis broker for Celery               |
| `ERP_API_URL`           | https://api.example.com/erp  | ERP API endpoint                      |
| `ERP_API_KEY`           |                              | ERP API authentication key            |
| `PLC_HOST`              | 192.168.1.100                | PLC Modbus TCP host                   |
| `PLC_PORT`              | 502                          | PLC Modbus TCP port                   |
| `RFID_READER_HOST`      | 192.168.1.101                | RFID reader TCP host                  |
| `RFID_READER_PORT`      | 10001                        | RFID reader TCP port                  |
| `BARCODE_SCANNER_PORT`  | /dev/ttyUSB0                 | Barcode scanner serial port           |
| `SECRET_KEY`            | change_this                  | JWT signing key (future auth)         |

## Deployment

### Docker Compose (Production)

1. Review `docker‑compose.yml` and adjust resource limits, volumes, and networks.
2. Set strong passwords in `.env` (do not commit `.env`).
3. Run with:
   ```bash
   docker compose -f docker-compose.yml up -d
   ```

### Cloud / Orchestration

The stack is compatible with Kubernetes, Docker Swarm, or any container orchestrator. Each service can be scaled independently.

## Monitoring

- **Health**: `GET /health` returns database and Redis status.
- **Logs**: Use `docker compose logs [service]` to view container logs.
- **Metrics**: (Future) Integrate Prometheus and Grafana for operational metrics.

## License

MIT License. See `LICENSE` file.

## Acknowledgements

- Built with [FastAPI](https://fastapi.tiangolo.com/), [Celery](https://docs.celeryq.dev/), [PostgreSQL](https://www.postgresql.org/), [Redis](https://redis.io/).
- Designed for Industry 4.0 and flexible manufacturing systems.
