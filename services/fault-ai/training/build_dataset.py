"""
Gate 02: Dataset Builder for M4 Fault AI

Generates synthetic 30-second rolling window missions for five scenario families:
- NONE
- OVERHEATING
- OIL_PRESSURE_DEGRADATION
- VIBRATION_MISFIRE
- SENSOR_FAULT

Enforces GroupShuffleSplit (70% train, 15% val, 15% test) by missionId to prevent leakage.
Supports CSV/JSON export natively with PyArrow/Parquet support when installed.
"""

from datetime import datetime, timedelta, timezone
import json
import math
import os
import random
from typing import Dict, List, Tuple, Any

try:
    import numpy as np
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


FAULT_CLASSES = [
    "NONE",
    "OVERHEATING",
    "OIL_PRESSURE_DEGRADATION",
    "VIBRATION_MISFIRE",
    "SENSOR_FAULT"
]


def generate_single_mission_raw(
    mission_id: str,
    scenario_family: str,
    num_samples: int = 120,
    seed: int = 42
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Generates raw time-series telemetry frames using standard Python math/random."""
    random.seed(seed)
    base_time = datetime.now(timezone.utc) - timedelta(minutes=10)

    rows = []
    fault_onset_sample = None
    if scenario_family != "NONE":
        fault_onset_sample = random.randint(30, 60)

    engine_id = f"ENG-{(hash(mission_id) & 0x7FFFFFFF) % 1000:03d}"

    for i in range(num_samples):
        timestamp = base_time + timedelta(seconds=i)
        load = 50.0 + 10.0 * math.sin(i / 20.0) + random.gauss(0, 1.0)
        rpm = 2000.0 + 20.0 * load + random.gauss(0, 5.0)

        temp_margin = 35.0 - (load - 50.0) * 0.2 + random.gauss(0, 0.5)
        pressure_margin = 80.0 - (load - 50.0) * 0.1 + random.gauss(0, 1.0)
        vibration_margin = 15.0 - random.gauss(0, 0.2)

        rolling_std_vib = 0.2 + random.uniform(0, 0.1)
        roc_oil_temp = 0.05 + random.gauss(0, 0.02)

        label = "NONE"
        is_fault = 0

        if fault_onset_sample is not None and i >= fault_onset_sample:
            is_fault = 1
            label = scenario_family
            ramp = i - fault_onset_sample
            if scenario_family == "OVERHEATING":
                temp_margin -= ramp * 0.8
                roc_oil_temp += 1.5 + random.gauss(0, 0.1)
            elif scenario_family == "OIL_PRESSURE_DEGRADATION":
                pressure_margin -= ramp * 1.5
            elif scenario_family == "VIBRATION_MISFIRE":
                vibration_margin -= random.uniform(8.0, 12.0)
                rolling_std_vib += random.uniform(2.5, 4.0)
            elif scenario_family == "SENSOR_FAULT":
                vibration_margin = random.choice([-10.0, 99.0])
                temp_margin = random.choice([-40.0, 150.0])

        rows.append({
            "missionId": mission_id,
            "engineId": engine_id,
            "sample_index": i,
            "timestamp": timestamp.isoformat(),
            "load": round(load, 3),
            "rollingMeanRpm": round(rpm, 3),
            "tempMarginC": round(temp_margin, 3),
            "pressureMarginKpa": round(pressure_margin, 3),
            "vibrationMarginMmS": round(vibration_margin, 3),
            "rollingStdVibration": round(rolling_std_vib, 3),
            "rateOfChangeOilTempCPerMin": round(roc_oil_temp, 3),
            "syncLagMs": round(random.uniform(10.0, 50.0), 3),
            "label": label,
            "is_fault": is_fault
        })

    manifest = {
        "missionId": mission_id,
        "scenario_family": scenario_family,
        "fault_onset_sample": fault_onset_sample,
        "total_samples": num_samples
    }
    return rows, manifest


def build_dataset(
    output_dir: str = "artifacts/v1",
    num_missions_per_family: int = 10,
    seed: int = 42
) -> Dict[str, Any]:
    """Generates complete dataset and splits 70/15/15 by missionId."""
    os.makedirs(output_dir, exist_ok=True)
    all_rows = []
    manifests = []

    mission_idx = 0
    for family in FAULT_CLASSES:
        for _ in range(num_missions_per_family):
            mission_id = f"MIS-{family[:3]}-{mission_idx:03d}"
            rows, manifest = generate_single_mission_raw(
                mission_id, family, num_samples=120, seed=seed + mission_idx
            )
            all_rows.extend(rows)
            manifests.append(manifest)
            mission_idx += 1

    # Split missions into Train (70%), Val (15%), Test (15%)
    all_missions = [m["missionId"] for m in manifests]
    random.seed(seed)
    random.shuffle(all_missions)

    n = len(all_missions)
    n_train = int(n * 0.70)
    n_val = int(n * 0.15)

    train_missions = set(all_missions[:n_train])
    val_missions = set(all_missions[n_train:n_train + n_val])
    test_missions = set(all_missions[n_train + n_val:])

    train_rows = [r for r in all_rows if r["missionId"] in train_missions]
    val_rows = [r for r in all_rows if r["missionId"] in val_missions]
    test_rows = [r for r in all_rows if r["missionId"] in test_missions]

    # Save JSON manifests and records
    with open(os.path.join(output_dir, "train_dataset.json"), "w") as f:
        json.dump(train_rows, f, indent=2)
    with open(os.path.join(output_dir, "val_dataset.json"), "w") as f:
        json.dump(val_rows, f, indent=2)
    with open(os.path.join(output_dir, "test_dataset.json"), "w") as f:
        json.dump(test_rows, f, indent=2)

    with open(os.path.join(output_dir, "test_manifest.json"), "w") as f:
        json.dump(manifests, f, indent=2)

    # Save Parquet files if Pandas is installed
    if HAS_PANDAS:
        try:
            pd.DataFrame(train_rows).to_parquet(os.path.join(output_dir, "train_dataset.parquet"), index=False)
            pd.DataFrame(val_rows).to_parquet(os.path.join(output_dir, "val_dataset.parquet"), index=False)
            pd.DataFrame(test_rows).to_parquet(os.path.join(output_dir, "test_dataset.parquet"), index=False)
        except Exception:
            pass

    summary = {
        "total_records": len(all_rows),
        "num_missions": len(manifests),
        "train_records": len(train_rows),
        "val_records": len(val_rows),
        "test_records": len(test_rows),
        "output_dir": output_dir
    }
    return summary


if __name__ == "__main__":
    result = build_dataset()
    print("Dataset build complete:", json.dumps(result, indent=2))
