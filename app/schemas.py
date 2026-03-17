from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    SUPERVISOR = "supervisor"
    MAINTENANCE = "maintenance"


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None
    role: UserRole = UserRole.OPERATOR
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class User(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MachineStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class MachineBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    machine_type: Optional[str] = None
    location: Optional[str] = None
    status: MachineStatus = MachineStatus.IDLE
    ip_address: Optional[str] = None


class MachineCreate(MachineBase):
    pass


class MachineUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    machine_type: Optional[str] = None
    location: Optional[str] = None
    status: Optional[MachineStatus] = None
    ip_address: Optional[str] = None
    last_seen: Optional[datetime] = None


class Machine(MachineBase):
    id: int
    last_seen: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class WorkOrderStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class WorkOrderBase(BaseModel):
    order_number: str = Field(..., min_length=1, max_length=50)
    product_name: str = Field(..., min_length=1, max_length=200)
    quantity: int = Field(..., gt=0)
    due_date: Optional[datetime] = None
    status: WorkOrderStatus = WorkOrderStatus.PENDING
    priority: int = Field(1, ge=1, le=5)
    machine_id: Optional[int] = None
    assigned_operator_id: Optional[int] = None
    notes: Optional[str] = None


class WorkOrderCreate(WorkOrderBase):
    pass


class WorkOrderUpdate(BaseModel):
    product_name: Optional[str] = Field(None, min_length=1, max_length=200)
    quantity: Optional[int] = Field(None, gt=0)
    quantity_completed: Optional[int] = Field(None, ge=0)
    due_date: Optional[datetime] = None
    status: Optional[WorkOrderStatus] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    machine_id: Optional[int] = None
    assigned_operator_id: Optional[int] = None
    notes: Optional[str] = None


class WorkOrder(WorkOrderBase):
    id: int
    quantity_completed: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    machine: Optional[Machine] = None
    assigned_operator: Optional[User] = None

    class Config:
        from_attributes = True


class SensorDataBase(BaseModel):
    machine_id: int
    sensor_type: str = Field(..., min_length=1, max_length=50)
    value: float
    unit: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SensorDataCreate(SensorDataBase):
    pass


class SensorData(SensorDataBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


class MachineLogBase(BaseModel):
    machine_id: int
    user_id: Optional[int] = None
    log_type: str = Field(..., min_length=1, max_length=50)
    message: str = Field(..., min_length=1)
    details: Optional[Dict[str, Any]] = None


class MachineLogCreate(MachineLogBase):
    pass


class MachineLog(MachineLogBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


class WorkOrderEventBase(BaseModel):
    work_order_id: int
    event_type: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    quantity_change: int = 0
    metadata: Optional[Dict[str, Any]] = None


class WorkOrderEventCreate(WorkOrderEventBase):
    pass


class WorkOrderEvent(WorkOrderEventBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


class RFIDTagBase(BaseModel):
    tag_id: str = Field(..., min_length=1, max_length=100)
    assigned_to: Optional[str] = None


class RFIDTagCreate(RFIDTagBase):
    pass


class RFIDTagUpdate(BaseModel):
    assigned_to: Optional[str] = None
    last_seen: Optional[datetime] = None


class RFIDTag(RFIDTagBase):
    id: int
    last_seen: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[UserRole] = None


class HealthCheck(BaseModel):
    status: str
    database: bool
    redis: bool
    timestamp: datetime


# WRP Module Schemas

class WrpBeamLoadingStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class WrpBeamLoadingBase(BaseModel):
    machine_code: str = Field(..., min_length=1, max_length=50)
    beam_code: str = Field(..., min_length=1, max_length=100)
    plan_id: Optional[str] = None
    yarn_code: Optional[str] = None
    beam_size: Optional[str] = None
    number_of_ends: Optional[int] = None
    schedule_start_time: Optional[datetime] = None
    schedule_end_time: Optional[datetime] = None
    empty_beam_weight: Optional[float] = None
    actual_empty_beam_weight: Optional[float] = None
    measured_beam_weight: Optional[float] = None
    operator_id: Optional[int] = None
    machine_id: Optional[int] = None
    status: WrpBeamLoadingStatus = WrpBeamLoadingStatus.PENDING
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class WrpBeamLoadingCreate(WrpBeamLoadingBase):
    pass


class WrpBeamLoadingUpdate(BaseModel):
    plan_id: Optional[str] = None
    yarn_code: Optional[str] = None
    beam_size: Optional[str] = None
    number_of_ends: Optional[int] = None
    schedule_start_time: Optional[datetime] = None
    schedule_end_time: Optional[datetime] = None
    empty_beam_weight: Optional[float] = None
    actual_empty_beam_weight: Optional[float] = None
    measured_beam_weight: Optional[float] = None
    operator_id: Optional[int] = None
    status: Optional[WrpBeamLoadingStatus] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class WrpBeamLoading(WrpBeamLoadingBase):
    id: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    operator: Optional[User] = None
    machine: Optional[Machine] = None

    class Config:
        from_attributes = True


class WrpWarpStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class WrpWarpBase(BaseModel):
    beam_loading_id: int
    warp_speed: Optional[float] = None
    tension: Optional[float] = None
    length_warped: Optional[float] = None
    target_length: Optional[float] = None
    operator_id: Optional[int] = None
    machine_id: Optional[int] = None
    status: WrpWarpStatus = WrpWarpStatus.PENDING
    quality_check: bool = False
    defects: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class WrpWarpCreate(WrpWarpBase):
    pass


class WrpWarpUpdate(BaseModel):
    warp_speed: Optional[float] = None
    tension: Optional[float] = None
    length_warped: Optional[float] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    operator_id: Optional[int] = None
    status: Optional[WrpWarpStatus] = None
    quality_check: Optional[bool] = None
    defects: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class WrpWarp(WrpWarpBase):
    id: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    beam_loading: Optional[WrpBeamLoading] = None
    operator: Optional[User] = None
    machine: Optional[Machine] = None

    class Config:
        from_attributes = True


class WrpUnloadStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class WrpUnloadBase(BaseModel):
    warp_id: int
    final_beam_weight: Optional[float] = None
    operator_id: Optional[int] = None
    machine_id: Optional[int] = None
    status: WrpUnloadStatus = WrpUnloadStatus.PENDING
    quality_inspection: Optional[str] = None
    packaging_details: Optional[str] = None
    next_process: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class WrpUnloadCreate(WrpUnloadBase):
    pass


class WrpUnloadUpdate(BaseModel):
    final_beam_weight: Optional[float] = None
    unload_time: Optional[datetime] = None
    operator_id: Optional[int] = None
    status: Optional[WrpUnloadStatus] = None
    quality_inspection: Optional[str] = None
    packaging_details: Optional[str] = None
    next_process: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class WrpUnload(WrpUnloadBase):
    id: int
    unload_time: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    warp: Optional[WrpWarp] = None
    operator: Optional[User] = None
    machine: Optional[Machine] = None

    class Config:
        from_attributes = True


class ErpPlanBase(BaseModel):
    plan_id: str = Field(..., min_length=1, max_length=100)
    machine_code: str = Field(..., min_length=1, max_length=50)
    yarn_code: Optional[str] = None
    beam_size: Optional[str] = None
    number_of_ends: Optional[int] = None
    schedule_start_time: Optional[datetime] = None
    schedule_end_time: Optional[datetime] = None
    priority: int = Field(1, ge=1, le=5)
    status: str = "pending"
    erp_data: Optional[Dict[str, Any]] = None


class ErpPlanCreate(ErpPlanBase):
    pass


class ErpPlanUpdate(BaseModel):
    yarn_code: Optional[str] = None
    beam_size: Optional[str] = None
    number_of_ends: Optional[int] = None
    schedule_start_time: Optional[datetime] = None
    schedule_end_time: Optional[datetime] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    status: Optional[str] = None
    erp_data: Optional[Dict[str, Any]] = None
    last_sync: Optional[datetime] = None


class ErpPlan(ErpPlanBase):
    id: int
    last_sync: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True