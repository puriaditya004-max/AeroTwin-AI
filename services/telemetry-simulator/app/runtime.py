from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from typing import Any
import uuid

from app.logging import log_event
from app.settings import Settings, get_settings
from simulation.engine_model import EngineModel
from simulation.scenarios import ScenarioCatalog
from simulation.seed import derive_correlation_id, derive_mission_id, rng_from_seed
from stream.publisher import FramePublisher, InMemoryPublisher, RetryingPublisher

DESIRED_KEY = "m1:desired"
LEASE_KEY = "m1:publisher-lease"


@dataclass
class RunState:
    scenario: str | None = None
    status: str = "idle"
    seed: int | None = None
    mission_id: str | None = None
    correlation_id: str | None = None
    tick: int = 0
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    error: str | None = None
    owner_id: str = field(default_factory=lambda: uuid.uuid4().hex)


class ScenarioRunner:
    def __init__(self, settings: Settings | None = None, publisher: RetryingPublisher | None = None):
        self.settings = settings or get_settings()
        self.catalog = ScenarioCatalog(self.settings)
        inner: FramePublisher = InMemoryPublisher()
        self.publisher = publisher or RetryingPublisher(inner, self.settings.publish)
        self.state = RunState()
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self.enable_publisher = self.settings.enablePublisher
        self.redis: Any = None

    def list_scenarios(self) -> list[dict[str, Any]]:
        items = []
        for name in self.catalog.names():
            definition = self.catalog.get(name)
            items.append(
                {
                    "id": name,
                    "name": definition.get("name", name),
                    "description": definition.get("description", ""),
                    "durationSeconds": definition.get("durationSeconds"),
                    "publishRateHz": definition.get("publishRateHz", self.settings.publish.defaultRateHz),
                    "injectAfterSeconds": definition.get("fault", {}).get("injectAfterSeconds", 0),
                    "status": "running" if self.state.scenario == name and self.state.status == "running" else "idle",
                    "active": self.state.scenario == name and self.state.status == "running",
                }
            )
        return items

    def snapshot(self) -> dict[str, Any]:
        metrics = self.publisher.metrics_snapshot()
        return {
            "status": self.state.status,
            "scenario": self.state.scenario,
            "seed": self.state.seed,
            "missionId": self.state.mission_id,
            "correlationId": self.state.correlation_id,
            "tick": self.state.tick,
            "startedAt": self.state.started_at.isoformat() if self.state.started_at else None,
            "stoppedAt": self.state.stopped_at.isoformat() if self.state.stopped_at else None,
            "error": self.state.error,
            "publisher": metrics,
        }

    async def start(self, name: str, seed: int | None = None, mission_id: str | None = None, correlation_id: str | None = None) -> dict[str, Any]:
        definition = self.catalog.get(name)
        if self.state.status == "running":
            if self.state.scenario == name:
                return self.snapshot()
            raise RuntimeError(f"Scenario {self.state.scenario} is already running")
        resolved_seed = int(seed if seed is not None else definition.get("seed", 1))
        resolved_mission = mission_id or derive_mission_id(name, resolved_seed)
        resolved_corr = correlation_id or derive_correlation_id(name, resolved_seed)
        self._stop.clear()
        self.state = RunState(
            scenario=name,
            status="running",
            seed=resolved_seed,
            mission_id=resolved_mission,
            correlation_id=resolved_corr,
            tick=0,
            started_at=datetime.now(timezone.utc),
        )
        self.publisher.current_scenario = name
        await self._write_desired(running=True)
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run_loop())
        log_event(
            "scenario_started",
            scenario=name,
            seed=resolved_seed,
            missionId=resolved_mission,
            correlationId=resolved_corr,
        )
        return self.snapshot()

    async def stop(self, name: str | None = None) -> dict[str, Any]:
        if name is not None and self.state.scenario and self.state.scenario != name:
            raise KeyError(f"Scenario {name} is not the active run ({self.state.scenario})")
        self._stop.set()
        if self._task is not None:
            await asyncio.sleep(0)
        self.state.status = "stopped"
        self.state.stopped_at = datetime.now(timezone.utc)
        self.publisher.current_scenario = None
        await self._write_desired(running=False)
        log_event("scenario_stopped", scenario=self.state.scenario, correlationId=self.state.correlation_id)
        return self.snapshot()

    async def _run_loop(self) -> None:
        if not self.enable_publisher:
            return
        try:
            while not self._stop.is_set() and self.state.status == "running" and self.state.scenario:
                model = self.catalog.model(self.state.scenario)
                if model.is_complete(self.state.tick):
                    self.state.status = "completed"
                    self.state.stopped_at = datetime.now(timezone.utc)
                    self.publisher.current_scenario = None
                    await self._write_desired(running=False)
                    log_event("scenario_completed", scenario=self.state.scenario, correlationId=self.state.correlation_id)
                    break
                if await self._has_publisher_lease():
                    await self._emit_tick(model)
                interval = 1.0 / float(model.rate_hz or self.settings.publish.defaultRateHz)
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=interval)
                except asyncio.TimeoutError:
                    continue
        except asyncio.CancelledError:
            self.state.status = "stopped"
            raise
        except Exception as exc:
            self.state.status = "error"
            self.state.error = str(exc)
            log_event("scenario_error", scenario=self.state.scenario, error=str(exc))

    async def _emit_tick(self, model: EngineModel) -> None:
        assert self.state.seed is not None
        rng = rng_from_seed(self.state.seed + self.state.tick)
        quality_rng = rng_from_seed(self.state.seed + 7919 + self.state.tick)
        frames, _flag, skip_publish = model.build_frame(
            self.state.tick,
            rng,
            mission_id=self.state.mission_id or "",
            correlation_id=self.state.correlation_id or "",
            quality_rng=quality_rng,
        )
        self.state.tick += 1
        if skip_publish:
            self.publisher.record_drop()
            log_event(
                "frame_dropped",
                correlationId=self.state.correlation_id,
                scenario=self.state.scenario,
                qualityFlag="DROPOUT",
                tick=self.state.tick,
            )
            return
        for frame in frames:
            await self.publisher.publish(frame)

    async def _write_desired(self, running: bool) -> None:
        if self.redis is None:
            return
        payload = {
            "running": running,
            "scenario": self.state.scenario,
            "seed": self.state.seed,
            "missionId": self.state.mission_id,
            "correlationId": self.state.correlation_id,
        }
        await self.redis.set(DESIRED_KEY, json.dumps(payload))

    async def read_desired(self) -> dict[str, Any] | None:
        if self.redis is None:
            return None
        raw = await self.redis.get(DESIRED_KEY)
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)

    async def follow_desired(self) -> None:
        desired = await self.read_desired()
        if not desired:
            return
        if desired.get("running"):
            name = desired.get("scenario")
            if not name:
                return
            if self.state.status == "running" and self.state.scenario == name:
                return
            if self.state.status == "running":
                await self.stop(self.state.scenario)
            await self.start(
                name,
                seed=desired.get("seed"),
                mission_id=desired.get("missionId"),
                correlation_id=desired.get("correlationId"),
            )
            return
        if self.state.status == "running":
            await self.stop(self.state.scenario)

    async def _has_publisher_lease(self) -> bool:
        if self.redis is None:
            return True
        ttl = self.settings.publish.leaseTtlSeconds
        owner = self.state.owner_id
        acquired = await self.redis.set(LEASE_KEY, owner, nx=True, ex=ttl)
        if acquired:
            return True
        current = await self.redis.get(LEASE_KEY)
        if current in {owner, owner.encode() if isinstance(owner, str) else owner}:
            await self.redis.expire(LEASE_KEY, ttl)
            return True
        return False

    def replay(self, name: str, seed: int | None = None) -> list[Any]:
        definition = self.catalog.get(name)
        resolved_seed = int(seed if seed is not None else definition.get("seed", 1))
        model = self.catalog.model(name)
        return model.replay(
            resolved_seed,
            derive_mission_id(name, resolved_seed),
            derive_correlation_id(name, resolved_seed),
        )


_runner: ScenarioRunner | None = None


def get_runner() -> ScenarioRunner:
    global _runner
    if _runner is None:
        _runner = ScenarioRunner()
    return _runner


def reset_runner() -> None:
    global _runner
    _runner = None
