from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class WeatherSnapshot:
    location_name: str
    latitude: float
    longitude: float
    temperature_c: float
    humidity_pct: float
    pressure_hpa: float
    dew_point_c: float
    wind_speed_kmh: float
    wind_direction_deg: float
    precipitation_mm: float
    cape_j_kg: float
    timestamp: datetime = datetime.utcnow()

@dataclass
class PredictionRecord:
    location_name: str
    predicted_at: datetime
    probability_pct: Optional[float]
    risk_level: Optional[str]
    model_available: bool
