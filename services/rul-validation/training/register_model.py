from pathlib import Path

import mlflow
from mlflow import MlflowClient


# ============================================================
# M5 - MLflow Model Registry
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

TRACKING_DB = BASE_DIR / "mlflow.db"

EXPERIMENT_NAME = "AeroTwin-M5-RUL"
REGISTERED_MODEL_NAME = "AeroTwin-M5-RUL-XGBoost"


def main():

    print("=" * 60)
    print("M5 - MLflow Model Registry")
    print("=" * 60)

    # --------------------------------------------------------
    # Tracking URI
    # --------------------------------------------------------

    tracking_uri = f"sqlite:///{TRACKING_DB.as_posix()}"

    mlflow.set_tracking_uri(tracking_uri)

    client = MlflowClient()

    print("\nTracking URI:")
    print(tracking_uri)

    print("\nExperiment:")
    print(EXPERIMENT_NAME)

    # --------------------------------------------------------
    # Get experiment
    # --------------------------------------------------------

    experiment = client.get_experiment_by_name(
        EXPERIMENT_NAME
    )

    if experiment is None:
        raise RuntimeError(
            f"Experiment '{EXPERIMENT_NAME}' not found."
        )

    # --------------------------------------------------------
    # Find successful run
    # --------------------------------------------------------

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        filter_string="attributes.status = 'FINISHED'",
        order_by=["start_time DESC"],
        max_results=10,
    )

    if not runs:
        raise RuntimeError(
            "No successful MLflow run found."
        )

    run = runs[0]

    run_id = run.info.run_id

    print("\nLatest successful Run ID:")
    print(run_id)

    # --------------------------------------------------------
    # Check artifacts
    # --------------------------------------------------------

    artifacts = client.list_artifacts(run_id)

    print("\nArtifacts:")

    for artifact in artifacts:
        print(" -", artifact.path)

    model_artifact = None

    for artifact in artifacts:
        if artifact.path == "model":
            model_artifact = artifact.path
            break

    if model_artifact is None:
        raise RuntimeError(
            "Model artifact not found in MLflow run."
        )

    # --------------------------------------------------------
    # Model source
    # --------------------------------------------------------

    model_source = (
        f"runs:/{run_id}/{model_artifact}"
    )

    print("\nModel source:")
    print(model_source)

    # --------------------------------------------------------
    # Create registered model if needed
    # --------------------------------------------------------

    try:

        client.get_registered_model(
            REGISTERED_MODEL_NAME
        )

        print(
            "\nRegistered model already exists:"
        )
        print(REGISTERED_MODEL_NAME)

    except Exception:

        print(
            "\nCreating registered model..."
        )

        client.create_registered_model(
            REGISTERED_MODEL_NAME
        )

        print(
            "Registered model created successfully."
        )

    # --------------------------------------------------------
    # Create model version directly
    # --------------------------------------------------------

    print("\nCreating model version...")

    try:

        version = client.create_model_version(
            name=REGISTERED_MODEL_NAME,
            source=model_source,
            run_id=run_id,
        )

        print("\nModel version created successfully!")

        print(
            "Model:",
            version.name
        )

        print(
            "Version:",
            version.version
        )

        print(
            "Run ID:",
            version.run_id
        )

        print(
            "Source:",
            version.source
        )

    except Exception as exc:

        print(
            "\nModel version creation failed."
        )

        print(
            "Error:",
            exc
        )

        raise

    # --------------------------------------------------------
    # List registered versions
    # --------------------------------------------------------

    print("\nRegistered model versions:")

    versions = client.search_model_versions(
        f"name='{REGISTERED_MODEL_NAME}'"
    )

    for item in versions:

        print(
            f" - Version {item.version}"
            f" | Run: {item.run_id}"
            f" | Status: {item.status}"
        )

    print("\n" + "=" * 60)
    print("M5 Model Registry completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()