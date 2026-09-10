"""Calibrate M4 on actual M1->M2 synthetic outputs using mission-separated splits.

This is module calibration, not a live E2E run. Artifact promotion is a separate step.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def stage(service, code, payload=None):
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT / "services" / service,
        input=json.dumps(payload), capture_output=True, text=True, env=env)
    if result.returncode:
        raise RuntimeError(result.stderr[-8000:])
    return json.loads(result.stdout.split("RESULT:")[-1])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    splits = {"train": list(range(100, 108)), "validation": [200, 201, 202], "test": [300, 301, 302]}
    print("Generating real M1 synthetic mission frames...", flush=True)
    frames = stage("telemetry-simulator", '''
import json,sys
from app.runtime import ScenarioRunner
runner=ScenarioRunner(); result=[]
for split,seeds in json.load(sys.stdin).items():
    for scenario in runner.catalog.names():
        for seed in seeds:
            frames=runner.replay(scenario,seed)
            result.append({"split":split,"scenario":scenario,"seed":seed,
                "frames":[f.model_dump(mode="json",exclude_none=True) for f in frames]})
print("RESULT:"+json.dumps(result))
''', splits)
    print("Estimating M2 states with source-time replay clock...", flush=True)
    states = stage("twin-engine", '''
import json,sys
from datetime import datetime,timedelta
from unittest.mock import patch
from app.processor import TwinProcessor
from app.settings import get_settings
result=[]
for mission in json.load(sys.stdin):
    processor=TwinProcessor(get_settings()); states=[]
    for frame in mission.pop("frames"):
        clock=datetime.fromisoformat(frame["timestamp"].replace("Z","+00:00"))+timedelta(milliseconds=10)
        with patch("state.estimator.datetime") as dt:
            dt.now.return_value=clock
            state=processor.process_payload(frame).state
        if state: states.append(state.model_dump(mode="json",exclude_none=True))
    result.append({**mission,"states":states})
print("RESULT:"+json.dumps(result))
''', frames)
    print("Training, calibrating and evaluating disjoint held-out missions...", flush=True)
    metrics = stage("fault-ai", '''
import json,sys,os,hashlib
from pathlib import Path
import numpy as np
import sklearn,xgboost
from sklearn.metrics import classification_report,confusion_matrix
from app.contracts import TwinState,FaultType
from features.builder import FeaturePipeline
from models.classifier import FaultClassifier,LABEL_MAP
from models.anomaly import AnomalyEngine
from models.fusion import DecisionFusionPolicy
data=json.load(sys.stdin); output=Path(data["output"])
pipeline=FeaturePipeline(include_sensor_temperatures=True); splits={k:[] for k in ("train","validation","test")}; manifest=[]
for mission in data["missions"]:
    window=[]
    for payload in mission["states"]:
        state=TwinState.model_validate(payload);window.append(state);window=window[-30:]
        label="NONE"
        # Scenario ground truth is activated only after observable fault onset.
        # Early nominal sections and poor-quality frames are not physical faults.
        if state.stateQuality=="GOOD":
            sensors=payload["sensors"]
            if mission["scenario"]=="oil_pressure_degradation" and state.margins.pressureMarginKpa<0:
                label="OIL_PRESSURE_DEGRADATION"
            elif mission["scenario"]=="overheating" and (sensors["oilTempC"]>115 or sensors["coolantTempC"]>110):
                label="OVERHEATING"
            elif mission["scenario"]=="vibration_misfire" and state.margins.vibrationMarginMmS<4:
                label="VIBRATION_MISFIRE"
        splits[mission["split"]].append((pipeline.extract_from_window(window),LABEL_MAP[label],state,mission["scenario"]))
    manifest.append({"split":mission["split"],"scenario":mission["scenario"],"seed":mission["seed"],"missionId":state.missionId,"states":len(mission["states"])})
def xy(split):
    rows=splits[split]
    # Quality policy handles degraded/stale states; classifier sees GOOD data.
    rows=[r for r in rows if r[2].stateQuality=="GOOD"]
    return np.asarray([r[0] for r in rows]),np.asarray([r[1] for r in rows])
xt,yt=xy("train");xv,yv=xy("validation")
classifier=FaultClassifier(random_state=42);classifier.base_model.set_params(n_jobs=1)
classifier.fit(xt,yt,xv,yv)
assert classifier.calibrated_model is not None,"Calibration failed"
anomaly=AnomalyEngine(random_state=42);anomaly.model.set_params(n_jobs=1);anomaly.fit(xt[yt==0])
rows=splits["test"]; x=np.asarray([r[0] for r in rows]);truth=np.asarray([r[1] for r in rows])
types,confidence=classifier.predict(x);scores=anomaly.predict_anomaly_score(x)
policy=DecisionFusionPolicy();pred=[]
for row,t,c,a in zip(rows,types,confidence,scores):
    pred.append(LABEL_MAP[policy.fuse(row[2],float(a),t,float(c),[]).faultType.value])
report=classification_report(truth,pred,labels=[0,1,2,3],target_names=["NONE","OVERHEATING","OIL_PRESSURE_DEGRADATION","VIBRATION_MISFIRE"],output_dict=True,zero_division=0)
normal=[i for i,r in enumerate(rows) if r[3]=="normal"]
metrics={"scope":"synthetic module calibration; not E2E or real-engine validation","producerVersion":"m4-integrated@2.0.0", "sklearn":sklearn.__version__,"xgboost":xgboost.__version__,
    "splits":{k:len(v) for k,v in splits.items()},"classification":report,
    "confusionMatrix":confusion_matrix(truth,pred,labels=[0,1,2,3]).tolist(),
    "normalPhysicalClaims":sum(pred[i]!=0 for i in normal),
    "normalMaximumAnomaly":float(max(scores[i] for i in normal)),
    "featureNames":pipeline.feature_names,
    "sensorFaultPolicy":"Poor quality returns NONE with confidence zero; no learned sensor-fault claim"}
assert report["macro avg"]["f1-score"]>=0.85,metrics
assert report["OIL_PRESSURE_DEGRADATION"]["recall"]>=0.9,metrics
assert report["OVERHEATING"]["recall"]>=0.9,metrics
assert metrics["normalPhysicalClaims"]==0,metrics
assert metrics["normalMaximumAnomaly"]<0.75,metrics
classifier.save(str(output/"xgboost_fault.json"),str(output/"calibrated_classifier.joblib"))
anomaly.save(str(output/"isolation_forest.joblib"))
(output/"metrics.json").write_text(json.dumps(metrics,indent=2))
(output/"split_manifest.json").write_text(json.dumps(manifest,indent=2))
print("RESULT:"+json.dumps(metrics))
''', {"output": str(output), "missions": states})
    sources = [*ROOT.glob("services/telemetry-simulator/configs/scenarios/*.yaml"),
        ROOT / "services/twin-engine/state/estimator.py", ROOT / "services/twin-engine/state/features.py",
        ROOT / "services/fault-ai/features/builder.py", Path(__file__)]
    (output / "source_hashes.json").write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},indent=2))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
