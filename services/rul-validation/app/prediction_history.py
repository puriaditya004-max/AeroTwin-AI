# =========================================================
# M5 - Prediction History / Reliable Trend
# =========================================================

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class PredictionHistory:
    """
    Stores recent RUL predictions and calculates a reliable trend.

    In-memory storage for the M5 demonstrator.
    This is not a persistent production database.
    """

    def __init__(self, max_size: int = 20):
        if not isinstance(max_size, int):
            raise TypeError("max_size must be an integer")

        if max_size <= 0:
            raise ValueError("max_size must be greater than zero")

        self.max_size = max_size

        self._history: deque[Dict[str, Any]] = deque(
            maxlen=max_size
        )

    # -----------------------------------------------------
    # Add prediction
    # -----------------------------------------------------

    def add_prediction(
        self,
        predicted_rul: float,
        lower_bound: float,
        upper_bound: float,
        risk_level: str,
        health_status: str,
    ) -> Dict[str, Any]:

        predicted_rul = float(predicted_rul)
        lower_bound = float(lower_bound)
        upper_bound = float(upper_bound)

        # Validate predicted RUL
        if predicted_rul < 0:
            raise ValueError(
                "predicted_rul cannot be negative"
            )

        # Validate lower bound
        if lower_bound < 0:
            raise ValueError(
                "lower_bound cannot be negative"
            )

        # Validate upper bound
        if upper_bound < 0:
            raise ValueError(
                "upper_bound cannot be negative"
            )

        # Validate bounds order
        if lower_bound > upper_bound:
            raise ValueError(
                "lower_bound cannot be greater than upper_bound"
            )

        # RUL must be inside uncertainty interval
        if not (
            lower_bound
            <= predicted_rul
            <= upper_bound
        ):
            raise ValueError(
                "predicted_rul must be inside uncertainty interval"
            )

        # Validate risk level
        if not isinstance(risk_level, str):
            raise TypeError(
                "risk_level must be a string"
            )

        # Validate health status
        if not isinstance(health_status, str):
            raise TypeError(
                "health_status must be a string"
            )

        prediction = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),

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
                (upper_bound - lower_bound) / 2,
                2,
            ),

            "risk_level": risk_level,

            "health_status": health_status,
        }

        self._history.append(prediction)

        return prediction.copy()

    # -----------------------------------------------------
    # Get complete history
    # -----------------------------------------------------

    def get_history(self) -> List[Dict[str, Any]]:
        """
        Return predictions from oldest to newest.
        """

        return [
            item.copy()
            for item in self._history
        ]

    # -----------------------------------------------------
    # Latest prediction
    # -----------------------------------------------------

    def get_latest(self) -> Optional[Dict[str, Any]]:
        """
        Return the latest prediction.
        """

        if not self._history:
            return None

        return self._history[-1].copy()

    # -----------------------------------------------------
    # Previous prediction
    # -----------------------------------------------------

    def get_previous(self) -> Optional[Dict[str, Any]]:
        """
        Return the prediction immediately before latest.
        """

        if len(self._history) < 2:
            return None

        return self._history[-2].copy()

    # -----------------------------------------------------
    # History size
    # -----------------------------------------------------

    def size(self) -> int:
        """
        Return number of stored predictions.
        """

        return len(self._history)

    # -----------------------------------------------------
    # Calculate trend
    # -----------------------------------------------------

    def calculate_trend(self) -> str:
        """
        Calculate trend using latest two predictions.

        Difference > +5  -> IMPROVING
        Difference < -5  -> DEGRADING
        Otherwise         -> STABLE
        """

        if len(self._history) < 2:
            return "STABLE"

        previous_rul = self._history[-2][
            "predicted_rul"
        ]

        current_rul = self._history[-1][
            "predicted_rul"
        ]

        difference = current_rul - previous_rul

        if difference > 5:
            return "IMPROVING"

        if difference < -5:
            return "DEGRADING"

        return "STABLE"

    # -----------------------------------------------------
    # Trend details
    # -----------------------------------------------------

    def get_trend_details(self) -> Dict[str, Any]:
        """
        Return detailed trend information.
        """

        if len(self._history) < 2:

            latest = self.get_latest()

            current_rul = (
                latest["predicted_rul"]
                if latest is not None
                else None
            )

            return {
                "trend": "STABLE",
                "previous_rul": None,
                "current_rul": current_rul,
                "difference": 0,
                "history_count": self.size(),
            }

        previous_rul = self._history[-2][
            "predicted_rul"
        ]

        current_rul = self._history[-1][
            "predicted_rul"
        ]

        difference = round(
            current_rul - previous_rul,
            2,
        )

        return {
            "trend": self.calculate_trend(),
            "previous_rul": previous_rul,
            "current_rul": current_rul,
            "difference": difference,
            "history_count": self.size(),
        }

    # -----------------------------------------------------
    # Clear history
    # -----------------------------------------------------

    def clear(self) -> None:
        """
        Remove all stored predictions.
        """

        self._history.clear()