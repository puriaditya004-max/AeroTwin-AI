"""
Integration-style Unit Tests for Redis Consumer, M6 Handoff & ModelRegistry Readiness
"""

import asyncio
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
