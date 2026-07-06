import requests
import streamlit as st
from datetime import datetime

class DiscordNotifier:
    @staticmethod
    def send_alert(webhook_url: str, snapshot, probability: float, risk_level: str):
        if not webhook_url or risk_level in ["BAJO", "MODERADO"]:
            return False
        
        color = 0xFF0000 if risk_level == "CRÍTICO" else 0xFFAA00  # Rojo o Naranja
        
        embed = {
            "title": "🌪️ ¡ALERTA DE TORNADO!",
            "description": f"**{risk_level}** - Probabilidad: **{probability}%**",
            "color": color,
            "fields": [
                {"name": "📍 Ubicación", "value": snapshot.location_name, "inline": True},
                {"name": "🌡️ Temperatura", "value": f"{snapshot.temperature_c}°C", "inline": True},
                {"name": "⚡ CAPE", "value": f"{snapshot.cape_j_kg} J/kg", "inline": True},
                {"name": "💧 Humedad", "value": f"{snapshot.humidity_pct}%", "inline": True},
                {"name": "🌬️ Viento", "value": f"{snapshot.wind_speed_kmh} km/h", "inline": True},
            ],
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": "MDT Tornado Predictor"}
        }
        
        payload = {
            "content": "@everyone" if risk_level == "CRÍTICO" else "",
            "embeds": [embed]
        }
        
        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            return response.status_code == 204
        except:
            return False
