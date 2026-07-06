import streamlit as st
from engine.weather_api import WeatherDataProvider
from engine.tornado_predictor import TornadoRiskEngine

def main():
    st.set_page_config(page_title="Monitor de Tornados", layout="wide")
    st.title("🌪️ Centro de Monitoreo Meteorológico")
    
    predictor = TornadoRiskEngine()
    
    # Lógica de UI que orquesta los componentes
    # 1. Sidebar para ubicación
    # 2. Renderizado de métricas meteorológicas
    # 3. Renderizado de riesgo (solo si predictor.is_available)
    # 4. Historial y Alertas

if __name__ == "__main__":
    main()
