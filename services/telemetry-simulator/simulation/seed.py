from __future__ import annotations

import random
from typing import Any


def rng_from_seed(seed: int) -> random.Random:
    """Return a deterministic PRNG for replayable missions."""
    return random.Random(int(seed))


def derive_correlation_id(scenario_id: str, seed: int) -> str:
    return f"corr-{scenario_id}-{seed}"


def derive_mission_id(scenario_id: str, seed: int) -> str:
    return f"MSN-{scenario_id.upper()}-{seed}"


def clone_rng(rng: random.Random) -> random.Random:
    clone = random.Random()
    clone.setstate(rng.getstate())
    return clone


def snapshot_state(rng: random.Random) -> Any:
    return rng.getstate()
