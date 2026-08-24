"""
Gate 04: Isolation Forest Anomaly Engine

Unsupervised Isolation Forest model adapter with [0..1] score normalization.
"""

from typing import Optional
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest


class AnomalyEngine:
    """Wrapper around scikit-learn IsolationForest."""

    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self.model = IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=random_state,
            n_jobs=-1
        )
        self.is_fitted = False

    def fit(self, X: np.ndarray):
        """Fit Isolation Forest on normal baseline data."""
        self.model.fit(X)
        self.is_fitted = True

    def predict_anomaly_score(self, X: np.ndarray) -> np.ndarray:
        """
        Calculates normalized anomalyScore in range [0..1].
        Higher value indicates higher likelihood of anomaly.
        """
        if not self.is_fitted:
            # Fallback for uninitialized model
            return np.zeros(X.shape[0], dtype=np.float32)

        # decision_function returns negative values for anomalies, positive for normal
        raw_scores = self.model.decision_function(X)
        # Transform raw_scores into 0..1 scale
        normalized = 1.0 - (1.0 / (1.0 + np.exp(-4.0 * raw_scores)))
        return np.clip(normalized, 0.0, 1.0).astype(np.float32)

    def save(self, filepath: str):
        joblib.dump(self.model, filepath)

    def load(self, filepath: str):
        self.model = joblib.load(filepath)
        self.is_fitted = True
