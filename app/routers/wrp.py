from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import requests
import json

from ..database import get_local_db, get_central_db
from ..models import (
    WrpBeamLoading, WrpBeamLoadingStatus,
    WrpWarp, WrpWarpStatus,
    WrpUnload, WrpUnloadStatus,
    ErpPlan, Machine, User
)
from ..schemas import (
    WrpBeamLoadingCreate, WrpBeamLoadingUpdate, WrpBeamLoading as WrpBeamLoadingSchema,
    WrpWarpCreate, WrpWarpUpdate, WrpWarp as WrpWarpSchema,
    WrpUnloadCreate, WrpUnloadUpdate, WrpUnload as WrpUnloadSchema,
    ErpPlanCreate, ErpPlanUpdate, ErpPlan as ErpPlanSchema
)
from ..tasks import log_machine_event
from .. import tasks

router = APIRouter(
    prefix="/wrp",
    tags=["wrp"],
)


# ERP Plan Management
@router.get("/plans", response_model=List[ErpPlanSchema])
def get_erp_plans(
    machine_code: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_local_db)
):
    """Get ERP plans for a machine."""
    query = db.query(ErpPlan)
    if machine_code:
        query = query.filter(ErpPlan.machine_code == machine_code)
    if status:
        query = query.filter(ErpPlan.status == status)
    
    plans = query.order_by(ErpPlan.priority.desc(), ErpPlan.schedule_start_time).offset(skip).limit(limit).all()
    return plans


@router.post("/plans/sync", status_code=status.HTTP_202_ACCEPTED)
def sync_erp_plans(
    machine_code: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_local_db)
):
    """Sync ERP plans for a machine from ERP system."""
    # This would call ERP API in background
    background_tasks.add_task(fetch_erp_plans_for_machine, machine_code, db)
    
    return {"message": "ERP plan sync started", "machine_code": machine_code}


def fetch_erp_plans_for_machine(machine_code: str, db: Session):
    """Background task to fetch plans from ERP."""
    # This is a placeholder - implement actual ERP API call
    from ..config import settings
    
    try:
        # Example ERP API call
        response = requests.get(
            f"{settings.ERP_API_URL}/plans",
            params={"machine_code": machine_code},
            headers={"Authorization": f"Bearer {settings.ERP_API_KEY}"},
            timeout=settings.ERP_API_TIMEOUT
        )
        response.raise_for_status()
        
        plans_data = response.json()
        
        for plan_data in plans_data:
            # Check if plan already exists
            existing_plan = db.query(ErpPlan).filter(
                ErpPlan.plan_id == plan_data["plan_id"]
            ).first()
            
            if existing_plan:
                # Update existing plan
                for key, value in plan_data.items():
                    if hasattr(existing_plan, key):
                        setattr(existing_plan, key, value)
                existing_plan.last_sync = datetime.utcnow()
            else:
                # Create new plan
                new_plan = ErpPlan(
                    plan_id=plan_data["plan_id"],
                    machine_code=machine_code,
                    yarn_code=plan_data.get("yarn_code"),
                    beam_size=plan_data.get("beam_size"),
                    number_of_ends=plan_data.get("number_of_ends"),
                    schedule_start_time=datetime.fromisoformat(plan_data.get("schedule_start_time")) if plan_data.get("schedule_start_time") else None,
                    schedule_end_time=datetime.fromisoformat(plan_data.get("schedule_end_time")) if plan_data.get("schedule_end_time") else None,
                    priority=plan_data.get("priority", 1),
                    status=plan_data.get("status", "pending"),
                    erp_data=plan_data,
                    last_sync=datetime.utcnow()
                )
                db.add(new_plan)
        
        db.commit()
        
    except Exception as e:
        # Log error but don't fail the task
        print(f"Error syncing ERP plans for machine {machine_code}: {e}")
        db.rollback()


