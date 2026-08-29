from app.settings import get_settings
from simulation.scenarios import ScenarioCatalog
from simulation.seed import derive_correlation_id, derive_mission_id


def test_same_seed_replays_identical_frames():
    catalog = ScenarioCatalog(get_settings())
    model = catalog.model("oil_pressure_degradation")
    seed = 7
    mission_id = derive_mission_id("oil_pressure_degradation", seed)
    correlation_id = derive_correlation_id("oil_pressure_degradation", seed)
    first = [frame.model_dump(mode="json") for frame in model.replay(seed, mission_id, correlation_id)]
    second = [frame.model_dump(mode="json") for frame in model.replay(seed, mission_id, correlation_id)]
    assert first == second
    assert first[0]["correlationId"] == correlation_id


def test_different_seeds_diverge():
    catalog = ScenarioCatalog(get_settings())
    model = catalog.model("normal")
    left = [frame.model_dump(mode="json") for frame in model.replay(1, "m", "c")]
    right = [frame.model_dump(mode="json") for frame in model.replay(2, "m", "c")]
    assert left != right
