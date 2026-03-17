from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic_settings import BaseSettings
import os
from pathlib import Path

class DatabaseSettings(BaseSettings):
    # Local SQLite configuration
    SQLITE_PATH: str = "local_mes.db"
    
    # Central SQL Server configuration
    SQL_SERVER_HOST: str = ""
    SQL_SERVER_DATABASE: str = ""
    SQL_SERVER_USER: str = ""
    SQL_SERVER_PASSWORD: str = ""
    SQL_SERVER_DRIVER: str = "ODBC Driver 17 for SQL Server"
    SQL_SERVER_ENCRYPT: bool = False
    
    # Sync settings
    SYNC_ENABLED: bool = True
    SYNC_INTERVAL_MINUTES: int = 20
    
    class Config:
        env_file = ".env"

settings = DatabaseSettings()

# Determine SQLite file path (in project root)
sqlite_path = Path(settings.SQLITE_PATH)
if not sqlite_path.is_absolute():
    sqlite_path = Path(__file__).parent.parent / sqlite_path

# Ensure directory exists
sqlite_path.parent.mkdir(parents=True, exist_ok=True)

# Local SQLite engine for touch panel
local_engine = create_engine(
    f"sqlite:///{sqlite_path}",
    connect_args={"check_same_thread": False},
    echo=False,
)

# Central SQL Server engine (if configured)
central_engine = None
if (settings.SQL_SERVER_HOST and settings.SQL_SERVER_DATABASE and 
    settings.SQL_SERVER_USER and settings.SQL_SERVER_PASSWORD):
    try:
        connection_string = (
            f"DRIVER={{{settings.SQL_SERVER_DRIVER}}};"
            f"SERVER={settings.SQL_SERVER_HOST};"
            f"DATABASE={settings.SQL_SERVER_DATABASE};"
            f"UID={settings.SQL_SERVER_USER};"
            f"PWD={settings.SQL_SERVER_PASSWORD};"
            f"Encrypt={'yes' if settings.SQL_SERVER_ENCRYPT else 'no'};"
            "TrustServerCertificate=yes;"
        )
        central_engine = create_engine(
            f"mssql+pyodbc:///?odbc_connect={connection_string}",
            pool_pre_ping=True,
            pool_recycle=300,
        )
    except Exception as e:
        print(f"Warning: Could not create SQL Server engine: {e}")
        central_engine = None

LocalSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=local_engine)
CentralSessionLocal = None
if central_engine:
    CentralSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=central_engine)

Base = declarative_base()

def get_local_db():
    """Get local SQLite database session for regular operations."""
    db = LocalSessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_central_db():
    """Get central SQL Server database session for sync operations."""
    if not CentralSessionLocal:
        raise RuntimeError("Central SQL Server not configured")
    db = CentralSessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_local_db():
    """Initialize local SQLite database tables."""
    from . import models  # noqa
    Base.metadata.create_all(bind=local_engine)

def init_central_db():
    """Initialize central SQL Server database tables (if engine exists)."""
    if central_engine:
        from . import models  # noqa
        Base.metadata.create_all(bind=central_engine)

# For backward compatibility, default to local DB
get_db = get_local_db
engine = local_engine
SessionLocal = LocalSessionLocal

def init_db():
    """Initialize databases (local only by default)."""
    init_local_db()