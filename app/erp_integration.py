"""
ERP Integration Module for MES System.
Provides API client for communicating with ERP system.
"""
import httpx
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseSettings, HttpUrl
import asyncio

logger = logging.getLogger(__name__)


class ERPSettings(BaseSettings):
    """ERP API configuration settings."""
    ERP_API_URL: HttpUrl = "https://api.example.com/erp"  # type: ignore
    ERP_API_KEY: str = ""
    ERP_API_TIMEOUT: int = 30
    ERP_API_RETRY_ATTEMPTS: int = 3
    ERP_API_RETRY_DELAY: float = 1.0
    
    class Config:
        env_file = ".env"


class ERPClient:
    """Client for communicating with ERP system."""
    
    def __init__(self):
        self.settings = ERPSettings()
        self.client = None
        self.base_url = str(self.settings.ERP_API_URL)
        
    async def __aenter__(self):
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
        
    async def connect(self):
        """Create HTTP client connection."""
        headers = {
            "Authorization": f"Bearer {self.settings.ERP_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=self.settings.ERP_API_TIMEOUT,
            follow_redirects=True
        )
        
    async def close(self):
        """Close HTTP client connection."""
        if self.client:
            await self.client.aclose()
            
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make HTTP request with retry logic."""
        if not self.client:
            await self.connect()
            
        for attempt in range(self.settings.ERP_API_RETRY_ATTEMPTS):
            try:
                response = await self.client.request(method, endpoint, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"ERP API HTTP error: {e.response.status_code} - {e.response.text}")
                if e.response.status_code >= 500:
                    # Server error, retry
                    if attempt < self.settings.ERP_API_RETRY_ATTEMPTS - 1:
                        await asyncio.sleep(self.settings.ERP_API_RETRY_DELAY * (attempt + 1))
                        continue
                # Client error or final attempt
                return None
            except (httpx.RequestError, json.JSONDecodeError) as e:
                logger.error(f"ERP API request error: {e}")
                if attempt < self.settings.ERP_API_RETRY_ATTEMPTS - 1:
                    await asyncio.sleep(self.settings.ERP_API_RETRY_DELAY * (attempt + 1))
                    continue
                return None
                
        return None
        
    async def get_plans_for_machine(self, machine_code: str) -> List[Dict[str, Any]]:
        """
        Retrieve production plans for a specific machine.
        
        Args:
            machine_code: Machine identifier code
            
        Returns:
            List of production plans
        """
        endpoint = f"/api/v1/plans/machine/{machine_code}"
        data = await self._make_request("GET", endpoint)
        
        if data and "plans" in data:
            return data["plans"]
            
        # Return mock data for demonstration
        return self._get_mock_plans(machine_code)
        
    async def get_plan_details(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific production plan.
        
        Args:
            plan_id: Plan identifier
            
        Returns:
            Plan details dictionary
        """
        endpoint = f"/api/v1/plans/{plan_id}"
        data = await self._make_request("GET", endpoint)
        
        if data:
            return data
            
        # Return mock data for demonstration
        return self._get_mock_plan_details(plan_id)
        
    async def update_plan_status(self, plan_id: str, status: str, 
                                 completed_quantity: int = 0) -> bool:
        """
        Update production plan status in ERP.
        
        Args:
            plan_id: Plan identifier
            status: New status (e.g., "in_progress", "completed")
            completed_quantity: Quantity completed
            
        Returns:
            True if update successful
        """
        endpoint = f"/api/v1/plans/{plan_id}/status"
        payload = {
            "status": status,
            "completed_quantity": completed_quantity,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        data = await self._make_request("PUT", endpoint, json=payload)
        return data is not None
        
    async def get_material_info(self, material_code: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a material/yarn.
        
        Args:
            material_code: Material/Yarn code
            
        Returns:
            Material information dictionary
        """
        endpoint = f"/api/v1/materials/{material_code}"
        data = await self._make_request("GET", endpoint)
        
        if data:
            return data
            
        # Return mock data for demonstration
        return self._get_mock_material_info(material_code)
        
    async def create_production_report(self, report_data: Dict[str, Any]) -> Optional[str]:
        """
        Create production report in ERP.
        
        Args:
            report_data: Production report data
            
        Returns:
            Report ID if created successfully
        """
        endpoint = "/api/v1/production-reports"
        data = await self._make_request("POST", endpoint, json=report_data)
        
        if data and "report_id" in data:
            return data["report_id"]
            
        return None
        
    def _get_mock_plans(self, machine_code: str) -> List[Dict[str, Any]]:
        """Return mock production plans for demonstration."""
        return [
            {
                "id": "PLAN-001",
                "machine_code": machine_code,
                "yarn_code": "YC-001",
                "beam_size": '30"',
                "num_ends": 1200,
                "scheduled_start": "2024-01-15T08:00:00",
                "scheduled_end": "2024-01-15T16:00:00",
                "priority": "high",
                "status": "pending"
            },
            {
                "id": "PLAN-002",
                "machine_code": machine_code,
                "yarn_code": "YC-002",
                "beam_size": '32"',
                "num_ends": 1400,
                "scheduled_start": "2024-01-15T16:00:00",
                "scheduled_end": "2024-01-16T00:00:00",
                "priority": "medium",
                "status": "pending"
            },
            {
                "id": "PLAN-003",
                "machine_code": machine_code,
                "yarn_code": "YC-003",
                "beam_size": '28"',
                "num_ends": 1000,
                "scheduled_start": "2024-01-16T08:00:00",
                "scheduled_end": "2024-01-16T16:00:00",
                "priority": "low",
                "status": "pending"
            }
        ]
        
    def _get_mock_plan_details(self, plan_id: str) -> Dict[str, Any]:
        """Return mock plan details for demonstration."""
        return {
            "id": plan_id,
            "yarn_code": "YC-001",
            "yarn_description": "Polyester Elastic Yarn",
            "beam_size": '30"',
            "num_ends": 1200,
            "total_length_m": 5000,
            "warp_speed_m_min": 120,
            "scheduled_start": "2024-01-15T08:00:00",
            "scheduled_end": "2024-01-15T16:00:00",
            "operator_id": "OP-001",
            "supervisor": "SUP-001",
            "quality_requirements": {
                "tension_variation": "≤5%",
                "density_variation": "≤3%",
                "yarn_breakage": "≤2 breaks/1000m"
            }
        }
        
    def _get_mock_material_info(self, material_code: str) -> Dict[str, Any]:
        """Return mock material information for demonstration."""
        return {
            "code": material_code,
            "description": f"Elastic Yarn {material_code}",
            "type": "polyester",
            "denier": 150,
            "color": "white",
            "supplier": "Supplier A",
            "batch_number": f"BATCH-{material_code[-3:]}",
            "empty_beam_weight_kg": 45.5,
            "standard_density": 2.5,
            "safety_stock": 1000,
            "current_stock": 2500
        }


# Async context manager helper
async def get_erp_client() -> ERPClient:
    """Get ERP client as async context manager."""
    client = ERPClient()
    await client.connect()
    return client