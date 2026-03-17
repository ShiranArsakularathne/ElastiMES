from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import random
import string

from ..database import get_db
from ..models import Machine, WorkOrder, WorkOrderStatus, RFIDTag, MachineLog
from ..schemas import Machine as MachineSchema, WorkOrder as WorkOrderSchema, RFIDTag as RFIDTagSchema
from ..tasks import update_machine_status, log_machine_event

router = APIRouter(
    prefix="/touch",
    tags=["touchpanel"],
)

@router.get("/machine/{machine_id}/status", response_model=MachineSchema)
def get_machine_status(machine_id: int, db: Session = Depends(get_db)):
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    return machine

@router.post("/machine/{machine_id}/status")
def set_machine_status(machine_id: int, status: str, db: Session = Depends(get_db)):
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    
    # Update via Celery task for async processing
    task = update_machine_status.delay(machine_id, status)
    return {"task_id": task.id, "status": "updating"}

@router.get("/machine/{machine_id}/work-orders", response_model=List[WorkOrderSchema])
def get_assigned_work_orders(machine_id: int, db: Session = Depends(get_db)):
    orders = db.query(WorkOrder).filter(
        WorkOrder.machine_id == machine_id,
        WorkOrder.status.in_([WorkOrderStatus.PENDING, WorkOrderStatus.IN_PROGRESS])
    ).order_by(WorkOrder.priority.desc(), WorkOrder.due_date).all()
    return orders

@router.post("/work-order/{order_id}/start")
def start_work_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(WorkOrder).filter(WorkOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")
    
    if order.status != WorkOrderStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Work order not in pending state")
    
    order.status = WorkOrderStatus.IN_PROGRESS
    order.updated_at = datetime.utcnow()
    db.commit()
    
    # Log event
    log_machine_event.delay(
        machine_id=order.machine_id,
        log_type="info",
        message=f"Started work order {order.order_number}",
        details={"work_order_id": order.id}
    )
    
    return {"status": "started", "order_id": order.id}

@router.post("/work-order/{order_id}/complete")
def complete_work_order(order_id: int, quantity: int, db: Session = Depends(get_db)):
    order = db.query(WorkOrder).filter(WorkOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work order not found")
    
    if order.status != WorkOrderStatus.IN_PROGRESS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Work order not in progress")
    
    order.quantity_completed += quantity
    if order.quantity_completed >= order.quantity:
        order.status = WorkOrderStatus.COMPLETED
    
    order.updated_at = datetime.utcnow()
    db.commit()
    
    log_machine_event.delay(
        machine_id=order.machine_id,
        log_type="info",
        message=f"Completed {quantity} units for work order {order.order_number}",
        details={"work_order_id": order.id, "quantity": quantity}
    )
    
    return {"status": "updated", "order_id": order.id, "quantity_completed": order.quantity_completed}

@router.post("/rfid/scan")
def scan_rfid(tag_id: str, machine_id: Optional[int] = None, db: Session = Depends(get_db)):
    tag = db.query(RFIDTag).filter(RFIDTag.tag_id == tag_id).first()
    if not tag:
        tag = RFIDTag(tag_id=tag_id)
        db.add(tag)
    
    tag.last_seen = datetime.utcnow()
    db.commit()
    
    # Determine action based on assignment
    action = "unknown"
    if tag.assigned_to:
        if tag.assigned_to.startswith("operator:"):
            operator_id = tag.assigned_to.split(":")[1]
            action = f"operator_{operator_id}_present"
        elif tag.assigned_to.startswith("machine:"):
            assigned_machine_id = tag.assigned_to.split(":")[1]
            action = f"machine_{assigned_machine_id}_identified"
    
    # If machine_id provided, log the scan for that machine
    if machine_id:
        log_machine_event.delay(
            machine_id=machine_id,
            log_type="info",
            message=f"RFID tag scanned: {tag_id}",
            details={"tag_id": tag_id, "assigned_to": tag.assigned_to, "action": action}
        )
    
    return {
        "tag_id": tag_id,
        "assigned_to": tag.assigned_to,
        "action": action,
        "timestamp": tag.last_seen.isoformat()
    }

@router.post("/log")
def create_log(
    machine_id: int,
    log_type: str,
    message: str,
    details: Optional[dict] = None,
    db: Session = Depends(get_db)
):
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    
    task = log_machine_event.delay(machine_id, log_type, message, details)
    return {"task_id": task.id, "status": "logged"}

@router.get("/dashboard/{machine_id}")
def get_touch_dashboard(machine_id: int, db: Session = Depends(get_db)):
    machine = db.query(Machine).filter(Machine.id == machine_id).first()
    if not machine:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Machine not found")
    
    active_orders = db.query(WorkOrder).filter(
        WorkOrder.machine_id == machine_id,
        WorkOrder.status.in_([WorkOrderStatus.PENDING, WorkOrderStatus.IN_PROGRESS])
    ).order_by(WorkOrder.priority.desc()).limit(5).all()
    
    recent_logs = db.query(MachineLog).filter(
        MachineLog.machine_id == machine_id
    ).order_by(MachineLog.timestamp.desc()).limit(10).all()
    
    return {
        "machine": {
            "id": machine.id,
            "name": machine.name,
            "status": machine.status.value,
            "last_seen": machine.last_seen,
        },
        "active_orders": [
            {
                "id": order.id,
                "order_number": order.order_number,
                "product_name": order.product_name,
                "quantity": order.quantity,
                "quantity_completed": order.quantity_completed,
                "status": order.status.value,
                "priority": order.priority,
            }
            for order in active_orders
        ],
        "recent_logs": [
            {
                "id": log.id,
                "log_type": log.log_type,
                "message": log.message,
                "timestamp": log.timestamp,
            }
            for log in recent_logs
        ]
    }


@router.post("/barcode/scan")
def scan_barcode(db: Session = Depends(get_db)):
    """Simulate a barcode scan by generating a random barcode."""
    # In production, this would read from the barcode driver
    barcode = "BEAM-" + ''.join(random.choices(string.digits, k=8))
    
    return {
        "code": barcode,
        "type": "beam",
        "timestamp": datetime.utcnow().isoformat()
    }