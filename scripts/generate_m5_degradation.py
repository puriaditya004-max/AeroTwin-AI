import os
import numpy as np
import pandas as pd


# Reproducibility
np.random.seed(42)

# Number of synthetic records
N = 5000


# -----------------------------
# UAV / Flight Parameters
# -----------------------------

uav_id = np.random.randint(1, 101, N)
mission_id = np.arange(1, N + 1)

flight_hours = np.random.uniform(10, 1000, N)

battery_cycles = np.random.randint(20, 1200, N)

temperature = np.random.normal(35, 8, N)
temperature = np.clip(temperature, 15, 60)

vibration = np.random.uniform(0.1, 2.5, N)

motor_current = np.random.normal(18, 4, N)
motor_current = np.clip(motor_current, 5, 35)

battery_voltage = np.random.normal(22.2, 1.2, N)
battery_voltage = np.clip(battery_voltage, 18, 25)

payload_kg = np.random.uniform(0.5, 5.0, N)


# -----------------------------
# Degradation Calculation
# -----------------------------

degradation_score = (
    0.30 * (battery_cycles / 1200)
    + 0.20 * (flight_hours / 1000)
    + 0.15 * ((temperature - 15) / 45)
    + 0.15 * (vibration / 2.5)
    + 0.10 * (motor_current / 35)
    + 0.10 * ((25 - battery_voltage) / 7)
)

# Add small random noise
degradation_score += np.random.normal(0, 0.03, N)

# Keep score between 0 and 1
degradation_score = np.clip(degradation_score, 0, 1)


# -----------------------------
# Remaining Useful Life (RUL)
# -----------------------------

remaining_useful_life = 1000 * (1 - degradation_score)

remaining_useful_life += np.random.normal(0, 30, N)

remaining_useful_life = np.clip(
    remaining_useful_life,
    0,
    1000
)


# -----------------------------
# Failure Risk
# -----------------------------

failure_risk = np.where(
    degradation_score >= 0.75,
    "High",
    np.where(
        degradation_score >= 0.45,
        "Medium",
        "Low"
    )
)


# -----------------------------
# Create DataFrame
# -----------------------------

df = pd.DataFrame({
    "uav_id": uav_id,
    "mission_id": mission_id,
    "flight_hours": flight_hours.round(2),
    "battery_cycles": battery_cycles,
    "temperature": temperature.round(2),
    "vibration": vibration.round(3),
    "motor_current": motor_current.round(2),
    "battery_voltage": battery_voltage.round(2),
    "payload_kg": payload_kg.round(2),
    "degradation_score": degradation_score.round(4),
    "remaining_useful_life": remaining_useful_life.round(2),
    "failure_risk": failure_risk
})


# -----------------------------
# Save Dataset
# -----------------------------

output_dir = "data/synthetic"
output_file = os.path.join(
    output_dir,
    "m5_degradation.csv"
)

os.makedirs(output_dir, exist_ok=True)

df.to_csv(output_file, index=False)


print("=" * 60)
print("M5 DEGRADATION DATASET GENERATED SUCCESSFULLY")
print("=" * 60)
print(f"Dataset path : {output_file}")
print(f"Records      : {len(df)}")
print(f"Columns      : {len(df.columns)}")
print()
print("Columns:")
print(df.columns.tolist())
print()
print("First 5 records:")
print(df.head())
print()
print("Failure Risk Distribution:")
print(df["failure_risk"].value_counts())
print("=" * 60)