"""
Gate 07: Training Script for M4 Fault AI

Trains Isolation Forest anomaly detector and XGBoost fault classifier on train_dataset.parquet.
Calibrates probabilities on val_dataset.parquet and saves model artifacts to artifacts/v1/.
"""

import os
import joblib
import numpy as np
import pandas as pd

from features.builder import FeaturePipeline
from models.anomaly import AnomalyEngine
from models.classifier import FaultClassifier, LABEL_MAP
from training.build_dataset import build_dataset


def train_models(artifacts_dir: str = "artifacts/v1"):
    """Main training routine for M4 models."""
    os.makedirs(artifacts_dir, exist_ok=True)

    train_path = os.path.join(artifacts_dir, "train_dataset.parquet")
    val_path = os.path.join(artifacts_dir, "val_dataset.parquet")

    if not os.path.exists(train_path) or not os.path.exists(val_path):
        print("Dataset not found. Building synthetic dataset first...")
        build_dataset(output_dir=artifacts_dir)

    train_df = pd.read_parquet(train_path)
    val_df = pd.read_parquet(val_path)

    pipeline = FeaturePipeline()
    X_train = pipeline.transform_df(train_df).values
    X_val = pipeline.transform_df(val_df).values

    y_train = np.array([LABEL_MAP[lbl] for lbl in train_df["label"]])
    y_val = np.array([LABEL_MAP[lbl] for lbl in val_df["label"]])

    # 1. Train Isolation Forest on normal baseline data
    normal_mask_train = (train_df["label"] == "NONE")
    X_train_normal = X_train[normal_mask_train]

    print("Fitting Isolation Forest on normal training data...")
    anomaly_engine = AnomalyEngine()
    anomaly_engine.fit(X_train_normal)
    anomaly_engine.save(os.path.join(artifacts_dir, "isolation_forest.joblib"))

    # 2. Train XGBoost classifier & calibrate on val set
    print("Fitting XGBoost fault classifier...")
    classifier = FaultClassifier()
    classifier.fit(X_train, y_train, X_val, y_val)
    classifier.save(
        os.path.join(artifacts_dir, "xgboost_fault.json"),
        os.path.join(artifacts_dir, "calibrated_classifier.joblib")
    )

    print("Model training complete. Promoted artifacts saved to:", artifacts_dir)


if __name__ == "__main__":
    train_models()