# Beam Loading Management
@router.post("/beam-loading", response_model=WrpBeamLoadingSchema, status_code=status.HTTP_201_CREATED)
def create_beam_loading(
    beam_loading: WrpBeamLoadingCreate,
    db: Session = Depends(get_local_db)
):
    """Create a new beam loading record."""
    # Check if beam code already exists
    existing = db.query(WrpBeamLoading).filter(
        WrpBeamLoading.beam_code == beam_loading.beam_code
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Beam with this code already exists"
        )
    
    # Validate machine exists
    if beam_loading.machine_id:
        machine = db.query(Machine).filter(Machine.id == beam_loading.machine_id).first()
        if not machine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Machine not found"
            )
    
    # Validate operator exists
    if beam_loading.operator_id:
        operator = db.query(User).filter(User.id == beam_loading.operator_id).first()
        if not operator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operator not found"
            )
    
    db_beam_loading = WrpBeamLoading(**beam_loading.dict())
    db.add(db_beam_loading)
    db.commit()
    db.refresh(db_beam_loading)
    
    # Log event
    log_machine_event.delay(
        machine_id=beam_loading.machine_id,
        log_type="info",
        message=f"Beam loading started for beam {beam_loading.beam_code}",
        details={"beam_loading_id": db_beam_loading.id, "machine_code": beam_loading.machine_code}
    )
    
    return db_beam_loading


@router.get("/beam-loading", response_model=List[WrpBeamLoadingSchema])
def get_beam_loadings(
    machine_code: Optional[str] = None,
    status: Optional[WrpBeamLoadingStatus] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_local_db)
):
    """Get beam loading records."""
    query = db.query(WrpBeamLoading)
    if machine_code:
        query = query.filter(WrpBeamLoading.machine_code == machine_code)
    if status:
        query = query.filter(WrpBeamLoading.status == status)
    
    beam_loadings = query.order_by(WrpBeamLoading.created_at.desc()).offset(skip).limit(limit).all()
    return beam_loadings


@router.get("/beam-loading/{beam_loading_id}", response_model=WrpBeamLoadingSchema)
def get_beam_loading(beam_loading_id: int, db: Session = Depends(get_local_db)):
    """Get a specific beam loading record."""
    beam_loading = db.query(WrpBeamLoading).filter(WrpBeamLoading.id == beam_loading_id).first()
    if not beam_loading:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beam loading record not found"
        )
    return beam_loading


@router.put("/beam-loading/{beam_loading_id}", response_model=WrpBeamLoadingSchema)
def update_beam_loading(
    beam_loading_id: int,
    beam_loading_update: WrpBeamLoadingUpdate,
    db: Session = Depends(get_local_db)
):
    """Update a beam loading record."""
    beam_loading = db.query(WrpBeamLoading).filter(WrpBeamLoading.id == beam_loading_id).first()
    if not beam_loading:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beam loading record not found"
        )
    
    update_data = beam_loading_update.dict(exclude_unset=True)
    
    # Handle status transitions
    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == WrpBeamLoadingStatus.IN_PROGRESS and not beam_loading.started_at:
            beam_loading.started_at = datetime.utcnow()
        elif new_status == WrpBeamLoadingStatus.COMPLETED and not beam_loading.completed_at:
            beam_loading.completed_at = datetime.utcnow()
    
    for field, value in update_data.items():
        setattr(beam_loading, field, value)
    
    db.commit()
    db.refresh(beam_loading)
    
    return beam_loading


@router.post("/beam-loading/{beam_loading_id}/start-warp", response_model=WrpWarpSchema, status_code=status.HTTP_201_CREATED)
def start_warp_from_beam_loading(
    beam_loading_id: int,
    warp_data: WrpWarpCreate,
    db: Session = Depends(get_local_db)
):
    """Start warp process from a completed beam loading."""
    beam_loading = db.query(WrpBeamLoading).filter(WrpBeamLoading.id == beam_loading_id).first()
    if not beam_loading:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beam loading record not found"
        )
    
    if beam_loading.status != WrpBeamLoadingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Beam loading must be completed before starting warp"
        )
    
    # Create warp record
    warp_dict = warp_data.dict()
    warp_dict["beam_loading_id"] = beam_loading_id
    warp_dict["start_time"] = datetime.utcnow()
    warp_dict["status"] = WrpWarpStatus.IN_PROGRESS
    
    # Use same machine and operator if not specified
    if not warp_dict.get("machine_id") and beam_loading.machine_id:
        warp_dict["machine_id"] = beam_loading.machine_id
    if not warp_dict.get("operator_id") and beam_loading.operator_id:
        warp_dict["operator_id"] = beam_loading.operator_id
    
    db_warp = WrpWarp(**warp_dict)
    db.add(db_warp)
    db.commit()
    db.refresh(db_warp)
    
    # Log event
    log_machine_event.delay(
        machine_id=warp_dict.get("machine_id") or beam_loading.machine_id,
        log_type="info",
        message=f"Warp started for beam {beam_loading.beam_code}",
        details={"beam_loading_id": beam_loading_id, "warp_id": db_warp.id}
    )
    
    return db_warp


