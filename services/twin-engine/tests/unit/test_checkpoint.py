import json

import pytest

from app.contracts import TwinState
from storage.checkpoint import RedisCheckpointStore


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.sets = {}

    async def set(self, key, value):
        self.values[key] = value

    async def get(self, key):
        return self.values.get(key)

    async def sadd(self, key, value):
        self.sets.setdefault(key, set()).add(value)


def sample_state():
    return TwinState.model_validate(
        {
            "engineId": "ENG-CKPT",
            "missionId": "MIS-CKPT",
            "correlationId": "corr-ckpt",
            "stateTime": "2026-08-25T12:00:00Z",
            "producerVersion": "m2-twin-engine@1.0.0",
            "load": 60,
            "margins": {
                "tempMarginC": 18,
                "pressureMarginKpa": 120,
                "vibrationMarginMmS": 7,
            },
            "derivedFeatures": {
                "rollingMeanRpm": 2300,
                "rollingStdVibration": 0.4,
                "rateOfChangeOilTempCPerMin": 0.8,
                "sampleWindowSeconds": 30,
            },
            "stateQuality": "GOOD",
            "syncLagMs": 20,
        }
    )


@pytest.mark.asyncio
async def test_redis_checkpoint_round_trips_latest_state_and_stream_id():
    redis = FakeRedis()
    store = RedisCheckpointStore(redis)
    state = sample_state()

    await store.save(state, "123-0")
    loaded = await store.latest("ENG-CKPT", "MIS-CKPT")

    assert loaded is not None
    assert loaded.correlationId == "corr-ckpt"
    assert redis.values["m2:twin:last-stream-id"] == "123-0"
    assert json.loads(redis.values["m2:twin:state:ENG-CKPT:MIS-CKPT"])["engineId"] == "ENG-CKPT"
