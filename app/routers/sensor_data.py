from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from ..database import get_db
from ..models import SensorData, Machine
from ..schemas import SensorDataCreate, SensorData as SensorDataSchema
from ..tasks import process_sensor_data as process_sensor_data_task

router = APIRouter(
    prefix="/sensor-data",
    tags=["sensor-data"],
)

@router.post("/", response_model=SensorDataSchema, status_code=status.HTTP_201_CREATED)
def create_sensor_data(data: SensorDataCreate, db: Session = Depends(get_db)):
    machine = db.query(Machine).filter(Machine.id == data.machine_id).first()
    if not machine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    
    db_data = SensorData(**data.dict())
    db.add(db_data)
    db.commit()
    db.refresh(db_data)
    return db_data

@router.post("/async")
def create_sensor_data_async(data: SensorDataCreate):
    """Submit sensor data asynchronously via Celery."""
    task = process_sensor_data_task.delay(data.dict())
    return {"task_id": task.id, "status": "processing"}

@router.get("/", response_model=List[SensorDataSchema])
def read_sensor_data(
    machine_id: Optional[int] = None,
    sensor_type: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(SensorData)
    if machine_id:
        query = query.filter(SensorData.machine_id == machine_id)
    if sensor_type:
        query = query.filter(SensorData.sensor_type == sensor_type)
    if start_time:
        query = query.filter(SensorData.timestamp >= start_time)
    if end_time:
        query = query.filter(SensorData.timestamp <= end_time)
    
    query = query.order_by(SensorData.timestamp.desc())
    data = query.offset(skip).limit(limit).all()
    return data

@router.get("/{data_id}", response_model=SensorDataSchema)
def read_sensor_data_by_id(data_id: int, db: Session = Depends(get_db)):
    data = db.query(SensorData).filter(SensorData.id == data_id).first()
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor data not found")
    return data

@router.delete("/{data_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sensor_data(data_id: int, db: Session = Depends(get_db)):
    data = db.query(SensorData).filter(SensorData.id == data_id).first()
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sensor data not found")
    
    db.delete(data)
    db.commit()
    return None

@router.get("/machines/{machine_id}/latest")
def get_latest_sensor_data(machine_id: int, db: Session = Depends(get_db)):
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    
    # Get latest sensor data for each sensor type
    subquery = db.query(
        SensorData.sensor_type,
        SensorData.value,
        SensorData.unit,
        SensorData.timestamp
    ).filter(
        SensorData.machine_id == machine_id
    ).order_by(
        SensorData.timestamp.desc()
    ).distinct(
        SensorData.sensor_type
    ).subquery()
    
    # This is a simplified approach; actual implementation may vary
    latest_data = db.query(subquery).all()
    return latest_data