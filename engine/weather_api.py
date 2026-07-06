import requests
import streamlit as st
from engine.models import WeatherSnapshot

class WeatherDataProvider:
    @staticmethod
    @st.cache_data(ttl=600)
    def get_snapshot(lat: float, lon: float) -> WeatherSnapshot:
        # Lógica de llamada a Open-Meteo usando st.secrets["OPEN_METEO_API_KEY"]
        # Retorna instancia de WeatherSnapshot
        pass
