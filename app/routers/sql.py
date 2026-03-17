from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, validator
from pydantic_settings import BaseSettings
import hashlib
import secrets
from typing import List, Optional
import pyodbc

router = APIRouter(
    prefix="/sql",
    tags=["sql"],
)

class Settings(BaseSettings):
    api_key_hash: str
    allowed_servers: str = ""
    rate_limit_per_minute: int = 60
    encrypt: bool = False

    class Config:
        env_file = ".env"

settings = Settings()

api_key_header = APIKeyHeader(name="X-API-Key")

def parse_allowed_servers(raw: str) -> List[str]:
    servers = [s.strip() for s in raw.split(",") if s.strip()]
    return servers

def verify_api_key(api_key: str = Depends(api_key_header)):
    expected_hash = settings.api_key_hash
    provided_hash = hashlib.sha256(api_key.encode()).hexdigest()
    if not expected_hash:
        raise HTTPException(status_code=500, detail="API key hash not configured")
    if not secrets.compare_digest(provided_hash, expected_hash):
        raise HTTPException(status_code=403, detail="Invalid API key")

class QueryRequest(BaseModel):
    server: str
    database: str
    username: str
    password: str
    query: str

    @validator("query")
    def validate_query(cls, v: str) -> str:
        cleaned = v.strip()
        if ";" in cleaned.rstrip(";"):
            raise ValueError("Multiple SQL statements not allowed")
        return cleaned

def limit_query(original_query: str) -> str:
    query = original_query.strip()
    if query.upper().startswith("SELECT"):
        # Inject TOP 100 if not already present
        if "TOP" not in query.upper().split():
            query = query.replace("SELECT", "SELECT TOP 100", 1)
    return query

def ensure_allowed_server(server: str):
    allowed = parse_allowed_servers(settings.allowed_servers)
    if allowed and server not in allowed:
        raise HTTPException(status_code=403, detail="Server not allowed")

def create_connection(server: str, database: str, username: str, password: str):
    ensure_allowed_server(server)
    encrypt_flag = "yes" if settings.encrypt else "no"
    try:
        connection_string = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            "Connection Timeout=30;"
            f"Encrypt={encrypt_flag};"
            "TrustServerCertificate=yes;"
        )
        return pyodbc.connect(connection_string)
    except pyodbc.Error as e:
        error_details = str(e)
        raise HTTPException(status_code=500, detail=f"Database connection failed: {error_details}")

@router.post("/execute-query")
async def execute_query(request: QueryRequest, api_key: str = Depends(verify_api_key)):
    modified_query = limit_query(request.query)
    connection = None
    try:
        connection = create_connection(
            request.server,
            request.database,
            request.username,
            request.password,
        )
        cursor = connection.cursor()
        cursor.execute(modified_query)
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return {"status": "success", "data": results, "row_count": len(results)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if connection:
            connection.close()