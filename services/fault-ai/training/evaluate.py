"""
Gate 07 / Gate 10: Model Evaluation and Card Generation

Evaluates promoted models on held-out test_dataset.parquet and outputs metrics.json and model_card.md.
"""

import json
import os
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, f1_score

from features.builder import FeaturePipeline
from models.anomaly import AnomalyEngine
from models.classifier import FaultClassifier, LABEL_MAP, INV_LABEL_MAP


def evaluate_models(artifacts_dir: str = "artifacts/v1") -> dict:
    """Evaluates promoted models on held-out test dataset."""
    test_path = os.path.join(artifacts_dir, "test_dataset.parquet")
    if not os.path.exists(test_path):
        raise FileNotFoundError(f"Test dataset not found at {test_path}")

    test_df = pd.read_parquet(test_path)
    pipeline = FeaturePipeline()
    X_test = pipeline.transform_df(test_df).values
    y_test = np.array([LABEL_MAP[lbl] for lbl in test_df["label"]])

    anomaly_engine = AnomalyEngine()
    anomaly_engine.load(os.path.join(artifacts_dir, "isolation_forest.joblib"))

    classifier = FaultClassifier()
    classifier.load(
        os.path.join(artifacts_dir, "xgboost_fault.json"),
        os.path.join(artifacts_dir, "calibrated_classifier.joblib")
    )

    preds, confs = classifier.predict(X_test)
    y_pred = [LABEL_MAP[p.value] for p in preds]

    macro_f1 = float(f1_score(y_test, y_pred, average="macro"))
    cm = confusion_matrix(y_test, y_pred).tolist()

    metrics = {
        "macro_f1": macro_f1,
        "confusion_matrix": cm,
        "class_names": list(LABEL_MAP.keys()),
        "test_samples": len(test_df),
        "target_f1_met": macro_f1 >= 0.80
    }

    with open(os.path.join(artifacts_dir, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    # Write Model Card
    card_content = f"""# AeroTwin AI - M4 Fault AI Model Card

## Model Overview
- **Model Type**: Isolation Forest (Unsupervised) + Calibrated XGBoost Multiclass Classifier
- **Input**: 30-second rolling window TwinState features
- **Output**: FaultType enum, confidence score (0..1), anomalyScore (0..1), and signed TreeSHAP contributors

## Performance Metrics
- **Macro-F1 Score**: {macro_f1:.4f} (Target: >= 0.80)
- **Test Samples**: {len(test_df)}
- **Target Gate Met**: {"YES" if macro_f1 >= 0.80 else "NO"}

## Confusion Matrix
```
{np.array(cm)}
```
"""
    with open(os.path.join(artifacts_dir, "model_card.md"), "w") as f:
        f.write(card_content)

    print("Evaluation complete. Metrics saved to:", os.path.join(artifacts_dir, "metrics.json"))
    return metrics


if __name__ == "__main__":
    evaluate_models()
