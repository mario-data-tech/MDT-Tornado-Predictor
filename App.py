import streamlit as st
from engine.weather_api import WeatherDataProvider
from engine.tornado_predictor import TornadoRiskEngine
from engine.models import PredictionRecord
from datetime import datetime

def main():
    st.set_page_config(page_title="Monitor de Tornados", layout="wide")
    st.title("🌪️ Centro de Monitoreo Meteorológico - MDT Tornado Predictor")
    
    predictor = TornadoRiskEngine()
    
    # Sidebar
    st.sidebar.header("📍 Ubicación")
    lat = st.sidebar.number_input("Latitud", value=40.7128, format="%.4f")
    lon = st.sidebar.number_input("Longitud", value=-74.0060, format="%.4f")
    location_name = st.sidebar.text_input("Nombre de ubicación (opcional)", "Nueva York")
    
    if st.sidebar.button("🔄 Obtener datos y predecir", type="primary"):
        with st.spinner("Obteniendo datos meteorológicos..."):
            snapshot = WeatherDataProvider.get_snapshot(lat, lon, location_name)
            
            # Mostrar datos
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🌡️ Temperatura", f"{snapshot.temperature_c}°C")
                st.metric("💧 Humedad", f"{snapshot.humidity_pct}%")
            with col2:
                st.metric("🌬️ Viento", f"{snapshot.wind_speed_kmh} km/h")
                st.metric("☔ Precipitación", f"{snapshot.precipitation_mm} mm")
            with col3:
                st.metric("⚡ CAPE", f"{snapshot.cape_j_kg} J/kg")
            
            # Predicción
            if predictor.is_available:
                prob, risk_level = predictor.predict(snapshot)
                if prob is not None:
                    st.success(f"**Probabilidad de Tornado: {prob}%**")
                    st.subheader(f"Nivel de Riesgo: **{risk_level}**")
                    
                    # Color según riesgo
                    if risk_level == "CRÍTICO":
                        st.error("⚠️ ¡ALERTA CRÍTICA! Posibilidad alta de tornados")
                    elif risk_level == "ALTO":
                        st.warning("⚠️ Riesgo alto de tornados")
                    else:
                        st.info("✅ Riesgo bajo")
            else:
                st.warning("Modelo no disponible. Usando modo demo.")

if __name__ == "__main__":
    main()
