import streamlit as st
from engine.weather_api import WeatherDataProvider
from engine.tornado_predictor import TornadoRiskEngine
from engine.models import PredictionRecord
from datetime import datetime
import pandas as pd

def main():
    st.set_page_config(page_title="MDT Tornado Predictor", layout="wide")
    st.title("🌪️ MDT Tornado Predictor")
    st.markdown("**Plataforma de predicción de riesgo de tornados en tiempo real**")

    predictor = TornadoRiskEngine()
    
    # --- Sidebar ---
    st.sidebar.header("📍 Ubicaciones")
    
    # Ubicaciones predefinidas
    presets = {
        "Nueva York": (40.7128, -74.0060),
        "Oklahoma City": (35.4676, -97.5164),
        "Chicago": (41.8781, -87.6298),
        "Miami": (25.7617, -80.1918),
        "Ciudad de México": (19.4326, -99.1332),
    }
    
    selected_preset = st.sidebar.selectbox("Ubicaciones predefinidas", options=list(presets.keys()))
    lat, lon = presets[selected_preset]
    
    # Inputs manuales
    lat = st.sidebar.number_input("Latitud", value=float(lat), format="%.4f")
    lon = st.sidebar.number_input("Longitud", value=float(lon), format="%.4f")
    location_name = st.sidebar.text_input("Nombre de la ubicación", selected_preset)
    
    if st.sidebar.button("🔄 Analizar Ubicación", type="primary"):
        with st.spinner("Obteniendo datos meteorológicos y generando predicción..."):
            snapshot = WeatherDataProvider.get_snapshot(lat, lon, location_name)
            
            # --- Métricas ---
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("🌡️ Temp", f"{snapshot.temperature_c:.1f}°C")
            with col2:
                st.metric("💧 Humedad", f"{snapshot.humidity_pct:.0f}%")
            with col3:
                st.metric("🌬️ Viento", f"{snapshot.wind_speed_kmh:.1f} km/h")
            with col4:
                st.metric("⚡ CAPE", f"{snapshot.cape_j_kg:.0f} J/kg")
            
            # --- Predicción ---
            prob, risk_level = predictor.predict(snapshot)
            
            st.divider()
            st.subheader("🎯 Predicción de Riesgo de Tornado")
            
            if prob is not None:
                # Gauge visual
                st.progress(prob / 100)
                st.markdown(f"### **Probabilidad: {prob}%** — **{risk_level}**")
                
                if risk_level == "CRÍTICO":
                    st.error("🚨 ¡ALERTA MÁXIMA! Condiciones muy favorables para tornados")
                elif risk_level == "ALTO":
                    st.warning("⚠️ Alto riesgo. Mantenerse alerta")
                elif risk_level == "MODERADO":
                    st.info("ℹ️ Riesgo moderado")
                else:
                    st.success("✅ Riesgo bajo")
            
            # Mapa
            st.subheader("📍 Ubicación")
            map_data = pd.DataFrame([[snapshot.latitude, snapshot.longitude]], columns=['lat', 'lon'])
            st.map(map_data, use_container_width=True)
            
            # Datos completos
            with st.expander("Ver todos los datos meteorológicos"):
                st.json(snapshot.__dict__)
    
    # --- Historial de predicciones (en memoria) ---
    if 'history' not in st.session_state:
        st.session_state.history = []
    
    if st.button("Guardar predicción actual en historial"):
        if 'snapshot' in locals() and prob is not None:
            record = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "location": location_name,
                "probability": prob,
                "risk": risk_level
            }
            st.session_state.history.append(record)
            st.success("Predicción guardada en historial")
    
    if st.session_state.history:
        st.subheader("📜 Historial de Predicciones")
        df = pd.DataFrame(st.session_state.history)
        st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()
