from datetime import datetime, timezone

import sys
from pathlib import Path


# =========================================================
# Shared AeroTwin contracts
# =========================================================

SHARED_CONTRACTS_PATH = (
    Path("/app/packages/schemas/python")
)

if not SHARED_CONTRACTS_PATH.exists():
    SHARED_CONTRACTS_PATH = (
        Path(__file__).resolve().parents[3]
        / "packages"
        / "schemas"
        / "python"
    )

if str(SHARED_CONTRACTS_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_CONTRACTS_PATH))

from contracts import RulBasis, RulEstimate


# =========================================================
# M5 Contract Configuration
# =========================================================

PRODUCER_VERSION = "rul-reg-1.0.0"


# =========================================================
# Build canonical M5 → M6 RulEstimate
# =========================================================

def build_rul_estimate(
    *,
    engine_id: str,
    mission_id: str,
    correlation_id: str,
    predicted_rul: float,
    lower_bound: float,
    upper_bound: float,
    trend: str,
) -> RulEstimate:
    """
    Convert an M5 RUL prediction into the canonical
    AeroTwin RulEstimate contract consumed by M6.
    """

    return RulEstimate(
        engineId=engine_id,
        missionId=mission_id,
        correlationId=correlation_id,
        estimateTime=datetime.now(timezone.utc),
        producerVersion=PRODUCER_VERSION,
        cycles=predicted_rul,
        lowerBound=lower_bound,
        upperBound=upper_bound,
        trend=trend,
        experimental=True,
        basis=RulBasis.ML_REGRESSION,
    )