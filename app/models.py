from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    Enum,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from .base import Base


class UserRole(enum.Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    SUPERVISOR = "supervisor"
    MAINTENANCE = "maintenance"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(100))
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.OPERATOR)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    work_orders = relationship("WorkOrder", back_populates="assigned_operator")
    machine_logs = relationship("MachineLog", back_populates="user")


class MachineStatus(enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class Machine(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text)
    machine_type = Column(String(50))
    location = Column(String(100))
    status = Column(Enum(MachineStatus), default=MachineStatus.IDLE)
    ip_address = Column(String(45))  # IPv6 compatible
    last_seen = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    work_orders = relationship("WorkOrder", back_populates="machine")
    sensor_data = relationship("SensorData", back_populates="machine")
    logs = relationship("MachineLog", back_populates="machine")


class WorkOrderStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, index=True, nullable=False)
    product_name = Column(String(200), nullable=False)
    quantity = Column(Integer, nullable=False)
    quantity_completed = Column(Integer, default=0)
    due_date = Column(DateTime(timezone=True))
    status = Column(Enum(WorkOrderStatus), default=WorkOrderStatus.PENDING)
    priority = Column(Integer, default=1)  # 1=low, 5=high
    machine_id = Column(Integer, ForeignKey("machines.id"))
    assigned_operator_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    notes = Column(Text)

    # Relationships
    machine = relationship("Machine", back_populates="work_orders")
    assigned_operator = relationship("User", back_populates="work_orders")
    events = relationship("WorkOrderEvent", back_populates="work_order")


class SensorData(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False)
    sensor_type = Column(String(50), nullable=False)  # e.g., temperature, pressure
    value = Column(Float, nullable=False)
    unit = Column(String(20))
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    metadata = Column(JSON)  # additional sensor-specific data

    # Relationships
    machine = relationship("Machine", back_populates="sensor_data")


class MachineLog(Base):
    __tablename__ = "machine_logs"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    log_type = Column(String(50))  # info, warning, error, maintenance
    message = Column(Text, nullable=False)
    details = Column(JSON)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    machine = relationship("Machine", back_populates="logs")
    user = relationship("User", back_populates="machine_logs")


class WorkOrderEvent(Base):
    __tablename__ = "work_order_events"

    id = Column(Integer, primary_key=True, index=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id"), nullable=False)
    event_type = Column(String(50))  # start, pause, complete, scrap, etc.
    description = Column(Text)
    quantity_change = Column(Integer, default=0)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    metadata = Column(JSON)

    # Relationships
    work_order = relationship("WorkOrder", back_populates="events")


class RFIDTag(Base):
    __tablename__ = "rfid_tags"

    id = Column(Integer, primary_key=True, index=True)
    tag_id = Column(String(100), unique=True, index=True, nullable=False)
    assigned_to = Column(String(100))  # operator name, machine name, etc.
    last_seen = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# WRP Module Models

class WrpBeamLoadingStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class WrpBeamLoading(Base):
    __tablename__ = "wrp_beam_loading"

    id = Column(Integer, primary_key=True, index=True)
    machine_code = Column(String(50), nullable=False, index=True)
    beam_code = Column(String(100), unique=True, index=True, nullable=False)
    plan_id = Column(String(100))  # ERP plan ID
    yarn_code = Column(String(100))
    beam_size = Column(String(50))
    number_of_ends = Column(Integer)
    schedule_start_time = Column(DateTime(timezone=True))
    schedule_end_time = Column(DateTime(timezone=True))
    empty_beam_weight = Column(Float)  # from master data
    actual_empty_beam_weight = Column(Float)  # editable by user
    measured_beam_weight = Column(Float)  # from load cells via PLC
    operator_id = Column(Integer, ForeignKey("users.id"))
    machine_id = Column(Integer, ForeignKey("machines.id"))
    status = Column(Enum(WrpBeamLoadingStatus), default=WrpBeamLoadingStatus.PENDING)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    notes = Column(Text)
    metadata = Column(JSON)  # additional data

    # Relationships
    operator = relationship("User")
    machine = relationship("Machine")


class WrpWarpStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class WrpWarp(Base):
    __tablename__ = "wrp_warp"

    id = Column(Integer, primary_key=True, index=True)
    beam_loading_id = Column(Integer, ForeignKey("wrp_beam_loading.id"), nullable=False)
    warp_speed = Column(Float)  # meters per minute
    tension = Column(Float)  # Newtons
    length_warped = Column(Float)  # meters
    target_length = Column(Float)  # meters
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    operator_id = Column(Integer, ForeignKey("users.id"))
    machine_id = Column(Integer, ForeignKey("machines.id"))
    status = Column(Enum(WrpWarpStatus), default=WrpWarpStatus.PENDING)
    quality_check = Column(Boolean, default=False)
    defects = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    metadata = Column(JSON)

    # Relationships
    beam_loading = relationship("WrpBeamLoading")
    operator = relationship("User")
    machine = relationship("Machine")


class WrpUnloadStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class WrpUnload(Base):
    __tablename__ = "wrp_unload"

    id = Column(Integer, primary_key=True, index=True)
    warp_id = Column(Integer, ForeignKey("wrp_warp.id"), nullable=False)
    final_beam_weight = Column(Float)  # total weight after warping
    unload_time = Column(DateTime(timezone=True))
    operator_id = Column(Integer, ForeignKey("users.id"))
    machine_id = Column(Integer, ForeignKey("machines.id"))
    status = Column(Enum(WrpUnloadStatus), default=WrpUnloadStatus.PENDING)
    quality_inspection = Column(Text)
    packaging_details = Column(Text)
    next_process = Column(String(100))  # e.g., "LOOM", "RANGE"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    metadata = Column(JSON)

    # Relationships
    warp = relationship("WrpWarp")
    operator = relationship("User")
    machine = relationship("Machine")


class ErpPlan(Base):
    __tablename__ = "erp_plans"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(String(100), unique=True, index=True, nullable=False)
    machine_code = Column(String(50), nullable=False, index=True)
    yarn_code = Column(String(100))
    beam_size = Column(String(50))
    number_of_ends = Column(Integer)
    schedule_start_time = Column(DateTime(timezone=True))
    schedule_end_time = Column(DateTime(timezone=True))
    priority = Column(Integer, default=1)
    status = Column(String(50), default="pending")
    erp_data = Column(JSON)  # full ERP response
    last_sync = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())