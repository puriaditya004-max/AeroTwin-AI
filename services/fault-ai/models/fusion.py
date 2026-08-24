"""
Gate 06: Quality-Aware Decision Fusion Policy

Combines TwinState quality flags, Isolation Forest anomaly score, and XGBoost classifier probabilities.
Enforces safety rules: degraded/stale data never yields unsupported physical fault claims.
"""

from datetime import datetime, timezone
from typing import List, Optional
import numpy as np

from app.contracts import TwinState, FaultPrediction, FaultType, Contributor, StateQuality
from features.builder import FEATURE_NAMES


class DecisionFusionPolicy:
    """Quality-aware fusion policy manager."""

    def __init__(
        self,
        anomaly_threshold: float = 0.55,
        confidence_threshold: float = 0.60
    ):
        self.anomaly_threshold = anomaly_threshold
        self.confidence_threshold = confidence_threshold

    def fuse(
        self,
        latest_state: TwinState,
        anomaly_score: float,
        predicted_type: FaultType,
        confidence: float,
        contributors: List[Contributor]
    ) -> FaultPrediction:
        """
        Fuses inputs according to quality and confidence safety gates.
        """
        # Safety rule: Degraded or Stale state quality prevents physical fault claims
        if latest_state.stateQuality in (StateQuality.STALE, StateQuality.DEGRADED):
            return FaultPrediction(
                engineId=latest_state.engineId,
                missionId=latest_state.missionId,
                correlationId=latest_state.correlationId,
                predictionTime=datetime.now(timezone.utc),
                producerVersion="1.0.0",
                faultType=FaultType.NONE,
                confidence=0.0,
                anomalyScore=float(anomaly_score),
                contributors=[],
                detectionDelayMs=None
            )

        final_fault = predicted_type
        final_conf = confidence

        # Physical fault claim requires calibrated classifier confidence + supporting anomaly score
        if final_fault != FaultType.NONE:
            if final_conf < self.confidence_threshold or anomaly_score < (self.anomaly_threshold * 0.5):
                # Downgrade to NONE if confidence or supporting anomaly evidence is insufficient
                final_fault = FaultType.NONE
                final_conf = 1.0 - final_conf

        return FaultPrediction(
            engineId=latest_state.engineId,
            missionId=latest_state.missionId,
            correlationId=latest_state.correlationId,
            predictionTime=datetime.now(timezone.utc),
            producerVersion="1.0.0",
            faultType=final_fault,
            confidence=float(final_conf),
            anomalyScore=float(anomaly_score),
            contributors=contributors,
            detectionDelayMs=None
        )
