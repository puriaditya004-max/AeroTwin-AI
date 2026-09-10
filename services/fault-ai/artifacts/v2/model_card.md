# M4 integrated synthetic calibration v2

This model is for the local synthetic demonstration, not real-engine or operational validation.

Training uses actual M1 scenario frames processed through M2 and the runtime M4 rolling feature pipeline. Oil and coolant sensor temperatures extend the original 16 features to 18; measured sensors are required. Quality failures remain a separate suppression policy.

Seeds 100–107 train the classifier, 200–202 calibrate probabilities, and 300–302 evaluate held-out missions. Scenario templates and threshold-derived labels are shared across splits, so perfect synthetic scores do not imply generalization to unseen fault physics or real engines. No sensor-fault classifier claim is made.

See metrics.json for scores, split_manifest.json for mission assignments, and source_hashes.json for reproducibility. Run scripts/calibrate-m4.py to generate a candidate. The legacy v1 model remains available for compatibility; Compose explicitly selects v2.
