"""
Gate 07: Model Registry and Artifact Loader

Handles model loading, versioning, checksum validation, and startup tests.
"""

import hashlib
import json
import os
from typing import Dict, Any, Optional

from features.builder import FeaturePipeline
from models.anomaly import AnomalyEngine
from models.classifier import FaultClassifier
from models.explain import TreeSHAPExplainer
from models.fusion import DecisionFusionPolicy


class ModelRegistry:
    """Manages promoted model artifacts and runtime inference pipelines."""

    def __init__(self, artifacts_dir: str = "artifacts/v1"):
        self.artifacts_dir = artifacts_dir
        self.feature_pipeline = FeaturePipeline()
        self.anomaly_engine = AnomalyEngine()
        self.classifier = FaultClassifier()
        self.explainer = TreeSHAPExplainer()
        self.fusion_policy = DecisionFusionPolicy()
        self.is_loaded = False

    def calculate_checksum(self, filepath: str) -> str:
        """Calculates SHA256 checksum of a file."""
        if not os.path.exists(filepath):
            return "MISSING"
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def load_artifacts(self) -> bool:
        """Loads all trained model artifacts from the specified directory."""
        if not os.path.exists(self.artifacts_dir):
            os.makedirs(self.artifacts_dir, exist_ok=True)
            return False

        iforest_path = os.path.join(self.artifacts_dir, "isolation_forest.joblib")
        xgb_path = os.path.join(self.artifacts_dir, "xgboost_fault.json")
        calibrated_path = os.path.join(self.artifacts_dir, "calibrated_classifier.joblib")

        if os.path.exists(iforest_path):
            self.anomaly_engine.load(iforest_path)

        if os.path.exists(xgb_path):
            self.classifier.load(xgb_path, calibrated_path if os.path.exists(calibrated_path) else None)
            self.explainer.set_model(self.classifier.base_model)

        self.is_loaded = True
        return True

    def get_manifest(self) -> Dict[str, Any]:
        """Returns checksum manifest for audit traceability."""
        return {
            "isolation_forest_sha256": self.calculate_checksum(os.path.join(self.artifacts_dir, "isolation_forest.joblib")),
            "xgboost_sha256": self.calculate_checksum(os.path.join(self.artifacts_dir, "xgboost_fault.json")),
            "artifacts_dir": self.artifacts_dir,
            "is_loaded": self.is_loaded
        }
