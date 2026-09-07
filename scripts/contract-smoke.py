"""Pre-E2E: real module boundary checks in isolated processes; no Docker/DB claim."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def stage(service, code, payload=None):
    env = dict(os.environ, M5_ALLOW_EXPERIMENTAL_FALLBACK="true")
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT / "services" / service,
        input=json.dumps(payload), text=True, capture_output=True, env=env, check=True)
    return json.loads(result.stdout.split("RESULT:")[-1])


frames = stage("telemetry-simulator", '''
import json
from app.runtime import ScenarioRunner
runner=ScenarioRunner()
result={name: [f.model_dump(mode="json",exclude_none=True) for f in runner.replay(name,42)] for name in runner.catalog.names()}
print("RESULT:"+json.dumps(result))
''')
states = stage("twin-engine", '''
import json,sys
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from app.processor import TwinProcessor
from app.settings import get_settings
frames=json.load(sys.stdin)
result={}
for name,items in frames.items():
    processor=TwinProcessor(get_settings()); result[name]=[]
    for f in items:
        clock=datetime.fromisoformat(f["timestamp"].replace("Z","+00:00"))+timedelta(milliseconds=10)
        with patch("state.estimator.datetime") as dt:
            dt.now.return_value=clock
            state=processor.process_payload(f).state
        if state: result[name].append(state.model_dump(mode="json",exclude_none=True))
print("RESULT:"+json.dumps(result))
''', frames)
health = stage("health-monitor", '''
import json,sys
from fastapi.testclient import TestClient
from main import app
client=TestClient(app)
result={}
for name,states in json.load(sys.stdin).items():
    result[name]=[]
    for state in states:
        response=client.post("/evaluate",json=state); response.raise_for_status()
        result[name].append(response.json())
print("RESULT:"+json.dumps(result))
''', states)
rul = stage("rul-validation", '''
import json,sys
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app); result={}
data=json.load(sys.stdin)
for name,states in data["states"].items():
    result[name]=[]
    for state,health in zip(states,data["health"][name]):
        response=client.post("/estimate",json={"state":state,"health":health});response.raise_for_status()
        result[name].append(response.json())
print("RESULT:"+json.dumps(result))
''', {"states": states, "health": health})
# Real committed models, testing windows through actual M4 HTTP boundary.
fault = stage("fault-ai", '''
import json,sys
from fastapi.testclient import TestClient
from app.main import app,registry
result={}
with TestClient(app) as client:
    assert registry.is_loaded, registry.load_error
    for name,states in json.load(sys.stdin).items():
        result[name]=[]
        for i in range(0,len(states),10):
            response=client.post("/predict",json={"engineId":states[i]["engineId"],"missionId":states[i]["missionId"],"states":states[max(0,i-29):i+1]})
            response.raise_for_status(); result[name].append(response.json())
print("RESULT:"+json.dumps(result))
''', states)
from jsonschema import Draft7Validator
schemas = ROOT / "packages/schemas/json-schema"
checks = 0
for contract, batches in [("TelemetryFrame",frames),("TwinState",states),("HealthSnapshot",health),("RulEstimate",rul),("FaultPrediction",fault)]:
    validator=Draft7Validator(json.loads((schemas/f"{contract}.schema.json").read_text()))
    for batch in batches.values():
        for event in batch:
            validator.validate(event); checks+=1
for name in states:
    for state,h,r in zip(states[name],health[name],rul[name]):
        for key in ("engineId","missionId","correlationId"):
            assert state[key]==h[key]==r[key]
assert all(f["faultType"]=="NONE" for f in fault["normal"]), fault["normal"]
assert health["normal"][0]["dataQualityIssue"]  # M2 needs two samples to warm up.
assert all(h["healthScore"]==100 for h in health["normal"][1:])
assert any("RULE_PRESSURE_LOW" in h["violatedRules"] for h in health["oil_pressure_degradation"])
assert any("RULE_TEMP_WARN" in h["violatedRules"] for h in health["overheating"])
assert any("RULE_VIBRATION_EXCEEDED" in h["violatedRules"] for h in health["vibration_misfire"])
assert any(h["dataQualityIssue"] for h in health["sensor_dropout"])
report={"stage":"pre-E2E in-process module contracts", "schemaChecks":checks,
    "fullE2EVerified":False,
    "oilPressureClassObserved":any(f["faultType"]=="OIL_PRESSURE_DEGRADATION" for f in fault["oil_pressure_degradation"]),
    "scenarios":{name:{"states":len(states[name]),"minimumHealth":min(h['healthScore'] for h in health[name]),
        "faultTypes":sorted(set(f['faultType'] for f in fault[name])), "rulBasis":rul[name][-1]['basis']} for name in states}}
print(json.dumps(report,indent=2))
