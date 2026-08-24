"""
Gate 08: Unit Tests for Full Pipeline (Features, Anomaly, XGBoost, Fusion, SHAP)
"""

from datetime import datetime, timezone
import numpy as np
import pytest

from app.contracts import TwinState, Margins, DerivedFeatures, StateQuality, FaultType
from features.builder import FeaturePipeline
from models.anomaly import AnomalyEngine
from models.classifier import FaultClassifier
from models.fusion import DecisionFusionPolicy
from models.explain import TreeSHAPExplainer


def make_dummy_state(quality: StateQuality = StateQuality.GOOD) -> TwinState:
    return TwinState(
        engineId="ENG-TEST",
        missionId="MIS-TEST",
        correlationId="CORR-TEST",
        stateTime=datetime.now(timezone.utc),
        producerVersion="1.0.0",
        load=80.0,
        margins=Margins(tempMarginC=5.0, pressureMarginKpa=10.0, vibrationMarginMmS=1.0),
        derivedFeatures=DerivedFeatures(
            rollingMeanRpm=2500.0,
            rollingStdVibration=0.2,
            rateOfChangeOilTempCPerMin=1.2,
            sampleWindowSeconds=30.0
        ),
        stateQuality=quality,
        syncLagMs=25.0
    )


def test_feature_pipeline():
    pipeline = FeaturePipeline()
    state = make_dummy_state()
    vec = pipeline.extract_from_window([state])
    assert vec.shape[0] == 16
    assert vec[0] == 80.0  # load


def test_anomaly_engine_unfitted():
    engine = AnomalyEngine()
    X = np.zeros((1, 16))
    score = engine.predict_anomaly_score(X)
    assert score[0] == 0.0


def test_decision_fusion_stale_fallback():
    policy = DecisionFusionPolicy()
    stale_state = make_dummy_state(quality=StateQuality.STALE)
    prediction = policy.fuse(
        latest_state=stale_state,
        anomaly_score=0.9,
        predicted_type=FaultType.OVERHEATING,
        confidence=0.99,
        contributors=[]
    )
    assert prediction.faultType == FaultType.NONE
    assert prediction.confidence == 0.0
