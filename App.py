"""
================================================================================
 CENTRO DE MONITOREO METEOROLÓGICO Y PREDICCIÓN DE TORNADOS
================================================================================
Punto de entrada Streamlit. Orquesta exclusivamente las siguientes capas:

    engine.weather_api        -> datos meteorológicos reales (Open-Meteo)
    engine.tornado_predictor  -> inferencia de riesgo (modelo real o N/D)
    engine.policy             -> reglas de negocio (umbrales, alertas)
    engine.database           -> persistencia (historial, alertas, auditoría)
    engine.audit              -> trazabilidad técnica
    engine.utils              -> formato de presentación

No contiene, ni reutiliza, ninguna lógica de simulación de flotas,
camiones, rutas, costos, ROI u optimización logística: fue eliminada por
completo del proyecto.

Compatible con Streamlit Cloud. Todas las credenciales (API keys, cadena
de conexión a base de datos) se leen únicamente desde
`.streamlit/secrets.toml` y nunca se escriben en el código fuente.
================================================================================
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime

import pandas as pd
import streamlit as st

from engine.audit import AuditLogger
from engine.database import (
    get_alerts,
    get_prediction_history,
    save_alert,
    save_prediction,
    save_weather_reading,
)
from engine.policy import MONITORED_LOCATIONS, RISK_COLORS, build_alert_message, should_trigger_alert
from engine.tornado_predictor import MODEL_PATH, TornadoRiskEngine, load_tornado_model
from engine.utils import degrees_to_cardinal, format_metric, format_timestamp
from engine.weather_api import WeatherAPIError, WeatherDataProvider, WeatherSnapshot, clear_cache

# ------------------------------------------------------------------------
# Logging de aplicación
# ------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("tornado_monitor.app")


# ==============================================================================
# CONFIGURACIÓN DE PÁGINA Y CONTROLES
# ==============================================================================

def configure_page() -> None:
    """Configura metadatos y layout de la página Streamlit."""
    st.set_page_config(
        page_title="Centro de Monitoreo Meteorológico - Tornados",
        page_icon="🌪️",
        layout="wide",
    )


def render_sidebar() -> tuple[str, bool]:
    """Renderiza los controles de la barra lateral. Devuelve (ubicación, refrescar_ahora)."""
    st.sidebar.header("⚙️ Configuración de Monitoreo")
    location_name = st.sidebar.selectbox(
        "Ubicación monitoreada",
        options=list(MONITORED_LOCATIONS.keys()),
        index=0,
    )
    refresh_clicked = st.sidebar.button("🔄 Actualizar datos", use_container_width=True)

    st.sidebar.divider()
    st.sidebar.markdown(
        "**Fuente meteorológica:** Open-Meteo (API pública, tiempo real)\n\n"
        "**Modelo de riesgo:** modelo de ML local (si está disponible)"
    )
    return location_name, refresh_clicked


# ==============================================================================
# SECCIONES DEL DASHBOARD
# ==============================================================================

def render_model_status(model_available: bool) -> None:
    """Muestra el estado real del modelo de IA: cargado o no entrenado."""
    st.markdown("### 🤖 Estado del modelo de IA")
    if model_available:
        st.success("✅ Modelo de predicción de tornados cargado correctamente desde `model/tornado_model.pkl`.")
    else:
        st.error(
            "⚠️ **No hay un modelo de Machine Learning entrenado disponible.** "
            f"Se esperaba encontrarlo en `{MODEL_PATH.relative_to(MODEL_PATH.parent.parent)}`. "
            "No se generan predicciones ficticias: entrená y guardá un modelo "
            "compatible (interfaz `predict_proba`) en esa ruta para habilitar "
            "la probabilidad de tornado y el nivel de riesgo."
        )


def render_risk_panel(probability: float | None, level: str | None, model_available: bool) -> None:
    """Muestra probabilidad de tornado y nivel de riesgo (sólo si hay modelo real)."""
    col1, col2 = st.columns(2)

    with col1:
        if model_available and probability is not None:
            st.metric("Probabilidad de tornado", f"{probability}%")
        else:
            st.metric("Probabilidad de tornado", "N/D")

    with col2:
        if model_available and level is not None:
            color = RISK_COLORS.get(level, "#95a5a6")
            st.markdown(
                f"<div style='padding:0.6rem;border-radius:0.5rem;background-color:{color};"
                f"color:white;text-align:center;font-weight:bold;'>Nivel de riesgo: {level}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.warning("Nivel de riesgo: no disponible")


def render_weather_metrics(snapshot: WeatherSnapshot) -> None:
    """Muestra las variables meteorológicas reales obtenidas de la API."""
    st.markdown("### 🌡️ Condiciones meteorológicas actuales")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Temperatura", format_metric(snapshot.temperature_c, "°C"))
    c2.metric("Presión atmosférica", format_metric(snapshot.pressure_hpa, "hPa"))
    c3.metric("Humedad", format_metric(snapshot.humidity_pct, "%"))
    c4.metric("Punto de rocío", format_metric(snapshot.dew_point_c, "°C"))

    c5, c6, c7 = st.columns(3)
    c5.metric("Velocidad del viento", format_metric(snapshot.wind_speed_kmh, "km/h"))
    c6.metric(
        "Dirección del viento",
        f"{degrees_to_cardinal(snapshot.wind_direction_deg)} "
        f"({format_metric(snapshot.wind_direction_deg, '°', 0)})",
    )
    c7.metric("Precipitación", format_metric(snapshot.precipitation_mm, "mm"))

    st.caption(
        "CAPE (inestabilidad atmosférica, proxy): "
        f"{format_metric(snapshot.cape_j_kg, 'J/kg', 0)}. "
        "No sustituye a un índice oficial de riesgo de tornado, que requiere "
        "además datos de wind shear y rotación de radar Doppler."
    )


def render_map(snapshot: WeatherSnapshot) -> None:
    """Muestra un mapa con la ubicación meteorológica monitoreada."""
    st.markdown("### 🗺️ Mapa meteorológico")
    map_df = pd.DataFrame({"lat": [snapshot.latitude], "lon": [snapshot.longitude]})
    st.map(map_df, zoom=6)
    st.caption(
        "Marcador: ubicación monitoreada. Para radar de precipitación y "
        "capas meteorológicas avanzadas en producción, se recomienda "
        "integrar una fuente especializada (ej. RainViewer API o NEXRAD)."
    )


def render_history(location_name: str) -> None:
    """Muestra el historial de predicciones persistidas para la ubicación."""
    st.markdown("### 📈 Historial de predicciones")
    records = get_prediction_history(location_name)
    if not records:
        st.caption("Aún no hay predicciones registradas para esta ubicación.")
        return

    df = pd.DataFrame(
        [
            {
                "Fecha (UTC)": format_timestamp(r.predicted_at),
                "Probabilidad (%)": r.probability_pct if r.probability_pct is not None else "N/D",
                "Riesgo": r.risk_level or "N/D",
                "Modelo disponible": "Sí" if r.model_available else "No",
            }
            for r in records
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_alerts(location_name: str) -> None:
    """Muestra el registro de alertas generadas según la política de riesgo."""
    st.markdown("### 🚨 Registro de alertas")
    alerts = get_alerts(location_name)
    if not alerts:
        st.caption("Sin alertas registradas para esta ubicación.")
        return

    df = pd.DataFrame(
        [
            {
                "Fecha (UTC)": format_timestamp(a.triggered_at),
                "Riesgo": a.risk_level,
                "Mensaje": a.message,
            }
            for a in alerts
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_footer(last_update: datetime) -> None:
    """Muestra la marca de última actualización y avisos legales."""
    st.divider()
    st.caption(f"🕒 Última actualización: {format_timestamp(last_update)}")
    st.caption(
        "Fuente meteorológica: Open-Meteo (https://open-meteo.com). "
        "Esta aplicación no debe utilizarse como único sistema de alerta "
        "de emergencia; para avisos oficiales consultar al Servicio "
        "Meteorológico Nacional (SMN) o autoridad competente de su región."
    )


# ==============================================================================
# PUNTO DE ENTRADA PRINCIPAL
# ==============================================================================

def main() -> None:
    """Orquesta la obtención de datos, la inferencia y el renderizado del dashboard."""
    configure_page()

    location_name, refresh_clicked = render_sidebar()
    latitude, longitude = MONITORED_LOCATIONS[location_name]

    st.title("🌪️ Centro de Monitoreo Meteorológico y Predicción de Tornados")
    st.caption(
        "Datos meteorológicos en tiempo real vía Open-Meteo. La probabilidad "
        "de tornado depende de un modelo de Machine Learning entrenado; "
        "no se generan estimaciones ficticias."
    )
    st.subheader(f"📍 Ubicación: {location_name}")

    if refresh_clicked:
        clear_cache()

    # --- Obtención de datos meteorológicos reales ---
    try:
        snapshot = WeatherDataProvider.get_snapshot(location_name, latitude, longitude)
        AuditLogger.log("weather_fetch", f"Datos obtenidos correctamente para {location_name}.", success=True)
    except WeatherAPIError as exc:
        logger.exception("No se pudo obtener el clima para %s", location_name)
        AuditLogger.log("weather_fetch", f"Fallo al obtener datos para {location_name}: {exc}", success=False)
        st.error(f"❌ No se pudieron obtener datos meteorológicos reales: {exc}")
        st.stop()
        return

    # --- Inferencia de riesgo (modelo real, o N/D si no existe) ---
    model = load_tornado_model()
    risk_engine = TornadoRiskEngine(model)
    probability, level = risk_engine.predict(snapshot)
    AuditLogger.log(
        "model_check",
        f"Modelo disponible: {risk_engine.is_available} para {location_name}.",
        success=risk_engine.is_available,
    )

    # --- Persistencia: lectura meteorológica y predicción ---
    reading_id = save_weather_reading(
        {
            "location_name": snapshot.location_name,
            "latitude": snapshot.latitude,
            "longitude": snapshot.longitude,
            "temperature_c": snapshot.temperature_c,
            "humidity_pct": snapshot.humidity_pct,
            "pressure_hpa": snapshot.pressure_hpa,
            "dew_point_c": snapshot.dew_point_c,
            "wind_speed_kmh": snapshot.wind_speed_kmh,
            "wind_direction_deg": snapshot.wind_direction_deg,
            "precipitation_mm": snapshot.precipitation_mm,
            "cape_j_kg": snapshot.cape_j_kg,
        }
    )

    prediction_id = save_prediction(
        {
            "weather_reading_id": reading_id,
            "location_name": location_name,
            "model_available": risk_engine.is_available,
            "probability_pct": probability,
            "risk_level": level,
        }
    )

    # --- Política de alertas ---
    if risk_engine.is_available and level is not None and should_trigger_alert(level):
        message = build_alert_message(location_name, probability, level)
        save_alert(
            {
                "prediction_id": prediction_id,
                "location_name": location_name,
                "risk_level": level,
                "message": message,
            }
        )
        AuditLogger.log("alert", message, success=True)

    # --- Renderizado del dashboard ---
    render_model_status(risk_engine.is_available)
    st.divider()
    render_risk_panel(probability, level, risk_engine.is_available)
    st.divider()
    render_weather_metrics(snapshot)
    st.divider()
    render_map(snapshot)
    st.divider()
    render_history(location_name)
    st.divider()
    render_alerts(location_name)
    render_footer(datetime.utcnow())


if __name__ == "__main__":
    mai
