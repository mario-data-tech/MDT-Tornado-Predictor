import joblib
from pathlib import Path
from typing import Tuple, Optional
from engine.models import WeatherSnapshot

MODEL_PATH = Path("model/tornado_model.pkl")

class TornadoRiskEngine:
    def __init__(self):
        self.model = self._load_model()

    def _load_model(self):
        return joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None

    @property
    def is_available(self) -> bool:
        return self.model is not None

    def predict(self, snapshot: WeatherSnapshot) -> Tuple[Optional[float], Optional[str]]:
        if not self.is_available:
            return None, None
        
        # Preparar features para el modelo
        features = [[snapshot.temperature_c, snapshot.humidity_pct, snapshot.cape_j_kg]]
        prob = self.model.predict_proba(features)[0][1]
        return round(prob * 100, 2), self._map_level(prob)

    def _map_level(self, prob: float) -> str:
        if prob > 0.8: return "CRÍTICO"
        if prob > 0.5: return "ALTO"
        return "BAJO"
