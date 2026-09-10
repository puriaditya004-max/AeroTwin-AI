"""Local HTTP/database boundary smoke; creates a unique test mission, not E2E."""
import argparse
import json
from pathlib import Path
import urllib.request
import urllib.error
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://localhost:4000")
    args = parser.parse_args()
    def request(path, payload=None, headers=None):
        req = urllib.request.Request(args.api_url + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={"Content-Type": "application/json", **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            return exc.code, json.load(exc)

    run = uuid.uuid4().hex
    mission = "MSN-SMOKE-" + run
    assert request("/health")[0] == 200
    assert request("/missions/" + mission + "/state")[0] == 401
    assert request("/auth/dev-login", {})[0] == 404
    status, login = request("/auth/demo-login", {})
    assert status == 200
    headers = {"Authorization": "Bearer " + login["token"]}
    results = {}
    expected = {}
    samples = Path(__file__).resolve().parents[1] / "packages/schemas/samples"
    for route, contract, field in [("health", "HealthSnapshot", "healthScore"),
                                   ("fault", "FaultPrediction", "confidence"),
                                   ("rul", "RulEstimate", "cycles")]:
        payload = json.loads((samples / (contract + ".sample.json")).read_text())
        payload.update(missionId=mission, correlationId=run)
        expected[route] = payload
        idem = {"X-Idempotency-Key": "smoke-" + route + "-" + run}
        fresh, _ = request("/ingest/" + route, payload, idem)
        duplicate, body = request("/ingest/" + route, payload, idem)
        assert fresh == duplicate == 202, (route, fresh, duplicate, body)
        assert body.get("duplicate") is True, body
        changed = dict(payload)
        changed[field] = payload[field] * 0.9
        conflict, _ = request("/ingest/" + route, changed, idem)
        assert conflict == 409, (route, conflict)
        results[route] = {"fresh": fresh, "duplicate": duplicate, "conflict": conflict}
    status, state = request("/missions/" + mission + "/state", headers=headers)
    assert status == 200, state
    for route, payload in expected.items():
        assert state[route] == payload, (route, state[route])
    assert state["advisory"]["missionId"] == mission
    print(json.dumps({"scope": "HTTP/PostgreSQL boundary smoke; not browser E2E",
        "missionId": mission, "ingest": results, "authenticatedState": status}, indent=2))


if __name__ == "__main__":
    main()
