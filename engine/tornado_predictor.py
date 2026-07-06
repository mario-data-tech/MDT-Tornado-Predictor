import joblib
from pathlib import Path
from typing import Tuple, Optional
from engine.models import WeatherSnapshot
import numpy as np

class TornadoRiskEngine:
    def __init__(self):
        self.model = self._load_or_create_model()
    
    def _load_or_create_model(self):
        model_path = Path("model/tornado_model.pkl")
        model_path.parent.mkdir(exist_ok=True)
        
        if model_path.exists():
            try:
                return joblib.load(model_path)
            except:
                pass
        
        # Modelo Dummy (RandomForest simple) - solo para desarrollo
        from sklearn.ensemble import RandomForestClassifier
        model = RandomForestClassifier(n_estimators=50, random_state=42)
        
        # Datos de entrenamiento dummy
        X_dummy = np.array([
            [25, 80, 1500], [18, 60, 300], [32, 90, 2500],
            [15, 40, 100], [28, 85, 1800], [22, 70, 800]
        ])
        y_dummy = np.array([1, 0, 1, 0, 1, 0])  # 1 = tornado risk
        
        model.fit(X_dummy, y_dummy)
        joblib.dump(model, model_path)
        return model

    @property
    def is_available(self) -> bool:
        return self.model is not None

    def predict(self, snapshot: WeatherSnapshot) -> Tuple[Optional[float], Optional[str]]:
        if not self.is_available:
            return None, None
        
        # Features: temperature, humidity, cape
        features = [[
            snapshot.temperature_c,
            snapshot.humidity_pct,
            snapshot.cape_j_kg
        ]]
        
        prob = self.model.predict_proba(features)[0][1]
        return round(prob * 100, 2), self._map_level(prob)

    def _map_level(self, prob: float) -> str:
        if prob > 0.75: return "CRÍTICO"
        if prob > 0.45: return "ALTO"
        if prob > 0.20: return "MODERADO"
        return "BAJO"
