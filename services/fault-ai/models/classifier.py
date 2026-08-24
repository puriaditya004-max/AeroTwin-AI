"""
Gate 05: XGBoost Fault Classifier with Sklearn Fallback Adapter

Supervised 5-class fault classifier with probability calibration.
Uses XGBoost when available; falls back seamlessly to HistGradientBoostingClassifier.
"""

import os
from typing import Dict, List, Tuple, Optional
import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

from app.contracts import FaultType

LABEL_MAP = {
    "NONE": 0,
    "OVERHEATING": 1,
    "OIL_PRESSURE_DEGRADATION": 2,
    "VIBRATION_MISFIRE": 3,
    "SENSOR_FAULT": 4
}

INV_LABEL_MAP = {v: k for k, v in LABEL_MAP.items()}


class FaultClassifier:
    """Multiclass fault classifier model with probability calibration."""

    def __init__(self, random_state: int = 42):
        if HAS_XGBOOST:
            self.base_model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.1,
                objective="multi:softprob",
                num_class=5,
                random_state=random_state,
                eval_metric="mlogloss"
            )
        else:
            self.base_model = HistGradientBoostingClassifier(
                max_iter=100,
                max_depth=4,
                learning_rate=0.1,
                random_state=random_state
            )
        self.calibrated_model: Optional[CalibratedClassifierCV] = None
        self.is_fitted = False

    def fit(self, X_train: np.ndarray, y_train: np.ndarray, X_val: Optional[np.ndarray] = None, y_val: Optional[np.ndarray] = None):
        """Fits base model and calibrates class probabilities on validation data."""
        self.base_model.fit(X_train, y_train)

        if X_val is not None and y_val is not None:
            self.calibrated_model = CalibratedClassifierCV(
                estimator=self.base_model,
                method="sigmoid",
                cv="prefit"
            )
            self.calibrated_model.fit(X_val, y_val)
        self.is_fitted = True

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Returns calibrated probability distribution across 5 fault classes."""
        if not self.is_fitted:
            probs = np.zeros((X.shape[0], 5), dtype=np.float32)
            probs[:, 0] = 1.0
            return probs

        if self.calibrated_model is not None:
            return self.calibrated_model.predict_proba(X)
        return self.base_model.predict_proba(X)

    def predict(self, X: np.ndarray) -> Tuple[List[FaultType], np.ndarray]:
        """Returns top predicted FaultType enum and confidence score."""
        probs = self.predict_proba(X)
        top_indices = np.argmax(probs, axis=1)
        confidences = np.max(probs, axis=1)

        predicted_types = [FaultType(INV_LABEL_MAP[idx]) for idx in top_indices]
        return predicted_types, confidences

    def save(self, json_path: str, calibrated_path: str):
        if HAS_XGBOOST and hasattr(self.base_model, "save_model"):
            self.base_model.save_model(json_path)
        else:
            joblib.dump(self.base_model, json_path.replace(".json", ".joblib"))
        if self.calibrated_model is not None:
            joblib.dump(self.calibrated_model, calibrated_path)

    def load(self, json_path: str, calibrated_path: Optional[str] = None):
        joblib_path = json_path.replace(".json", ".joblib")
        if HAS_XGBOOST and os.path.exists(json_path):
            self.base_model = xgb.XGBClassifier()
            self.base_model.load_model(json_path)
        elif os.path.exists(joblib_path):
            self.base_model = joblib.load(joblib_path)

        self.is_fitted = True
        if calibrated_path and os.path.exists(calibrated_path):
            self.calibrated_model = joblib.load(calibrated_path)
