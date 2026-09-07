from datetime import datetime, timezone
import pytest
from app.runtime import ScenarioRunner, RunState

@pytest.mark.asyncio
async def test_live_frame_clock_and_unique_correlation():
    runner = ScenarioRunner()
    runner.state = RunState(scenario="normal", seed=42, mission_id="MSN-LIVE-001",
        correlation_id="run-1", started_at=datetime.now(timezone.utc))
    captured = []
    async def capture(frame): captured.append(frame)
    runner.publisher.publish = capture
    model = runner.catalog.model("normal")
    await runner._emit_tick(model)
    await runner._emit_tick(model)
    assert len(captured) >= 2
    assert abs((captured[0].timestamp-datetime.now(timezone.utc)).total_seconds()) < 5
    assert captured[0].correlationId != captured[-1].correlationId
    assert captured[0].missionId == "MSN-LIVE-001"
