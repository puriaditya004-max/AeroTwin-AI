"""
Gate 07: Training Script for M4 Fault AI

Trains Isolation Forest anomaly detector and FaultClassifier model on train dataset.
Calibrates probabilities on validation dataset and saves model artifacts to artifacts/v1/.
"""

import json
import os
import joblib
import numpy as np

from features.builder import FeaturePipeline
from models.anomaly import AnomalyEngine
from models.classifier import FaultClassifier, LABEL_MAP
from training.build_dataset import build_dataset, HAS_PANDAS

if HAS_PANDAS:
    import pandas as pd


def load_dataset_rows(json_path: str, parquet_path: str):
    if HAS_PANDAS and os.path.exists(parquet_path):
        df = pd.read_parquet(parquet_path)
        return df.to_dict(orient="records")
    elif os.path.exists(json_path):
        with open(json_path, "r") as f:
            return json.load(f)
    else:
        raise FileNotFoundError(f"Neither {json_path} nor {parquet_path} exists.")


def train_models(artifacts_dir: str = "artifacts/v1"):
    """Main training routine for M4 models."""
    os.makedirs(artifacts_dir, exist_ok=True)

    train_json = os.path.join(artifacts_dir, "train_dataset.json")
    train_parquet = os.path.join(artifacts_dir, "train_dataset.parquet")
    val_json = os.path.join(artifacts_dir, "val_dataset.json")
    val_parquet = os.path.join(artifacts_dir, "val_dataset.parquet")

    if not os.path.exists(train_json) and not os.path.exists(train_parquet):
        print("Dataset not found. Building synthetic dataset first...")
        build_dataset(output_dir=artifacts_dir)

    train_rows = load_dataset_rows(train_json, train_parquet)
    val_rows = load_dataset_rows(val_json, val_parquet)

    pipeline = FeaturePipeline()

    if HAS_PANDAS:
        train_df = pd.DataFrame(train_rows)
        val_df = pd.DataFrame(val_rows)
        X_train = pipeline.transform_df(train_df).values
        X_val = pipeline.transform_df(val_df).values
    else:
        # Standard Python list transform fallback
        def rows_to_features(rows):
            features = []
            for r in rows:
                vec = [
                    r["load"], r["tempMarginC"], r["pressureMarginKpa"], r["vibrationMarginMmS"],
                    r["rollingMeanRpm"], r["rollingStdVibration"], r["rateOfChangeOilTempCPerMin"],
                    r["tempMarginC"], 0.0, 0.0, r["pressureMarginKpa"], 0.0, 0.0,
                    r["vibrationMarginMmS"], 0.0, r["syncLagMs"]
                ]
                features.append(vec)
            return np.array(features, dtype=np.float32)

        X_train = rows_to_features(train_rows)
        X_val = rows_to_features(val_rows)

    y_train = np.array([LABEL_MAP[r["label"]] for r in train_rows])
    y_val = np.array([LABEL_MAP[r["label"]] for r in val_rows])

    # 1. Train Isolation Forest on normal baseline data
    normal_mask_train = np.array([r["label"] == "NONE" for r in train_rows])
    X_train_normal = X_train[normal_mask_train]

    print("Fitting Isolation Forest on normal training data...")
    anomaly_engine = AnomalyEngine()
    anomaly_engine.fit(X_train_normal)
    anomaly_engine.save(os.path.join(artifacts_dir, "isolation_forest.joblib"))

    # 2. Train Fault Classifier & calibrate on val set
    print("Fitting fault classifier...")
    classifier = FaultClassifier()
    classifier.fit(X_train, y_train, X_val, y_val)
    classifier.save(
        os.path.join(artifacts_dir, "xgboost_fault.json"),
        os.path.join(artifacts_dir, "calibrated_classifier.joblib")
    )

    print("Model training complete. Promoted artifacts saved to:", artifacts_dir)


if __name__ == "__main__":
    train_models()
