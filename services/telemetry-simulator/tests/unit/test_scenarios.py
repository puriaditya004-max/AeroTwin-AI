from app.contracts import QualityFlag
from app.settings import get_settings
from simulation.engine_model import REQUIRED_SENSORS
from simulation.scenarios import ScenarioCatalog
from simulation.seed import derive_correlation_id, derive_mission_id


SCENARIOS = (
    "normal",
    "overheating",
    "oil_pressure_degradation",
    "vibration_misfire",
    "sensor_dropout",
)


def _replay(name: str, seed: int = 11):
    catalog = ScenarioCatalog(get_settings())
    model = catalog.model(name)
    return model, model.replay(seed, derive_mission_id(name, seed), derive_correlation_id(name, seed))


def test_all_scenarios_are_registered():
    catalog = ScenarioCatalog(get_settings())
    assert catalog.names() == sorted(SCENARIOS)


def test_each_scenario_emits_in_range_required_sensors():
    for name in SCENARIOS:
        model, frames = _replay(name)
        assert frames, name
        sample = frames[min(len(frames) - 1, 40)]
        dumped = sample.sensors.model_dump()
        for field_name in REQUIRED_SENSORS:
            assert field_name in dumped
        assert 700 <= sample.sensors.rpm <= 3600
        assert 0 <= sample.sensors.oilPressureKpa <= 1000
        assert -40 <= sample.sensors.coolantTempC <= 200
        assert 0 <= sample.sensors.vibrationMmS <= 50
        assert sample.correlationId
        assert sample.scenarioId == name
        assert sample.qualityFlag in QualityFlag


def test_oil_pressure_declines_after_inject_offset():
    model, frames = _replay("oil_pressure_degradation", seed=7)
    inject_tick = int(model.inject_after_s * model.rate_hz)
    before = [frame for frame in frames if frame.qualityFlag == QualityFlag.OK][:inject_tick]
    after = [frame for frame in frames if frame.qualityFlag == QualityFlag.OK][inject_tick + 10 :]
    assert before and after
    assert after[-1].sensors.oilPressureKpa < before[0].sensors.oilPressureKpa
    assert after[-1].sensors.oilPressureKpa < 140


def test_overheating_raises_coolant_after_inject_offset():
    model, frames = _replay("overheating", seed=3)
    inject_tick = int(model.inject_after_s * model.rate_hz)
    ok_frames = [frame for frame in frames if frame.qualityFlag == QualityFlag.OK]
    early = ok_frames[0]
    late = ok_frames[-1]
    assert late.sensors.coolantTempC > early.sensors.coolantTempC
    assert inject_tick > 0


def test_vibration_misfire_has_spikes_after_offset():
    model, frames = _replay("vibration_misfire", seed=21)
    inject_tick = int(model.inject_after_s * model.rate_hz)
    ok_frames = [frame for frame in frames if frame.qualityFlag == QualityFlag.OK]
    early = [frame.sensors.vibrationMmS for frame in ok_frames[:inject_tick]]
    late = [frame.sensors.vibrationMmS for frame in ok_frames[inject_tick:]]
    assert early and late
    assert max(late) > max(early)
    assert max(late) >= 12


def test_normal_stays_inside_nominal_band():
    _model, frames = _replay("normal", seed=42)
    pressures = [frame.sensors.oilPressureKpa for frame in frames]
    coolants = [frame.sensors.coolantTempC for frame in frames]
    assert max(pressures) - min(pressures) < 30
    assert max(coolants) - min(coolants) < 10
