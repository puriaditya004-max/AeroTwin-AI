import os
import pandas as pd
from sklearn.model_selection import train_test_split


# --------------------------------
# 1. Load M5 dataset
# --------------------------------

input_file = "data/synthetic/m5_degradation.csv"

df = pd.read_csv(input_file)

print("M5 dataset loaded successfully")
print("Dataset shape:", df.shape)


# --------------------------------
# 2. Define unified M5 schema
# --------------------------------

required_columns = [
    "engine_id",
    "mission_id",
    "cycle",
    "health_score",
    "fault_confidence",
    "anomaly_score",
    "temperature",
    "oil_pressure",
    "vibration",
    "rul_target"
]


# --------------------------------
# 3. Validate dataset schema
# --------------------------------

missing_columns = [
    column for column in required_columns
    if column not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required M5 columns: {missing_columns}"
    )


# --------------------------------
# 4. Select M5 model features
# --------------------------------

features = [
    "cycle",
    "health_score",
    "fault_confidence",
    "anomaly_score",
    "temperature",
    "oil_pressure",
    "vibration"
]

target = "rul_target"


# --------------------------------
# 5. Validate numeric columns
# --------------------------------

numeric_columns = features + [target]

for column in numeric_columns:
    df[column] = pd.to_numeric(
        df[column],
        errors="raise"
    )


# --------------------------------
# 6. Remove invalid rows
# --------------------------------

df = df.dropna(
    subset=required_columns
).reset_index(drop=True)


if len(df) < 5:
    raise ValueError(
        "Not enough valid rows for M5 dataset preparation."
    )


# --------------------------------
# 7. Create X and y
# --------------------------------

X = df[features]
y = df[target]


# --------------------------------
# 8. Train-Test Split
# --------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42
)


# --------------------------------
# 9. Create processed directory
# --------------------------------

output_dir = "data/processed"

os.makedirs(output_dir, exist_ok=True)


# --------------------------------
# 10. Save training data
# --------------------------------

train_data = X_train.copy()

train_data["rul_target"] = y_train.values

train_data.to_csv(
    f"{output_dir}/m5_train.csv",
    index=False
)


# --------------------------------
# 11. Save testing data
# --------------------------------

test_data = X_test.copy()

test_data["rul_target"] = y_test.values

test_data.to_csv(
    f"{output_dir}/m5_test.csv",
    index=False
)


# --------------------------------
# 12. Validation output
# --------------------------------

print("\nM5 dataset preparation completed!")
print("----------------------------------------")

print("Unified schema validation: PASSED")

print("\nRequired columns:")
print(required_columns)

print("\nModel features:")
print(features)

print("\nTarget:")
print(target)

print("\nValid dataset rows:", len(df))

print("Training samples:", len(X_train))
print("Testing samples :", len(X_test))

print("\nSaved files:")
print("data/processed/m5_train.csv")
print("data/processed/m5_test.csv")