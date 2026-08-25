import json

import pytest

from app.contracts import TwinState
from app.worker import M2Worker
from ingest.consumer import decode_stream_payload
from stream.publisher import TwinStatePublisher


def test_decode_stream_payload_accepts_bytes_payload():
    payload = {"engineId": "ENG-001"}

    decoded = decode_stream_payload({b"payload": json.dumps(payload).encode("utf-8")})

    assert decoded == payload


class FakeRedis:
    def __init__(self):
        self.calls = []

    async def xadd(self, stream_name, fields):
        self.calls.append((stream_name, fields))
        return b"1-0"


@pytest.mark.asyncio
async def test_twin_state_publisher_writes_canonical_payload_field():
    redis = FakeRedis()
    state = TwinState.model_validate(
        {
            "engineId": "ENG-001",
            "missionId": "MIS-001",
            "correlationId": "corr-001",
            "stateTime": "2026-08-25T12:00:00Z",
            "producerVersion": "m2-twin-engine@1.0.0",
            "load": 50,
            "margins": {
                "tempMarginC": 20,
                "pressureMarginKpa": 100,
                "vibrationMarginMmS": 8,
            },
            "derivedFeatures": {
                "rollingMeanRpm": 2200,
                "rollingStdVibration": 0.2,
                "rateOfChangeOilTempCPerMin": 1.1,
                "sampleWindowSeconds": 30,
            },
            "stateQuality": "GOOD",
            "syncLagMs": 10,
        }
    )

    message_id = await TwinStatePublisher(redis, "twin.state.v1").publish(state)

    assert message_id == "1-0"
    stream_name, fields = redis.calls[0]
    assert stream_name == "twin.state.v1"
    assert json.loads(fields["payload"])["correlationId"] == "corr-001"


class PendingRedis:
    async def xautoclaim(self, *args, **kwargs):
        return ("0-0", [(b"1-0", {b"payload": b'{"engineId":"ENG"}'})], [])


@pytest.mark.asyncio
async def test_worker_claims_pending_messages_for_restart_recovery():
    worker = M2Worker()

    streams = await worker._read_pending(PendingRedis())

    assert streams[0][0] == "telemetry.frame.v1"
    assert streams[0][1][0][0] == b"1-0"
