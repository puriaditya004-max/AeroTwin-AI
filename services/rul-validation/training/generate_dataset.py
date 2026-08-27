from pathlib import Path

import numpy as np
import pandas as pd


# ---------------------------------------------------------
# M5 - RUL & Model Validation
# Synthetic Degradation Dataset Generator
# ---------------------------------------------------------

RANDOM_SEED = 42
NUM_ENGINES = 50
MIN_CYCLES = 120
MAX_CYCLES = 250

OUTPUT_DIR = Path(__file__).resolve().parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "degradation_dataset.csv"


def generate_engine_data(engine_id: int, rng: np.random.Generator) -> pd.DataFrame:
    """Generate degradation data for one engine."""

    total_cycles = int(rng.integers(MIN_CYCLES, MAX_CYCLES + 1))

    rows = []

    for cycle in range(1, total_cycles + 1):

        # Progress: 0 at beginning -> 1 near failure
        progress = cycle / total_cycles

        # Health decreases as the engine degrades
        health_index = max(
            0.0,
            1.0 - progress + rng.normal(0, 0.015)
        )

        # Sensor degradation patterns
        temperature = (
            60
            + 25 * progress
            + rng.normal(0, 1.5)
        )

        vibration = (
            0.5
            + 2.0 * progress
            + rng.normal(0, 0.08)
        )

        pressure = (
            100
            - 20 * progress
            + rng.normal(0, 1.2)
        )

        rpm = (
            3000
            - 500 * progress
            + rng.normal(0, 50)
        )

        load = (
            70
            + 10 * progress
            + rng.normal(0, 2)
        )

        # Remaining Useful Life
        rul = total_cycles - cycle

        rows.append(
            {
                "engine_id": engine_id,
                "cycle": cycle,
                "temperature": round(temperature, 3),
                "vibration": round(vibration, 3),
                "pressure": round(pressure, 3),
                "rpm": round(rpm, 3),
                "load": round(load, 3),
                "health_index": round(health_index, 4),
                "rul": rul,
            }
        )

    return pd.DataFrame(rows)


def generate_dataset() -> pd.DataFrame:
    """Generate complete degradation dataset."""

    rng = np.random.default_rng(RANDOM_SEED)

    all_engines = []

    for engine_id in range(1, NUM_ENGINES + 1):
        engine_data = generate_engine_data(engine_id, rng)
        all_engines.append(engine_data)

    dataset = pd.concat(all_engines, ignore_index=True)

    return dataset


def main():
    print("=" * 60)
    print("M5 - RUL Degradation Dataset Generator")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dataset = generate_dataset()

    dataset.to_csv(OUTPUT_FILE, index=False)

    print("\nDataset generated successfully!")
    print(f"Output file: {OUTPUT_FILE}")

    print("\nDataset shape:")
    print(dataset.shape)

    print("\nColumns:")
    print(list(dataset.columns))

    print("\nFirst 5 rows:")
    print(dataset.head())

    print("\nDataset statistics:")
    print(dataset.describe())

    print("\nRUL range:")
    print(f"Minimum RUL: {dataset['rul'].min()}")
    print(f"Maximum RUL: {dataset['rul'].max()}")

    print("\nNumber of engines:")
    print(dataset["engine_id"].nunique())

    print("\n" + "=" * 60)
    print("Dataset generation completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()