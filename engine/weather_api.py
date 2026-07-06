import requests
import streamlit as st
from datetime import datetime
from engine.models import WeatherSnapshot
from typing import Optional, Tuple

class WeatherDataProvider:
    BASE_URL = "https://api.open-meteo.com/v1/forecast"
    
    @staticmethod
    @st.cache_data(ttl=600)  # Cache de 10 minutos
    def get_snapshot(lat: float, lon: float, location_name: Optional[str] = None) -> WeatherSnapshot:
        """Obtiene datos meteorológicos actuales desde Open-Meteo"""
        
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                       "precipitation,weather_code,wind_speed_10m,wind_direction_10m",
            "hourly": "cape",
            "timezone": "auto",
            "forecast_days": 1
        }
        
        try:
            response = requests.get(WeatherDataProvider.BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            current = data.get("current", {})
            hourly = data.get("hourly", {})
            
            # Tomamos el CAPE más cercano al momento actual (primer valor significativo)
            cape_values = hourly.get("cape", [0.0])
            cape = next((v for v in cape_values if v > 0), cape_values[0] if cape_values else 0.0)
            
            # Nombre de ubicación (fallback)
            if not location_name:
                location_name = f"Lat {lat:.2f}, Lon {lon:.2f}"
            
            return WeatherSnapshot(
                location_name=location_name,
                latitude=lat,
                longitude=lon,
                temperature_c=current.get("temperature_2m", 0.0),
                humidity_pct=current.get("relative_humidity_2m", 0.0),
                pressure_hpa=1013.0,  # Open-Meteo no lo da directamente en current (aproximación)
                dew_point_c=current.get("apparent_temperature", current.get("temperature_2m", 0.0)) - 5.0,  # Aproximación simple
                wind_speed_kmh=current.get("wind_speed_10m", 0.0),
                wind_direction_deg=current.get("wind_direction_10m", 0.0),
                precipitation_mm=current.get("precipitation", 0.0),
                cape_j_kg=float(cape),
                timestamp=datetime.fromisoformat(current.get("time", datetime.utcnow().isoformat()))
            )
            
        except Exception as e:
            st.error(f"Error al obtener datos meteorológicos: {str(e)}")
            # Retornar datos dummy en caso de error
            return WeatherSnapshot(
                location_name=location_name or "Ubicación Desconocida",
                latitude=lat,
                longitude=lon,
                temperature_c=20.0,
                humidity_pct=65.0,
                pressure_hpa=1013.0,
                dew_point_c=15.0,
                wind_speed_kmh=15.0,
                wind_direction_deg=180.0,
                precipitation_mm=0.0,
                cape_j_kg=500.0,
                timestamp=datetime.utcnow()
            )
