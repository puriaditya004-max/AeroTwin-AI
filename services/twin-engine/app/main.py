from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

try:
    import redis.asyncio as redis_async
except ImportError:  # pragma: no cover
    redis_async = None

from app.processor import TwinProcessor
from app.settings import get_settings
from storage.checkpoint import InMemoryCheckpointStore


settings = get_settings()
checkpoint = InMemoryCheckpointStore()
processor = TwinProcessor(settings, checkpoint)

app = FastAPI(
    title="AeroTwin AI - M2 Digital Twin Engine",
    description="Contract-safe telemetry synchronization, rolling state estimation, and TwinState publishing.",
    version=settings.service.version,
)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime
    details: dict[str, Any] = {}


@app.get("/health/live", response_model=HealthResponse)
async def health_live():
    return HealthResponse(
        status="UP",
        service=settings.service.name,
        version=settings.service.version,
        timestamp=datetime.now(timezone.utc),
        details={"metrics": processor.metrics},
    )


@app.get("/health/ready", response_model=HealthResponse)
async def health_ready():
    details: dict[str, Any] = {
        "inputStream": settings.streams.input,
        "outputStream": settings.streams.output,
        "consumerGroup": settings.streams.group,
    }
    if redis_async is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="redis-py is not installed")
    redis_client = redis_async.from_url(settings.redisUrl)
    try:
        pong = await redis_client.ping()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Redis unavailable: {exc}") from exc
    finally:
        await redis_client.aclose()
    details["redis"] = bool(pong)
    return HealthResponse(
        status="READY",
        service=settings.service.name,
        version=settings.service.version,
        timestamp=datetime.now(timezone.utc),
        details=details,
    )


@app.get("/metrics")
async def metrics():
    return processor.metrics


@app.get("/state/latest")
async def latest_state():
    state = checkpoint.latest()
    if state is None:
        raise HTTPException(status_code=404, detail="No TwinState has been produced yet")
    return state


@app.get("/state/{engineId}")
async def latest_engine_state(engineId: str):
    state = checkpoint.latest(engine_id=engineId)
    if state is None:
        raise HTTPException(status_code=404, detail=f"No TwinState found for engine {engineId}")
    return state


@app.get("/state/{engineId}/{missionId}")
async def latest_engine_mission_state(engineId: str, missionId: str):
    state = checkpoint.latest(engine_id=engineId, mission_id=missionId)
    if state is None:
        raise HTTPException(status_code=404, detail=f"No TwinState found for {engineId}/{missionId}")
    return state


@app.get("/states/{missionId}/latest")
async def latest_mission_state(missionId: str):
    states = [state for state in checkpoint.all_states() if state.missionId == missionId]
    state = max(states, key=lambda item: item.stateTime, default=None)
    if state is None:
        raise HTTPException(status_code=404, detail=f"No TwinState found for mission {missionId}")
    return state
