from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "MES System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Local SQLite database
    SQLITE_PATH: str = "local_mes.db"
    
    # Central SQL Server database
    SQL_SERVER_HOST: str = ""
    SQL_SERVER_DATABASE: str = ""
    SQL_SERVER_USER: str = ""
    SQL_SERVER_PASSWORD: str = ""
    SQL_SERVER_DRIVER: str = "ODBC Driver 17 for SQL Server"
    SQL_SERVER_ENCRYPT: bool = False
    
    # Database sync settings
    SYNC_ENABLED: bool = True
    SYNC_INTERVAL_MINUTES: int = 20
    SYNC_BATCH_SIZE: int = 100
    
    # Redis settings
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # ERP API settings
    ERP_API_URL: str = ""
    ERP_API_KEY: str = ""
    ERP_API_TIMEOUT: int = 30
    
    # PLC settings (Modbus TCP)
    PLC_HOST: str = ""
    PLC_PORT: int = 502
    PLC_UNIT_ID: int = 1
    PLC_POLL_INTERVAL: int = 5  # seconds
    
    # Barcode scanner settings (serial)
    BARCODE_SCANNER_PORT: str = "/dev/ttyUSB0"
    BARCODE_SCANNER_BAUDRATE: int = 9600
    BARCODE_SCANNER_TIMEOUT: float = 1.0
    
    # RFID reader settings (TCP)
    RFID_READER_HOST: str = ""
    RFID_READER_PORT: int = 10001
    RFID_READER_TIMEOUT: int = 5
    
    # Security settings
    SECRET_KEY: str = "change_this_to_a_secure_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "mes.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()