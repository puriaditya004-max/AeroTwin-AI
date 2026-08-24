"""
Gate 03: Feature Pipeline Builder

Converts rolling 30-second TwinState windows or DataFrames into deterministic feature vectors.
"""

from typing import List, Union
import numpy as np
import pandas as pd
from app.contracts import TwinState, TwinStateWindow


FEATURE_NAMES = [
    "load",
    "tempMarginC",
    "pressureMarginKpa",
    "vibrationMarginMmS",
    "rollingMeanRpm",
    "rollingStdVibration",
    "rateOfChangeOilTempCPerMin",
    "window_mean_tempMarginC",
    "window_std_tempMarginC",
    "window_slope_tempMarginC",
    "window_mean_pressureMarginKpa",
    "window_std_pressureMarginKpa",
    "window_slope_pressureMarginKpa",
    "window_mean_vibrationMarginMmS",
    "window_std_vibrationMarginMmS",
    "syncLagMs"
]


class FeaturePipeline:
    """Deterministic feature extractor."""

    def __init__(self):
        self.feature_names = FEATURE_NAMES

    def extract_from_window(self, states: List[TwinState]) -> np.ndarray:
        """Converts a window of TwinState objects into a single 1D feature array."""
        if not states:
            raise ValueError("State window cannot be empty.")

        latest = states[-1]
        t_margins = [s.margins.tempMarginC for s in states]
        p_margins = [s.margins.pressureMarginKpa for s in states]
        v_margins = [s.margins.vibrationMarginMmS for s in states]

        t_steps = np.arange(len(states))

        slope_t = np.polyfit(t_steps, t_margins, 1)[0] if len(states) > 1 else 0.0
        slope_p = np.polyfit(t_steps, p_margins, 1)[0] if len(states) > 1 else 0.0

        vec = [
            float(latest.load),
            float(latest.margins.tempMarginC),
            float(latest.margins.pressureMarginKpa),
            float(latest.margins.vibrationMarginMmS),
            float(latest.derivedFeatures.rollingMeanRpm),
            float(latest.derivedFeatures.rollingStdVibration),
            float(latest.derivedFeatures.rateOfChangeOilTempCPerMin),
            float(np.mean(t_margins)),
            float(np.std(t_margins)),
            float(slope_t),
            float(np.mean(p_margins)),
            float(np.std(p_margins)),
            float(slope_p),
            float(np.mean(v_margins)),
            float(np.std(v_margins)),
            float(latest.syncLagMs if latest.syncLagMs is not None else 0.0)
        ]
        return np.array(vec, dtype=np.float32)

    def transform_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transforms a DataFrame containing state columns into feature matrix."""
        res_df = pd.DataFrame()
        res_df["load"] = df["load"]
        res_df["tempMarginC"] = df["tempMarginC"]
        res_df["pressureMarginKpa"] = df["pressureMarginKpa"]
        res_df["vibrationMarginMmS"] = df["vibrationMarginMmS"]
        res_df["rollingMeanRpm"] = df["rollingMeanRpm"]
        res_df["rollingStdVibration"] = df["rollingStdVibration"]
        res_df["rateOfChangeOilTempCPerMin"] = df["rateOfChangeOilTempCPerMin"]

        res_df["window_mean_tempMarginC"] = df["tempMarginC"].rolling(30, min_periods=1).mean()
        res_df["window_std_tempMarginC"] = df["tempMarginC"].rolling(30, min_periods=1).std().fillna(0)
        res_df["window_slope_tempMarginC"] = df["tempMarginC"].diff().fillna(0)

        res_df["window_mean_pressureMarginKpa"] = df["pressureMarginKpa"].rolling(30, min_periods=1).mean()
        res_df["window_std_pressureMarginKpa"] = df["pressureMarginKpa"].rolling(30, min_periods=1).std().fillna(0)
        res_df["window_slope_pressureMarginKpa"] = df["pressureMarginKpa"].diff().fillna(0)

        res_df["window_mean_vibrationMarginMmS"] = df["vibrationMarginMmS"].rolling(30, min_periods=1).mean()
        res_df["window_std_vibrationMarginMmS"] = df["vibrationMarginMmS"].rolling(30, min_periods=1).std().fillna(0)

        res_df["syncLagMs"] = df["syncLagMs"]

        return res_df[FEATURE_NAMES]
