"""
Integration-style Unit Tests for Redis Consumer, M6 Handoff & ModelRegistry Readiness
"""

import asyncio
import json
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.contracts import TwinState, Margins, DerivedFeatures, StateQuality, FaultPrediction, FaultType
from app.worker import M4Worker
from models.registry import ModelRegistry


def test_model_registry_readiness_correctness(tmp_path):
    """Verify ModelRegistry is_loaded=False when artifacts are missing."""
    registry = ModelRegistry(artifacts_dir=str(tmp_path))
    assert registry.load_artifacts() is False
    assert registry.is_loaded is False

    manifest = registry.get_manifest()
    assert manifest["is_loaded"] is False
    assert manifest["isolation_forest_sha256"] == "MISSING"
    assert manifest["feature_count"] == 16
    assert "feature_names" in manifest


def test_worker_rolling_window_per_engine_and_mission():
    """Verify rolling window is maintained per (engineId, missionId) tuple key."""
    worker = M4Worker()
    state1 = {"engineId": "ENG-1", "missionId": "MIS-A", "load": 50.0}
    state2 = {"engineId": "ENG-1", "missionId": "MIS-B", "load": 60.0}

    w1 = worker.update_rolling_window("ENG-1", "MIS-A", state1)
    w2 = worker.update_rolling_window("ENG-1", "MIS-B", state2)

    assert len(w1) == 1
    assert len(w2) == 1
    assert ("ENG-1", "MIS-A") in worker.rolling_windows
    assert ("ENG-1", "MIS-B") in worker.rolling_windows


@pytest.mark.asyncio
async def test_m6_handoff_with_idempotency_header_and_retry():
    """Verify worker pushes FaultPrediction to M6 with X-Idempotency-Key and retries on failure."""
    worker = M4Worker(max_retries=2)
    payload = {
        "engineId": "ENG-001",
        "missionId": "MIS-101",
        "correlationId": "CORR-UNIQUE-1234",
        "faultType": "OVERHEATING",
        "confidence": 0.92,
        "anomalyScore": 0.75,
        "contributors": []
    }

    # Mock HTTP client responses: First fails 500, Second succeeds 200
    mock_resp_fail = MagicMock()
    mock_resp_fail.status_code = 500

    mock_resp_pass = MagicMock()
    mock_resp_pass.status_code = 200

    worker.client.post = AsyncMock(side_effect=[mock_resp_fail, mock_pass := mock_resp_pass])

    success = await worker.publish_to_m6_with_retry(payload)
    assert success is True
    assert worker.client.post.call_count == 2

    # Check header
    call_args = worker.client.post.call_args
    headers = call_args.kwargs.get("headers", {})
    assert headers.get("X-Idempotency-Key") == "CORR-UNIQUE-1234"

    await worker.close()


@pytest.mark.asyncio
async def test_worker_ack_only_after_successful_pipeline():
    """Verify Redis messages are acknowledged only after predict + M6 handoff succeeds."""
    worker = M4Worker()
    redis_client = AsyncMock()
    worker.process_twin_state = AsyncMock(return_value={
        "engineId": "ENG-001",
        "missionId": "MIS-001",
        "correlationId": "CORR-001",
        "faultType": "NONE",
    })

    await worker.handle_redis_message(
        redis_client,
        "1-0",
        {"payload": json.dumps({"engineId": "ENG-001", "missionId": "MIS-001"})},
    )

    redis_client.xack.assert_awaited_once_with(worker.stream_name, worker.group_name, "1-0")
    assert worker.snapshot_metrics()["redis_messages_acked"] == 1
    await worker.close()


@pytest.mark.asyncio
async def test_worker_does_not_ack_failed_pipeline():
    """Verify failed M6 handoff leaves the Redis message pending for retry/recovery."""
    worker = M4Worker()
    redis_client = AsyncMock()
    worker.process_twin_state = AsyncMock(return_value=None)

    await worker.handle_redis_message(
        redis_client,
        "1-1",
        {"payload": json.dumps({"engineId": "ENG-001", "missionId": "MIS-001"})},
    )

    redis_client.xack.assert_not_called()
    assert worker.snapshot_metrics()["redis_messages_acked"] == 0
    await worker.close()


@pytest.mark.asyncio
async def test_worker_dead_letters_invalid_payload_and_acks_poison_message():
    """Verify invalid JSON is persisted to DLQ and acknowledged to avoid blocking the group."""
    worker = M4Worker()
    redis_client = AsyncMock()

    await worker.handle_redis_message(redis_client, "2-0", {"payload": "{bad-json"})

    redis_client.xadd.assert_awaited_once()
    redis_client.xack.assert_awaited_once_with(worker.stream_name, worker.group_name, "2-0")
    metrics = worker.snapshot_metrics()
    assert metrics["redis_messages_dlq"] == 1
    assert metrics["redis_messages_acked"] == 1
    await worker.close()


@pytest.mark.asyncio
async def test_worker_recovers_pending_message_before_reading_new_work():
    """Verify idle pending Redis messages are claimed and reprocessed by this consumer."""
    worker = M4Worker(pending_idle_ms=1)
    redis_client = AsyncMock()
    redis_client.xautoclaim.return_value = (
        "0-0",
        [("3-0", {"payload": json.dumps({"engineId": "ENG-001", "missionId": "MIS-001"})})],
        [],
    )
    redis_client.xpending_range.return_value = [{"times_delivered": 2}]
    worker.process_twin_state = AsyncMock(return_value={
        "engineId": "ENG-001",
        "missionId": "MIS-001",
        "correlationId": "CORR-001",
        "faultType": "NONE",
    })

    await worker.recover_pending_messages(redis_client)

    redis_client.xack.assert_awaited_once_with(worker.stream_name, worker.group_name, "3-0")
    assert worker.snapshot_metrics()["redis_pending_claimed"] == 1
    await worker.close()


@pytest.mark.asyncio
async def test_worker_dead_letters_poison_pending_after_delivery_limit():
    """Verify repeatedly failing pending messages are moved to DLQ after a bounded delivery count."""
    worker = M4Worker(dead_letter_after_deliveries=3)
    redis_client = AsyncMock()
    redis_client.xautoclaim.return_value = (
        "0-0",
        [("4-0", {"payload": json.dumps({"engineId": "ENG-001", "missionId": "MIS-001"})})],
        [],
    )
    redis_client.xpending_range.return_value = [{"times_delivered": 3}]

    await worker.recover_pending_messages(redis_client)

    redis_client.xadd.assert_awaited_once()
    redis_client.xack.assert_awaited_once_with(worker.stream_name, worker.group_name, "4-0")
    assert worker.snapshot_metrics()["redis_messages_dlq"] == 1
    await worker.close()
