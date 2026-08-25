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
# 2. Select features
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


X = df[features]
y = df[target]


# --------------------------------
# 3. Train-Test Split
# --------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42
)


# --------------------------------
# 4. Create processed directory
# --------------------------------

output_dir = "data/processed"

os.makedirs(output_dir, exist_ok=True)


# --------------------------------
# 5. Save training data
# --------------------------------

train_data = X_train.copy()
train_data["rul_target"] = y_train

train_data.to_csv(
    f"{output_dir}/m5_train.csv",
    index=False
)


# --------------------------------
# 6. Save testing data
# --------------------------------

test_data = X_test.copy()
test_data["rul_target"] = y_test

test_data.to_csv(
    f"{output_dir}/m5_test.csv",
    index=False
)


# --------------------------------
# 7. Print information
# --------------------------------

print("\nM5 dataset preparation completed!")

print("Features:")
print(features)

print("\nTarget:")
print(target)

print("\nTraining samples:", len(X_train))
print("Testing samples :", len(X_test))

print("\nSaved files:")
print("data/processed/m5_train.csv")
print("data/processed/m5_test.csv")