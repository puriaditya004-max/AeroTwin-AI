import json
from pathlib import Path

from app.contracts import TelemetryFrame, TwinState


REPO_ROOT = Path(__file__).resolve().parents[4]


def test_shared_v2_samples_parse_with_m2_contracts():
    telemetry = json.loads((REPO_ROOT / "packages/schemas/samples/TelemetryFrame.sample.json").read_text())
    twin = json.loads((REPO_ROOT / "packages/schemas/samples/TwinState.sample.json").read_text())

    frame = TelemetryFrame.model_validate(telemetry)
    state = TwinState.model_validate(twin)

    assert frame.schemaVersion == "2.0.0"
    assert frame.sensors.chtCylindersC == [184, 187, 186, 185]
    assert state.schemaVersion == "2.0.0"
    assert state.derivedFeatures.featureVersion == "m2-features@2.0.0"
