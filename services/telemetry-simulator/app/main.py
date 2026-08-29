from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from app.logging import log_event
from app.runtime import ScenarioRunner, get_runner
from app.settings import get_settings

try:
    import redis.asyncio as redis_async
except ImportError:  # pragma: no cover
    redis_async = None

from stream.publisher import RedisPublisher, RetryingPublisher


settings = get_settings()
runner = get_runner()

app = FastAPI(
    title="AeroTwin AI - M1 Telemetry Simulator",
    description=(
        "Synthetic telemetry publisher for demonstrator missions. "
        "Not real engine physics. Advisory demonstrator only."
    ),
    version=settings.service.version,
)


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime
    details: dict[str, Any] = {}


class StartScenarioRequest(BaseModel):
    seed: Optional[int] = Field(default=None, ge=0)
    missionId: Optional[str] = None
    correlationId: Optional[str] = None


@app.on_event("startup")
async def startup() -> None:
    await attach_redis_publisher(runner)
    log_event("api_started", port=settings.service.port, stream=settings.streams.output)


async def attach_redis_publisher(target: ScenarioRunner) -> None:
    if redis_async is None:
        return
    try:
        client = redis_async.from_url(settings.redisUrl)
        await client.ping()
        inner = RedisPublisher(client, settings.streams.output, settings.streams.field)
        target.publisher = RetryingPublisher(inner, settings.publish)
        target.publisher.current_scenario = target.state.scenario
        target.redis = client
        log_event("redis_attached", redisUrl=settings.redisUrl, stream=settings.streams.output)
    except Exception as exc:
        log_event("redis_unavailable", error=str(exc))


@app.get("/health/live", response_model=HealthResponse)
async def health_live():
    return HealthResponse(
        status="UP",
        service=settings.service.name,
        version=settings.service.version,
        timestamp=datetime.now(timezone.utc),
        details={"run": runner.snapshot()},
    )


@app.get("/health/ready", response_model=HealthResponse)
async def health_ready():
    details: dict[str, Any] = {
        "outputStream": settings.streams.output,
        "producerVersion": settings.service.producerVersion,
        "scenarios": runner.catalog.names(),
    }
    try:
        ready = await runner.publisher.ping()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Publisher not ready: {exc}",
        ) from exc
    if not ready:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Publisher ping failed")
    details["publisher"] = True
    return HealthResponse(
        status="READY",
        service=settings.service.name,
        version=settings.service.version,
        timestamp=datetime.now(timezone.utc),
        details=details,
    )


@app.get("/metrics")
async def metrics():
    return runner.publisher.metrics_snapshot()


@app.get("/scenarios")
async def list_scenarios():
    return {
        "scenarios": runner.list_scenarios(),
        "run": runner.snapshot(),
    }


@app.post("/scenarios/{name}/start")
async def start_scenario(name: str, body: StartScenarioRequest | None = None):
    body = body or StartScenarioRequest()
    try:
        snapshot = await runner.start(
            name,
            seed=body.seed,
            mission_id=body.missionId,
            correlation_id=body.correlationId,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return snapshot


@app.post("/scenarios/{name}/stop")
async def stop_scenario(name: str):
    try:
        snapshot = await runner.stop(name)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return snapshot
