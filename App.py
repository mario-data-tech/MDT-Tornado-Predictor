import streamlit as st
import pandas as pd
from datetime import datetime
from engine.weather_api import WeatherDataProvider
from engine.tornado_predictor import TornadoRiskEngine
from engine.models import WeatherSnapshot

# Importar notifier (se crea abajo)
from engine.discord_alert import DiscordNotifier

def main():
    st.set_page_config(page_title="MDT Tornado Predictor", layout="wide")
    st.title("🌪️ MDT Tornado Predictor")
    st.markdown("**Plataforma de predicción de riesgo de tornados en tiempo real**")

    predictor = TornadoRiskEngine()
    
    # --- Sidebar ---
    st.sidebar.header("📍 Ubicaciones")
    
    presets = {
        "Nueva York": (40.7128, -74.0060),
        "Oklahoma City (Tornado Alley)": (35.4676, -97.5164),
        "Chicago": (41.8781, -87.6298),
        "Miami": (25.7617, -80.1918),
        "Ciudad de México": (19.4326, -99.1332),
        "Personalizada": (0.0, 0.0)
    }
    
    selected_preset = st.sidebar.selectbox("Seleccionar ubicación", options=list(presets.keys()))
    
    if selected_preset == "Personalizada":
        lat = st.sidebar.number_input("Latitud", value=19.4326, format="%.4f")
        lon = st.sidebar.number_input("Longitud", value=-99.1332, format="%.4f")
        location_name = st.sidebar.text_input("Nombre de la ubicación", "Mi Ubicación")
    else:
        lat, lon = presets[selected_preset]
        location_name = selected_preset

    # Discord Webhook
    webhook_url = st.secrets.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        webhook_url = st.sidebar.text_input(
            "🔗 Discord Webhook URL (opcional)", 
            type="password",
            help="Pégala aquí solo para esta sesión"
        )

    if st.sidebar.button("🔄 Analizar Ubicación", type="primary"):
        with st.spinner("Obteniendo datos y analizando riesgo..."):
            snapshot = WeatherDataProvider.get_snapshot(lat, lon, location_name)
            
            # Métricas
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("🌡️ Temperatura", f"{snapshot.temperature_c:.1f}°C")
            with col2:
                st.metric("💧 Humedad", f"{snapshot.humidity_pct:.0f}%")
            with col3:
                st.metric("🌬️ Viento", f"{snapshot.wind_speed_kmh:.1f} km/h")
            with col4:
                st.metric("⚡ CAPE", f"{int(snapshot.cape_j_kg)} J/kg")
            
            # Predicción
            prob, risk_level = predictor.predict(snapshot)
            
            st.divider()
            st.subheader("🎯 Predicción de Riesgo de Tornado")
            
            if prob is not None:
                st.progress(prob / 100)
                st.markdown(f"### **Probabilidad:** {prob}% — **{risk_level}**")
                
                if risk_level == "CRÍTICO":
                    st.error("🚨 ¡ALERTA MÁXIMA! Condiciones muy favorables para tornados")
                elif risk_level == "ALTO":
                    st.warning("⚠️ Alto riesgo de tornados")
                elif risk_level == "MODERADO":
                    st.info("ℹ️ Riesgo moderado")
                else:
                    st.success("✅ Riesgo bajo")
                
                # Enviar alerta a Discord si es ALTO o CRÍTICO
                if risk_level in ["ALTO", "CRÍTICO"] and webhook_url:
                    with st.spinner("Enviando alerta a Discord..."):
                        success = DiscordNotifier.send_alert(webhook_url, snapshot, prob, risk_level)
                        if success:
                            st.success("✅ Alerta enviada a Discord")
                        else:
                            st.warning("⚠️ No se pudo enviar la alerta")
            
            # Mapa
            st.subheader("📍 Ubicación en mapa")
            map_data = pd.DataFrame([[snapshot.latitude, snapshot.longitude]], columns=['lat', 'lon'])
            st.map(map_data, use_container_width=True)
            
            # Datos detallados
            with st.expander("Ver datos meteorológicos completos"):
                st.json({k: v for k, v in snapshot.__dict__.items() if not k.startswith('_')})

    # Historial
    if 'history' not in st.session_state:
        st.session_state.history = []
    
    if st.button("💾 Guardar esta predicción en historial"):
        if 'snapshot' in locals() and prob is not None:
            st.session_state.history.append({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "location": location_name,
                "probability": prob,
                "risk": risk_level
            })
            st.success("Predicción guardada")

    if st.session_state.history:
        st.subheader("📜 Historial de Predicciones")
        df = pd.DataFrame(st.session_state.history)
        st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()
