"""
Gate 07: Model Registry and Artifact Loader

Handles model loading, checksum validation, artifact metadata, and strict readiness checking.
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from features.builder import FeaturePipeline
from models.anomaly import AnomalyEngine
from models.classifier import FaultClassifier
from models.explain import TreeSHAPExplainer
from models.fusion import DecisionFusionPolicy


class ModelRegistry:
    """Manages promoted model artifacts, checksums, and runtime pipelines."""

    def __init__(self, artifacts_dir: str = "artifacts/v1"):
        self.artifacts_dir = os.getenv("M4_ARTIFACTS_DIR", artifacts_dir)
        self.feature_pipeline = FeaturePipeline()
        self.anomaly_engine = AnomalyEngine()
        self.classifier = FaultClassifier()
        self.explainer = TreeSHAPExplainer()
        self.fusion_policy = DecisionFusionPolicy()
        self.is_loaded = False
        self.missing_artifacts: list[str] = []
        self.load_error: str | None = None
        self.loaded_at: str | None = None

    def calculate_checksum(self, filepath: str) -> str:
        """Calculates SHA256 checksum of an artifact file."""
        if not os.path.exists(filepath):
            return "MISSING"
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def load_artifacts(self) -> bool:
        """
        Loads all required model artifacts from disk.
        Returns True and sets is_loaded=True ONLY if required artifacts exist and load cleanly.
        """
        self.missing_artifacts = []
        self.load_error = None

        if not os.path.exists(self.artifacts_dir):
            self.missing_artifacts = ["artifacts_dir"]
            self.is_loaded = False
            self.loaded_at = None
            return False

        iforest_path = os.path.join(self.artifacts_dir, "isolation_forest.joblib")
        xgb_json_path = os.path.join(self.artifacts_dir, "xgboost_fault.json")
        xgb_joblib_path = os.path.join(self.artifacts_dir, "xgboost_fault.joblib")
        calibrated_path = os.path.join(self.artifacts_dir, "calibrated_classifier.joblib")

        has_iforest = os.path.exists(iforest_path)
        has_classifier = os.path.exists(xgb_json_path) or os.path.exists(xgb_joblib_path)

        if not has_iforest:
            self.missing_artifacts.append("isolation_forest.joblib")
        if not has_classifier:
            self.missing_artifacts.append("xgboost_fault.json or xgboost_fault.joblib")

        if self.missing_artifacts:
            self.is_loaded = False
            return False

        try:
            self.anomaly_engine.load(iforest_path)
            self.classifier.load(
                xgb_json_path,
                calibrated_path if os.path.exists(calibrated_path) else None
            )
            if hasattr(self.classifier.base_model, "predict_proba"):
                self.explainer.set_model(self.classifier.base_model)

            self.is_loaded = True
            self.loaded_at = datetime.now(timezone.utc).isoformat()
            return True
        except Exception as exc:
            self.load_error = str(exc)
            self.is_loaded = False
            self.loaded_at = None
            return False

    def get_manifest(self) -> Dict[str, Any]:
        """Returns checksum manifest and readiness status for audit traceability."""
        iforest_path = os.path.join(self.artifacts_dir, "isolation_forest.joblib")
        xgb_path = os.path.join(self.artifacts_dir, "xgboost_fault.json")
        calibrated_path = os.path.join(self.artifacts_dir, "calibrated_classifier.joblib")
        metrics_path = os.path.join(self.artifacts_dir, "metrics.json")
        model_card_path = os.path.join(self.artifacts_dir, "model_card.md")

        return {
            "is_loaded": self.is_loaded,
            "artifacts_dir": self.artifacts_dir,
            "loaded_at": self.loaded_at,
            "missing_artifacts": self.missing_artifacts,
            "load_error": self.load_error,
            "isolation_forest_sha256": self.calculate_checksum(iforest_path),
            "xgboost_classifier_sha256": self.calculate_checksum(xgb_path),
            "calibrated_classifier_sha256": self.calculate_checksum(calibrated_path),
            "metrics_json_sha256": self.calculate_checksum(metrics_path),
            "model_card_sha256": self.calculate_checksum(model_card_path),
            "feature_count": len(self.feature_pipeline.feature_names),
            "feature_names": self.feature_pipeline.feature_names,
        }