# Warp Management
@router.get("/warp", response_model=List[WrpWarpSchema])
def get_warps(
    beam_loading_id: Optional[int] = None,
    status: Optional[WrpWarpStatus] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_local_db)
):
    """Get warp records."""
    query = db.query(WrpWarp)
    if beam_loading_id:
        query = query.filter(WrpWarp.beam_loading_id == beam_loading_id)
    if status:
        query = query.filter(WrpWarp.status == status)
    
    warps = query.order_by(WrpWarp.created_at.desc()).offset(skip).limit(limit).all()
    return warps


@router.put("/warp/{warp_id}", response_model=WrpWarpSchema)
def update_warp(
    warp_id: int,
    warp_update: WrpWarpUpdate,
    db: Session = Depends(get_local_db)
):
    """Update a warp record."""
    warp = db.query(WrpWarp).filter(WrpWarp.id == warp_id).first()
    if not warp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warp record not found"
        )
    
    update_data = warp_update.dict(exclude_unset=True)
    
    # Handle status transitions
    if "status" in update_data:
        new_status = update_data["status"]
        if new_status == WrpWarpStatus.COMPLETED and not warp.end_time:
            warp.end_time = datetime.utcnow()
    
    for field, value in update_data.items():
        setattr(warp, field, value)
    
    db.commit()
    db.refresh(warp)
    
    return warp


@router.post("/warp/{warp_id}/complete", response_model=WrpWarpSchema)
def complete_warp(
    warp_id: int,
    final_length: float,
    quality_check: bool = True,
    defects: Optional[str] = None,
    db: Session = Depends(get_local_db)
):
    """Complete a warp process."""
    warp = db.query(WrpWarp).filter(WrpWarp.id == warp_id).first()
    if not warp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warp record not found"
        )
    
    warp.length_warped = final_length
    warp.end_time = datetime.utcnow()
    warp.status = WrpWarpStatus.COMPLETED
    warp.quality_check = quality_check
    warp.defects = defects
    
    db.commit()
    db.refresh(warp)
    
    # Log event
    log_machine_event.delay(
        machine_id=warp.machine_id,
        log_type="info",
        message=f"Warp completed for beam loading {warp.beam_loading_id}",
        details={"warp_id": warp_id, "final_length": final_length, "quality_check": quality_check}
    )
    
    return warp


# Unload Management
@router.post("/warp/{warp_id}/unload", response_model=WrpUnloadSchema, status_code=status.HTTP_201_CREATED)
def create_unload(
    warp_id: int,
    unload_data: WrpUnloadCreate,
    db: Session = Depends(get_local_db)
):
    """Create unload record for a completed warp."""
    warp = db.query(WrpWarp).filter(WrpWarp.id == warp_id).first()
    if not warp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warp record not found"
        )
    
    if warp.status != WrpWarpStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Warp must be completed before unloading"
        )
    
    # Create unload record
    unload_dict = unload_data.dict()
    unload_dict["warp_id"] = warp_id
    unload_dict["unload_time"] = datetime.utcnow()
    unload_dict["status"] = WrpUnloadStatus.IN_PROGRESS
    
    # Use same machine and operator if not specified
    if not unload_dict.get("machine_id") and warp.machine_id:
        unload_dict["machine_id"] = warp.machine_id
    if not unload_dict.get("operator_id") and warp.operator_id:
        unload_dict["operator_id"] = warp.operator_id
    
    db_unload = WrpUnload(**unload_dict)
    db.add(db_unload)
    db.commit()
    db.refresh(db_unload)
    
    # Log event
    log_machine_event.delay(
        machine_id=unload_dict.get("machine_id") or warp.machine_id,
        log_type="info",
        message=f"Unload started for warp {warp_id}",
        details={"warp_id": warp_id, "unload_id": db_unload.id}
    )
    
    return db_unload


