from pathlib import Path

import joblib
import mlflow
import mlflow.pyfunc
import numpy as np

from .config import (
    FEATURE_COLUMNS,
    MAX_RUL,
    MIN_RUL,
    MLFLOW_MODEL_NAME,
    MLFLOW_MODEL_VERSION,
    MLFLOW_TRACKING_URI,
    MODEL_FILE,
    SCALER_FILE,
)


# =========================================================
# M5 - RUL Prediction Engine
# =========================================================


class RULPredictor:
    """
    RUL prediction engine.

    Loading priority:
        1. MLflow Model Registry
        2. Local joblib model

    Provides:
        - RUL prediction
        - uncertainty bounds
        - model source information
    """

    # Experimental uncertainty margin for hackathon
    # demonstrator purposes.
    UNCERTAINTY_MARGIN = 0.15

    def __init__(self):

        self.model = None
        self.scaler = None

        self.model_source = None
        self.model_error = None

        # -------------------------------------------------
        # Validate scaler
        # -------------------------------------------------

        if not SCALER_FILE.exists():
            raise FileNotFoundError(
                f"Scaler not found: {SCALER_FILE}"
            )

        self.scaler = joblib.load(SCALER_FILE)

        # -------------------------------------------------
        # Try MLflow Registry first
        # -------------------------------------------------

        try:

            mlflow.set_tracking_uri(
                MLFLOW_TRACKING_URI
            )

            model_uri = (
                f"models:/{MLFLOW_MODEL_NAME}/"
                f"{MLFLOW_MODEL_VERSION}"
            )

            self.model = mlflow.pyfunc.load_model(
                model_uri
            )

            self.model_source = (
                f"mlflow:{MLFLOW_MODEL_NAME}:"
                f"{MLFLOW_MODEL_VERSION}"
            )

            print(
                "RUL model loaded from MLflow Registry."
            )

        except Exception as exc:

            self.model_error = str(exc)

            print(
                "MLflow model loading failed."
            )

            print(
                "Reason:",
                self.model_error
            )

            # -------------------------------------------------
            # Local model fallback
            # -------------------------------------------------

            try:

                if not MODEL_FILE.exists():
                    raise FileNotFoundError(
                        f"Local model not found: {MODEL_FILE}"
                    )

                self.model = joblib.load(
                    MODEL_FILE
                )

                self.model_source = (
                    "local:rul_xgboost.joblib"
                )

                print(
                    "Fallback successful: "
                    "local model loaded."
                )

            except Exception as local_exc:

                raise RuntimeError(
                    "Unable to load RUL model from "
                    "both MLflow Registry and local "
                    f"fallback model.\n"
                    f"MLflow error: {self.model_error}\n"
                    f"Local model error: {local_exc}"
                ) from local_exc

    # =====================================================
    # Feature preparation
    # =====================================================

    def _prepare_features(
        self,
        temperature: float,
        vibration: float,
        pressure: float,
        rpm: float,
        load: float,
        health_index: float,
    ):

        features = np.array(
            [[
                temperature,
                vibration,
                pressure,
                rpm,
                load,
                health_index,
            ]],
            dtype=float,
        )

        return self.scaler.transform(features)

    # =====================================================
    # Raw RUL prediction
    # =====================================================

    def _predict_raw(self, features_scaled) -> float:

        prediction = self.model.predict(
            features_scaled
        )

        predicted_rul = float(
            np.asarray(prediction)
            .reshape(-1)[0]
        )

        return predicted_rul

    # =====================================================
    # Prediction with uncertainty
    # =====================================================

    def predict_with_uncertainty(
        self,
        temperature: float,
        vibration: float,
        pressure: float,
        rpm: float,
        load: float,
        health_index: float,
    ) -> dict:
        """
        Predict RUL with experimental uncertainty bounds.

        The uncertainty interval is currently based on a
        fixed relative margin and is intended for the
        hackathon demonstrator, not production safety use.
        """

        features_scaled = self._prepare_features(
            temperature=temperature,
            vibration=vibration,
            pressure=pressure,
            rpm=rpm,
            load=load,
            health_index=health_index,
        )

        raw_prediction = self._predict_raw(
            features_scaled
        )

        # -------------------------------------------------
        # Clamp prediction to configured RUL limits
        # -------------------------------------------------

        predicted_rul = max(
            MIN_RUL,
            min(
                MAX_RUL,
                raw_prediction,
            ),
        )

        # -------------------------------------------------
        # Calculate experimental uncertainty
        # -------------------------------------------------

        margin = (
            abs(predicted_rul)
            * self.UNCERTAINTY_MARGIN
        )

        lower_bound = max(
            MIN_RUL,
            predicted_rul - margin,
        )

        upper_bound = min(
            MAX_RUL,
            predicted_rul + margin,
        )

        return {
            "predicted_rul": round(
                predicted_rul,
                2,
            ),
            "lower_bound": round(
                lower_bound,
                2,
            ),
            "upper_bound": round(
                upper_bound,
                2,
            ),
            "uncertainty_margin": round(
                margin,
                2,
            ),
            "unit": "cycles",
        }

    # =====================================================
    # Backward-compatible prediction
    # =====================================================

    def predict(
        self,
        temperature: float,
        vibration: float,
        pressure: float,
        rpm: float,
        load: float,
        health_index: float,
    ) -> float:
        """
        Predict Remaining Useful Life in cycles.

        Kept for backward compatibility with the existing
        API and tests.
        """

        result = self.predict_with_uncertainty(
            temperature=temperature,
            vibration=vibration,
            pressure=pressure,
            rpm=rpm,
            load=load,
            health_index=health_index,
        )

        return result["predicted_rul"]