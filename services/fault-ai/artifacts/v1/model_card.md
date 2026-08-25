# AeroTwin AI - M4 Fault AI Model Card

## Model Overview
- **Model Type**: Isolation Forest (Unsupervised) + Calibrated Multiclass Classifier
- **Input**: 30-second rolling window TwinState features
- **Output**: FaultType enum, confidence score (0..1), anomalyScore (0..1), and signed TreeSHAP contributors

## Performance Metrics
- **Macro-F1 Score**: 0.9929 (Target: >= 0.80)
- **Test Samples**: 1200
- **Target Gate Met**: YES

## Confusion Matrix
```
[[622   0   3   0   0]
 [  0 147   0   0   0]
 [  5   0 133   0   0]
 [  0   0   0 129   0]
 [  0   0   0   0 161]]
```
