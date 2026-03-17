from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ..database import get_db
from ..models import Machine, MachineStatus, MachineLog
from ..schemas import MachineCreate, MachineUpdate, Machine as MachineSchema, MachineLogCreate, MachineLog as MachineLogSchema

router = APIRouter(
    prefix="/machines",
    tags=["machines"],
)

@router.post("/", response_model=MachineSchema, status_code=status.HTTP_201_CREATED)
def create_machine(machine: MachineCreate, db: Session = Depends(get_db)):
    existing_machine = db.query(Machine).filter(Machine.name == machine.name).first()
    if existing_machine:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Machine with this name already exists"
        )
    
    db_machine = Machine(**machine.dict())
    db.add(db_machine)
    db.commit()
    db.refresh(db_machine)
    return db_machine

@router.get("/", response_model=List[MachineSchema])
def read_machines(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    machines = db.query(Machine).offset(skip).limit(limit).all()
    return machines

@router.get("/{machine_id}", response_model=MachineSchema)
def read_machine(machine_id: int, db: Session = Depends(get_db)):
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if machine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    return machine

@router.put("/{machine_id}", response_model=MachineSchema)
def update_machine(machine_id: int, machine_update: MachineUpdate, db: Session = Depends(get_db)):
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if machine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    
    update_data = machine_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(machine, field, value)
    
    db.commit()
    db.refresh(machine)
    return machine

@router.delete("/{machine_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_machine(machine_id: int, db: Session = Depends(get_db)):
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if machine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    
    db.delete(machine)
    db.commit()
    return None

@router.post("/{machine_id}/status", response_model=MachineSchema)
def update_machine_status(machine_id: int, status: MachineStatus, db: Session = Depends(get_db)):
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if machine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    
    machine.status = status
    machine.last_seen = datetime.utcnow()
    db.commit()
    db.refresh(machine)
    return machine

@router.post("/{machine_id}/logs", response_model=MachineLogSchema, status_code=status.HTTP_201_CREATED)
def create_machine_log(machine_id: int, log: MachineLogCreate, db: Session = Depends(get_db)):
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if machine is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    
    db_log = MachineLog(machine_id=machine_id, **log.dict())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

@router.get("/{machine_id}/logs", response_model=List[MachineLogSchema])
def read_machine_logs(machine_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logs = db.query(MachineLog).filter(MachineLog.machine_id == machine_id).offset(skip).limit(limit).all()
    return logs