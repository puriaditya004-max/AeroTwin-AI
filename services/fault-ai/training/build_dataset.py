"""
Gate 02: Dataset Builder for M4 Fault AI

Generates synthetic 30-second rolling window missions for five scenario families:
- NONE
- OVERHEATING
- OIL_PRESSURE_DEGRADATION
- VIBRATION_MISFIRE
- SENSOR_FAULT

Enforces GroupShuffleSplit (70% train, 15% val, 15% test) by missionId to prevent leakage.
"""

from datetime import datetime, timedelta, timezone
import json
import os
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit


FAULT_CLASSES = [
    "NONE",
    "OVERHEATING",
    "OIL_PRESSURE_DEGRADATION",
    "VIBRATION_MISFIRE",
    "SENSOR_FAULT"
]


def generate_single_mission(
    mission_id: str,
    scenario_family: str,
    num_samples: int = 120,
    seed: int = 42
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """Generates time-series telemetry data for a 2-minute (120 samples @ 1Hz) mission."""
    np.random.seed(seed)
    base_time = datetime.now(timezone.utc) - timedelta(minutes=10)

    t = np.arange(num_samples)
    load = 50.0 + 10.0 * np.sin(t / 20.0) + np.random.normal(0, 1.0, num_samples)
    rpm = 2000.0 + 20.0 * load + np.random.normal(0, 5.0, num_samples)

    temp_margin = 35.0 - (load - 50.0) * 0.2 + np.random.normal(0, 0.5, num_samples)
    pressure_margin = 80.0 - (load - 50.0) * 0.1 + np.random.normal(0, 1.0, num_samples)
    vibration_margin = 15.0 - np.random.normal(0, 0.2, num_samples)

    rolling_std_vib = 0.2 + np.random.uniform(0, 0.1, num_samples)
    roc_oil_temp = 0.05 + np.random.normal(0, 0.02, num_samples)

    label = "NONE"
    fault_onset_sample = None

    if scenario_family == "OVERHEATING":
        onset = np.random.randint(30, 60)
        fault_onset_sample = onset
        ramp = np.maximum(0, t - onset)
        temp_margin -= ramp * 0.8
        roc_oil_temp += (ramp > 0) * (1.5 + np.random.normal(0, 0.1, num_samples))
        label = "OVERHEATING"

    elif scenario_family == "OIL_PRESSURE_DEGRADATION":
        onset = np.random.randint(30, 60)
        fault_onset_sample = onset
        ramp = np.maximum(0, t - onset)
        pressure_margin -= ramp * 1.5
        label = "OIL_PRESSURE_DEGRADATION"

    elif scenario_family == "VIBRATION_MISFIRE":
        onset = np.random.randint(30, 60)
        fault_onset_sample = onset
        vibration_margin[onset:] -= np.random.uniform(8.0, 12.0, num_samples - onset)
        rolling_std_vib[onset:] += np.random.uniform(2.5, 4.0, num_samples - onset)
        label = "VIBRATION_MISFIRE"

    elif scenario_family == "SENSOR_FAULT":
        onset = np.random.randint(30, 60)
        fault_onset_sample = onset
        # Inject random extreme spikes or zeroes
        vibration_margin[onset:] = np.random.choice([-10.0, 99.0], size=num_samples - onset)
        temp_margin[onset:] = np.random.choice([-40.0, 150.0], size=num_samples - onset)
        label = "SENSOR_FAULT"

    data = {
        "missionId": mission_id,
        "engineId": f"ENG-{hash(mission_id) % 1000:03d}",
        "sample_index": t,
        "timestamp": [base_time + timedelta(seconds=int(i)) for i in t],
        "load": load,
        "rollingMeanRpm": rpm,
        "tempMarginC": temp_margin,
        "pressureMarginKpa": pressure_margin,
        "vibrationMarginMmS": vibration_margin,
        "rollingStdVibration": rolling_std_vib,
        "rateOfChangeOilTempCPerMin": roc_oil_temp,
        "syncLagMs": np.random.uniform(10.0, 50.0, num_samples),
        "label": label,
        "is_fault": [0 if (fault_onset_sample is None or i < fault_onset_sample) else 1 for i in t]
    }

    df = pd.DataFrame(data)
    manifest = {
        "missionId": mission_id,
        "scenario_family": scenario_family,
        "fault_onset_sample": fault_onset_sample,
        "total_samples": num_samples
    }
    return df, manifest


def build_dataset(
    output_dir: str = "artifacts/v1",
    num_missions_per_family: int = 10,
    seed: int = 42
) -> Dict[str, Any]:
    """Generates a complete dataset with 70/15/15 GroupShuffleSplit across missionIds."""
    os.makedirs(output_dir, exist_ok=True)
    all_dfs = []
    manifests = []

    mission_idx = 0
    for family in FAULT_CLASSES:
        for i in range(num_missions_per_family):
            mission_id = f"MIS-{family[:3]}-{mission_idx:03d}"
            df, manifest = generate_single_mission(mission_id, family, seed=seed + mission_idx)
            all_dfs.append(df)
            manifests.append(manifest)
            mission_idx += 1

    full_df = pd.concat(all_dfs, ignore_index=True)

    # GroupShuffleSplit (Train 70%, Val 15%, Test 15%)
    gss1 = GroupShuffleSplit(n_splits=1, train_size=0.70, random_state=seed)
    train_idx, temp_idx = next(gss1.split(full_df, groups=full_df["missionId"]))

    train_df = full_df.iloc[train_idx].copy()
    temp_df = full_df.iloc[temp_idx].copy()

    gss2 = GroupShuffleSplit(n_splits=1, train_size=0.50, random_state=seed)
    val_sub_idx, test_sub_idx = next(gss2.split(temp_df, groups=temp_df["missionId"]))

    val_df = temp_df.iloc[val_sub_idx].copy()
    test_df = temp_df.iloc[test_sub_idx].copy()

    train_df.to_parquet(os.path.join(output_dir, "train_dataset.parquet"), index=False)
    val_df.to_parquet(os.path.join(output_dir, "val_dataset.parquet"), index=False)
    test_df.to_parquet(os.path.join(output_dir, "test_dataset.parquet"), index=False)

    manifest_path = os.path.join(output_dir, "test_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifests, f, indent=2)

    summary = {
        "total_records": len(full_df),
        "num_missions": len(manifests),
        "train_records": len(train_df),
        "val_records": len(val_df),
        "test_records": len(test_df),
        "output_dir": output_dir
    }
    return summary


if __name__ == "__main__":
    result = build_dataset()
    print("Dataset build complete:", json.dumps(result, indent=2))
