from celery import Celery
from pydantic_settings import BaseSettings
from datetime import datetime, timedelta
import traceback
from typing import List, Dict, Any

class CelerySettings(BaseSettings):
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    class Config:
        env_file = ".env"
    
    @property
    def broker_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

settings = CelerySettings()

celery_app = Celery(
    "mes",
    broker=settings.broker_url,
    backend=settings.broker_url,
    include=["app.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    worker_max_tasks_per_child=100,
    beat_schedule={
        'sync-databases-every-20-minutes': {
            'task': 'app.tasks.sync_databases',
            'schedule': timedelta(minutes=20),
            'args': (),
        },
        'cleanup-old-data-daily': {
            'task': 'app.tasks.cleanup_old_data',
            'schedule': timedelta(days=1),
            'args': (30,),  # Keep 30 days of data
        },
    },
)

@celery_app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")

@celery_app.task
def process_sensor_data(sensor_data: dict):
    """Process incoming sensor data and store in database."""
    # This is a placeholder; actual implementation will be added later
    from .database import SessionLocal
    from .models import SensorData
    db = SessionLocal()
    try:
        sensor = SensorData(
            machine_id=sensor_data["machine_id"],
            sensor_type=sensor_data["sensor_type"],
            value=sensor_data["value"],
            unit=sensor_data.get("unit"),
            metadata=sensor_data.get("metadata"),
        )
        db.add(sensor)
        db.commit()
        db.refresh(sensor)
        return {"id": sensor.id, "status": "processed"}
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()

@celery_app.task
def update_machine_status(machine_id: int, status: str):
    """Update machine status in database."""
    from .database import SessionLocal
    from .models import Machine, MachineStatus
    db = SessionLocal()
    try:
        machine = db.query(Machine).filter(Machine.id == machine_id).first()
        if machine:
            machine.status = MachineStatus(status)
            db.commit()
            return {"machine_id": machine_id, "status": status}
        else:
            return {"error": "Machine not found"}
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()

@celery_app.task
def log_machine_event(machine_id: int, log_type: str, message: str, details: dict = None, user_id: int = None):
    """Log machine event."""
    from .database import SessionLocal
    from .models import MachineLog
    db = SessionLocal()
    try:
        log = MachineLog(
            machine_id=machine_id,
            user_id=user_id,
            log_type=log_type,
            message=message,
            details=details,
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return {"log_id": log.id}
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task
def sync_databases():
    """Synchronize local SQLite database with central SQL Server database."""
    from .database import get_local_db, get_central_db
    from .models import (
        User, Machine, WorkOrder, SensorData, MachineLog, WorkOrderEvent, RFIDTag,
        WrpBeamLoading, WrpWarp, WrpUnload, ErpPlan
    )
    
    # Get database sessions
    local_db = next(get_local_db())
    central_db = None
    
    try:
        # Try to get central DB session
        central_db = next(get_central_db())
    except Exception as e:
        print(f"Central database not available: {e}")
        return {"status": "skipped", "reason": "central_db_unavailable"}
    
    try:
        # List of tables to sync (in order of dependencies)
        tables = [
            (User, "users"),
            (Machine, "machines"),
            (WorkOrder, "work_orders"),
            (SensorData, "sensor_data"),
            (MachineLog, "machine_logs"),
            (WorkOrderEvent, "work_order_events"),
            (RFIDTag, "rfid_tags"),
            (ErpPlan, "erp_plans"),
            (WrpBeamLoading, "wrp_beam_loading"),
            (WrpWarp, "wrp_warp"),
            (WrpUnload, "wrp_unload"),
        ]
        
        sync_results = {}
        
        for model, table_name in tables:
            try:
                # Get all records from local database
                local_records = local_db.query(model).all()
                
                for record in local_records:
                    # Check if record exists in central database
                    central_record = central_db.query(model).filter(model.id == record.id).first()
                    
                    if central_record:
                        # Update existing record
                        for attr in model.__table__.columns.keys():
                            if attr != 'id' and hasattr(record, attr):
                                setattr(central_record, attr, getattr(record, attr))
                    else:
                        # Create new record
                        record_data = {attr: getattr(record, attr) for attr in model.__table__.columns.keys()}
                        new_record = model(**record_data)
                        central_db.add(new_record)
                
                # Commit after each table to minimize transaction size
                central_db.commit()
                sync_results[table_name] = {"status": "synced", "count": len(local_records)}
                
            except Exception as e:
                central_db.rollback()
                sync_results[table_name] = {"status": "failed", "error": str(e)}
                # Continue with other tables even if one fails
        
        return {"status": "completed", "results": sync_results, "timestamp": datetime.utcnow().isoformat()}
    
    except Exception as e:
        if central_db:
            central_db.rollback()
        return {"status": "failed", "error": str(e), "traceback": traceback.format_exc()}
    
    finally:
        if central_db:
            central_db.close()
        local_db.close()


@celery_app.task
def cleanup_old_data(days_to_keep: int = 30):
    """Clean up old data from local database to prevent excessive growth."""
    from .database import get_local_db
    from .models import SensorData, MachineLog, WorkOrderEvent
    from datetime import datetime, timedelta
    
    local_db = next(get_local_db())
    cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
    
    try:
        # Clean old sensor data
        deleted_sensor = local_db.query(SensorData).filter(SensorData.timestamp < cutoff_date).delete()
        
        # Clean old machine logs (keep only error logs longer)
        deleted_logs = local_db.query(MachineLog).filter(
            MachineLog.timestamp < cutoff_date,
            MachineLog.log_type != 'error'
        ).delete()
        
        # Clean old work order events for completed orders
        deleted_events = local_db.query(WorkOrderEvent).filter(
            WorkOrderEvent.timestamp < cutoff_date
        ).delete()
        
        local_db.commit()
        
        return {
            "status": "completed",
            "deleted_sensor_records": deleted_sensor,
            "deleted_machine_logs": deleted_logs,
            "deleted_work_order_events": deleted_events,
            "cutoff_date": cutoff_date.isoformat(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        local_db.rollback()
        return {"status": "failed", "error": str(e)}
    
    finally:
        local_db.close()


@celery_app.task
def sync_transaction_to_central_db(model_name: str, record_id: int, action: str = "create", data: dict = None):
    """Sync a single transaction to central database immediately."""
    from .database import get_local_db, get_central_db
    from .models import (
        User, Machine, WorkOrder, SensorData, MachineLog, WorkOrderEvent, RFIDTag,
        WrpBeamLoading, WrpWarp, WrpUnload, ErpPlan
    )
    
    # Map model names to actual model classes
    model_map = {
        "User": User,
        "Machine": Machine,
        "WorkOrder": WorkOrder,
        "SensorData": SensorData,
        "MachineLog": MachineLog,
        "WorkOrderEvent": WorkOrderEvent,
        "RFIDTag": RFIDTag,
        "WrpBeamLoading": WrpBeamLoading,
        "WrpWarp": WrpWarp,
        "WrpUnload": WrpUnload,
        "ErpPlan": ErpPlan,
    }
    
    if model_name not in model_map:
        return {"status": "failed", "error": f"Unknown model: {model_name}"}
    
    model = model_map[model_name]
    
    local_db = next(get_local_db())
    central_db = None
    
    try:
        central_db = next(get_central_db())
    except Exception as e:
        print(f"Central database not available, queueing for later sync: {e}")
        # Here you would add to a queue for later retry
        return {"status": "queued", "reason": "central_db_unavailable", "data": data}
    
    try:
        if action == "create":
            # Get record from local database
            record = local_db.query(model).filter(model.id == record_id).first()
            if record:
                # Create in central database
                record_data = {attr: getattr(record, attr) for attr in model.__table__.columns.keys()}
                new_record = model(**record_data)
                central_db.add(new_record)
                central_db.commit()
                return {"status": "synced", "action": "create", "model": model_name, "id": record_id}
        
        elif action == "update":
            # Get record from local database
            record = local_db.query(model).filter(model.id == record_id).first()
            if record:
                # Update in central database
                central_record = central_db.query(model).filter(model.id == record_id).first()
                if central_record:
                    for attr in model.__table__.columns.keys():
                        if attr != 'id' and hasattr(record, attr):
                            setattr(central_record, attr, getattr(record, attr))
                    central_db.commit()
                    return {"status": "synced", "action": "update", "model": model_name, "id": record_id}
        
        elif action == "delete":
            # Delete from central database
            central_record = central_db.query(model).filter(model.id == record_id).first()
            if central_record:
                central_db.delete(central_record)
                central_db.commit()
                return {"status": "synced", "action": "delete", "model": model_name, "id": record_id}
        
        return {"status": "skipped", "reason": "record_not_found"}
    
    except Exception as e:
        if central_db:
            central_db.rollback()
        print(f"Error syncing transaction: {e}")
        # Queue for retry
        return {"status": "queued", "reason": "sync_error", "error": str(e), "data": data}
    
    finally:
        if central_db:
            central_db.close()
        local_db.close()