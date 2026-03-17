from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ..database import get_db
from ..models import WorkOrder, WorkOrderStatus, WorkOrderEvent, Machine, User
from ..schemas import WorkOrderCreate, WorkOrderUpdate, WorkOrder as WorkOrderSchema, WorkOrderEventCreate, WorkOrderEvent as WorkOrderEventSchema

router = APIRouter(
    prefix="/work-orders",
    tags=["work-orders"],
)

@router.post("/", response_model=WorkOrderSchema, status_code=status.HTTP_201_CREATED)
def create_work_order(order: WorkOrderCreate, db: Session = Depends(get_db)):
    existing_order = db.query(WorkOrder).filter(WorkOrder.order_number == order.order_number).first()
    if existing_order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Work order with this order number already exists"
        )
    
    if order.machine_id:
        machine = db.query(Machine).filter(Machine.id == order.machine_id).first()
        if not machine:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    
    if order.assigned_operator_id:
        user = db.query(User).filter(User.id == order.assigned_operator_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    db_order = WorkOrder(**order.dict())
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

@router.get("/", response_model=List[WorkOrderSchema])
def read_work_orders(
    skip: int = 0,
    limit: int = 100,
    status: WorkOrderStatus = None,
    machine_id: int = None,
    db: Session = Depends(get_db)
):
    query = db.query(WorkOrder)
    if status:
        query = query.filter(WorkOrder.status == status)
    if machine_id:
        query = query.filter(WorkOrder.machine_id == machine_id)
    
    orders = query.offset(skip).limit(limit).all()
    return orders

@router.get("/{order_id}", response_model=WorkOrderSchema)
def read_work_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(WorkOrder).filter(WorkOrder.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")
    return order

@router.put("/{order_id}", response_model=WorkOrderSchema)
def update_work_order(order_id: int, order_update: WorkOrderUpdate, db: Session = Depends(get_db)):
    order = db.query(WorkOrder).filter(WorkOrder.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")
    
    if order_update.machine_id:
        machine = db.query(Machine).filter(Machine.id == order_update.machine_id).first()
        if not machine:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    
    if order_update.assigned_operator_id:
        user = db.query(User).filter(User.id == order_update.assigned_operator_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    update_data = order_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)
    
    db.commit()
    db.refresh(order)
    return order

@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_work_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(WorkOrder).filter(WorkOrder.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")
    
    db.delete(order)
    db.commit()
    return None

@router.post("/{order_id}/events", response_model=WorkOrderEventSchema, status_code=status.HTTP_201_CREATED)
def create_work_order_event(order_id: int, event: WorkOrderEventCreate, db: Session = Depends(get_db)):
    order = db.query(WorkOrder).filter(WorkOrder.id == order_id).first()
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")
    
    db_event = WorkOrderEvent(work_order_id=order_id, **event.dict())
    db.add(db_event)
    
    # Update work order quantity if quantity_change is provided
    if event.quantity_change != 0:
        order.quantity_completed += event.quantity_change
        if order.quantity_completed < 0:
            order.quantity_completed = 0
        if order.quantity_completed >= order.quantity:
            order.status = WorkOrderStatus.COMPLETED
    
    db.commit()
    db.refresh(db_event)
    return db_event

@router.get("/{order_id}/events", response_model=List[WorkOrderEventSchema])
def read_work_order_events(order_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    events = db.query(WorkOrderEvent).filter(WorkOrderEvent.work_order_id == order_id).offset(skip).limit(limit).all()
    return events