@router.put("/unload/{unload_id}/complete", response_model=WrpUnloadSchema)
def complete_unload(
    unload_id: int,
    final_beam_weight: float,
    quality_inspection: Optional[str] = None,
    packaging_details: Optional[str] = None,
    next_process: Optional[str] = None,
    db: Session = Depends(get_local_db)
):
    """Complete an unload process."""
    unload = db.query(WrpUnload).filter(WrpUnload.id == unload_id).first()
    if not unload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unload record not found"
        )
    
    unload.final_beam_weight = final_beam_weight
    unload.status = WrpUnloadStatus.COMPLETED
    unload.quality_inspection = quality_inspection
    unload.packaging_details = packaging_details
    if next_process:
        unload.next_process = next_process
    
    db.commit()
    db.refresh(unload)
    
    # Log event
    log_machine_event.delay(
        machine_id=unload.machine_id,
        log_type="info",
        message=f"Unload completed for warp {unload.warp_id}",
        details={"unload_id": unload_id, "final_weight": final_beam_weight, "next_process": next_process}
    )
    
    return unload


@router.get("/unload", response_model=List[WrpUnloadSchema])
def get_unloads(
    warp_id: Optional[int] = None,
    status: Optional[WrpUnloadStatus] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_local_db)
):
    """Get unload records."""
    query = db.query(WrpUnload)
    if warp_id:
        query = query.filter(WrpUnload.warp_id == warp_id)
    if status:
        query = query.filter(WrpUnload.status == status)
    
    unloads = query.order_by(WrpUnload.created_at.desc()).offset(skip).limit(limit).all()
    return unloads


# PLC Integration Endpoints
@router.post("/plc/beam-weight")
def receive_beam_weight_from_plc(
    machine_code: str,
    beam_code: str,
    weight: float,
    timestamp: datetime = None,
    db: Session = Depends(get_local_db)
):
    """Receive beam weight measurement from PLC."""
    if not timestamp:
        timestamp = datetime.utcnow()
    
    # Find active beam loading for this machine and beam
    beam_loading = db.query(WrpBeamLoading).filter(
        WrpBeamLoading.machine_code == machine_code,
        WrpBeamLoading.beam_code == beam_code,
        WrpBeamLoading.status.in_([WrpBeamLoadingStatus.PENDING, WrpBeamLoadingStatus.IN_PROGRESS])
    ).first()
    
    if beam_loading:
        beam_loading.measured_beam_weight = weight
        beam_loading.updated_at = timestamp
        db.commit()
        
        return {
            "status": "updated",
            "beam_loading_id": beam_loading.id,
            "beam_code": beam_code,
            "weight": weight
        }
    else:
        # Log as sensor data if no matching beam loading
        from ..models import SensorData
        sensor_data = SensorData(
            machine_id=None,  # Would need to map machine_code to machine_id
            sensor_type="beam_weight",
            value=weight,
            unit="kg",
            timestamp=timestamp,
            metadata={"machine_code": machine_code, "beam_code": beam_code}
        )
        db.add(sensor_data)
        db.commit()
        
        return {
            "status": "logged_as_sensor_data",
            "beam_code": beam_code,
            "weight": weight
        }


@router.post("/barcode/scan")
def process_barcode_scan(
    barcode_data: str,
    scan_type: str = "beam_code",  # or "machine_code", "operator_code", etc.
    machine_id: Optional[int] = None,
    db: Session = Depends(get_local_db)
):
    """Process barcode scan data."""
    # This endpoint would integrate with barcode scanner hardware
    # For now, just log the scan and return appropriate action
    
    result = {
        "barcode_data": barcode_data,
        "scan_type": scan_type,
        "timestamp": datetime.utcnow().isoformat(),
        "action": "scanned"
    }
    
    # Based on scan type, perform different actions
    if scan_type == "beam_code":
        # Look up beam in database
        beam_loading = db.query(WrpBeamLoading).filter(
            WrpBeamLoading.beam_code == barcode_data
        ).first()
        
        if beam_loading:
            result.update({
                "action": "beam_found",
                "beam_loading_id": beam_loading.id,
                "status": beam_loading.status.value,
                "machine_code": beam_loading.machine_code
            })
        else:
            result["action"] = "beam_not_found"
    
    elif scan_type == "machine_code":
        # Look up machine
        machine = db.query(Machine).filter(
            Machine.name == barcode_data
        ).first()
        
        if machine:
            result.update({
                "action": "machine_found",
                "machine_id": machine.id,
                "status": machine.status.value
            })
        else:
            result["action"] = "machine_not_found"
    
    # Log the scan
    if machine_id:
        log_machine_event.delay(
            machine_id=machine_id,
            log_type="info",
            message=f"Barcode scanned: {barcode_data} ({scan_type})",
            details=result
        )
    
    return result