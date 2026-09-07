import importlib.util
import json
from pathlib import Path

from jsonschema import Draft7Validator, FormatChecker

from app.contracts import QualityFlag, Sensors, TelemetryFrame
from app.settings import get_settings
from simulation.scenarios import ScenarioCatalog
from simulation.seed import derive_correlation_id, derive_mission_id


REPO_ROOT = Path(__file__).resolve().parents[4]
SCHEMA_PATH = REPO_ROOT / "packages/schemas/json-schema/TelemetryFrame.schema.json"
SHARED_CONTRACTS = REPO_ROOT / "packages/schemas/python/contracts.py"
SAMPLE_PATH = REPO_ROOT / "packages/schemas/samples/TelemetryFrame.sample.json"


def _load_shared_contracts():
    spec = importlib.util.spec_from_file_location("shared_contracts", SHARED_CONTRACTS)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_local_contract_fields_match_shared_schema_and_pydantic():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    shared = _load_shared_contracts()

    required = set(schema["required"])
    assert required == {"engineId", "missionId", "correlationId", "timestamp", "sensors", "qualityFlag", "producerVersion"}
    assert set(TelemetryFrame.model_fields) >= required
    assert set(shared.TelemetryFrame.model_fields) == set(TelemetryFrame.model_fields)

    sensor_required = set(schema["properties"]["sensors"]["required"])
    assert sensor_required <= set(Sensors.model_fields)
    assert set(shared.Sensors.model_fields) == set(Sensors.model_fields)

    quality_enum = set(schema["properties"]["qualityFlag"]["enum"])
    assert quality_enum == {item.value for item in QualityFlag}
    assert quality_enum == {item.value for item in shared.QualityFlag}


def test_sample_payload_validates_against_m1_and_json_schema():
    payload = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
    frame = TelemetryFrame.model_validate(payload)
    assert frame.correlationId == "corr-8f3a1c"
    assert frame.qualityFlag == QualityFlag.OK
    assert frame.sensors.coolantTempC == 88
    assert "cylinderTempC" not in frame.sensors.model_dump()

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft7Validator(schema, format_checker=FormatChecker()).validate(payload)


def test_generated_frame_matches_json_schema():
    settings = get_settings()
    catalog = ScenarioCatalog(settings)
    model = catalog.model("oil_pressure_degradation")
    frames = model.replay(7, derive_mission_id("oil_pressure_degradation", 7), derive_correlation_id("oil_pressure_degradation", 7))
    assert frames
    payload = frames[0].model_dump(mode="json")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft7Validator(schema, format_checker=FormatChecker()).validate(payload)
    assert payload["correlationId"]
    assert payload["qualityFlag"] in {"OK", "DEGRADED", "DROPOUT", "DUPLICATE", "OUT_OF_ORDER"}
