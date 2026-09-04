from typing import Optional
from pydantic import BaseModel, Field

class PredictionRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90, description="Latitude of the location")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude of the location")
    base_date: Optional[str] = Field(None, description="Optional base date T for prediction (YYYY-MM-DD)")

class LocationData(BaseModel):
    latitude: float
    longitude: float
    latitude_snapped: float
    longitude_snapped: float

class ForecastsData(BaseModel):
    h1: float
    h2: float
    h3: float
    h4: float
    h5: float
    h6: float
    h7: float

class PredictionResponse(BaseModel):
    status: str
    location: LocationData
    base_date_T: str
    forecasts: ForecastsData
    unit: str = "mm"

class HealthResponse(BaseModel):
    status: str
    service: str

class ReadyResponse(BaseModel):
    status: str
    latest_valid_T: Optional[str] = None
    reason: Optional[str] = None

class ErrorResponse(BaseModel):
    error: str
    message: str
