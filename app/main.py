from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio
import redis
import json

from .database import get_db, engine, init_db
from .routers import users, machines, workorders, sensor_data, rfid, sql, touchpanel, wrp
from .schemas import HealthCheck

# Initialize database tables
init_db()

app = FastAPI(
    title="Industry 4.0 MES System",
    description="Manufacturing Execution System for elastic manufacturer",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")


# Include routers
app.include_router(users.router, prefix="/api")
app.include_router(machines.router, prefix="/api")
app.include_router(workorders.router, prefix="/api")
app.include_router(sensor_data.router, prefix="/api")
app.include_router(rfid.router, prefix="/api")
app.include_router(sql.router, prefix="/api")
app.include_router(touchpanel.router, prefix="/api")
app.include_router(wrp.router, prefix="/api")

# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# Redis connection for health check
redis_client = redis.Redis(host="redis", port=6379, db=0, socket_connect_timeout=1)

@app.get("/health", response_model=HealthCheck)
async def health_check(db: Session = Depends(get_db)):
    db_healthy = False
    redis_healthy = False
    
    # Check database
    try:
        db.execute("SELECT 1")
        db_healthy = True
    except:
        db_healthy = False
    
    # Check Redis
    try:
        redis_client.ping()
        redis_healthy = True
    except:
        redis_healthy = False
    
    overall_status = "healthy" if db_healthy and redis_healthy else "unhealthy"
    
    return HealthCheck(
        status=overall_status,
        database=db_healthy,
        redis=redis_healthy,
        timestamp=datetime.utcnow(),
    )

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/login")
async def login():
    return FileResponse("static/login.html")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo received message (could be commands)
            await manager.send_personal_message(f"Echo: {data}", websocket)
            # Broadcast to all clients if needed
            # await manager.broadcast(f"Client says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.websocket("/ws/sensor-data")
async def sensor_data_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Simulate sending sensor data updates periodically
            # In production, this would push real-time sensor data
            await asyncio.sleep(5)
            message = {
                "type": "sensor_update",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "machine_id": 1,
                    "sensor_type": "temperature",
                    "value": 25.5,
                    "unit": "C"
                }
            }
            await websocket.send_text(json.dumps(message))
    except WebSocketDisconnect:
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)