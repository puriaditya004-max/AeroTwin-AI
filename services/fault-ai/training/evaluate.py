"""
Gate 07 / Gate 10: Model Evaluation and Card Generation

Evaluates promoted models on held-out test_dataset and outputs metrics.json and model_card.md.
"""

import json
import os
import numpy as np
from sklearn.metrics import classification_report, confusion_matrix, f1_score

from features.builder import FeaturePipeline
from models.anomaly import AnomalyEngine
from models.classifier import FaultClassifier, LABEL_MAP, INV_LABEL_MAP
from training.build_dataset import HAS_PANDAS
from training.train import load_dataset_rows

if HAS_PANDAS:
    import pandas as pd


def evaluate_models(artifacts_dir: str = "artifacts/v1") -> dict:
    """Evaluates promoted models on held-out test dataset."""
    test_json = os.path.join(artifacts_dir, "test_dataset.json")
    test_parquet = os.path.join(artifacts_dir, "test_dataset.parquet")

    if not os.path.exists(test_json) and not os.path.exists(test_parquet):
        raise FileNotFoundError(f"Test dataset not found at {artifacts_dir}")

    test_rows = load_dataset_rows(test_json, test_parquet)
    pipeline = FeaturePipeline()

    if HAS_PANDAS:
        test_df = pd.DataFrame(test_rows)
        X_test = pipeline.transform_df(test_df).values
    else:
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

        X_test = rows_to_features(test_rows)

    y_test = np.array([LABEL_MAP[r["label"]] for r in test_rows])

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
        "test_samples": len(test_rows),
        "target_f1_met": macro_f1 >= 0.80
    }

    with open(os.path.join(artifacts_dir, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    # Write Model Card
    card_content = f"""# AeroTwin AI - M4 Fault AI Model Card

## Model Overview
- **Model Type**: Isolation Forest (Unsupervised) + Calibrated Multiclass Classifier
- **Input**: 30-second rolling window TwinState features
- **Output**: FaultType enum, confidence score (0..1), anomalyScore (0..1), and signed TreeSHAP contributors

## Performance Metrics
- **Macro-F1 Score**: {macro_f1:.4f} (Target: >= 0.80)
- **Test Samples**: {len(test_rows)}
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
