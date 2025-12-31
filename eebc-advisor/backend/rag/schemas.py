from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class BuildingContext(BaseModel):
    district: Optional[str] = None
    building_type: Optional[str] = None
    is_new_building: Optional[bool] = None
    floor_area_m2: Optional[float] = None
    electrical_demand_kva: Optional[float] = None
    cooling_capacity_kwth: Optional[float] = None
    heating_capacity_kwth: Optional[float] = None
    wwr_percent: Optional[float] = None
    skylight_percent: Optional[float] = None
    glazing_vlt: Optional[float] = None
    hvac_type: Optional[str] = None
    operating_hours: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    context: Optional[BuildingContext] = None

class Source(BaseModel):
    page: int
    chunk_id: str
    score: float
    excerpt: str

class ChatResponse(BaseModel):
    answer: str
    applies: str
    reason: str
    sources: List[Source]
