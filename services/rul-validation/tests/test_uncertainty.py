from app.predictor import RULPredictor


def create_predictor():
    return RULPredictor()


def test_uncertainty_response_contains_required_fields():
    predictor = create_predictor()

    result = predictor.predict_with_uncertainty(
        temperature=61.3,
        vibration=0.59,
        pressure=97.5,
        rpm=2931,
        load=70.3,
        health_index=0.9768,
    )

    assert "predicted_rul" in result
    assert "lower_bound" in result
    assert "upper_bound" in result
    assert "uncertainty_margin" in result
    assert "unit" in result


def test_uncertainty_bounds_are_valid():
    predictor = create_predictor()

    result = predictor.predict_with_uncertainty(
        temperature=61.3,
        vibration=0.59,
        pressure=97.5,
        rpm=2931,
        load=70.3,
        health_index=0.9768,
    )

    assert result["lower_bound"] <= result["predicted_rul"]
    assert result["predicted_rul"] <= result["upper_bound"]


def test_uncertainty_margin_is_non_negative():
    predictor = create_predictor()

    result = predictor.predict_with_uncertainty(
        temperature=61.3,
        vibration=0.59,
        pressure=97.5,
        rpm=2931,
        load=70.3,
        health_index=0.9768,
    )

    assert result["uncertainty_margin"] >= 0


def test_rul_stays_within_configured_bounds():
    predictor = create_predictor()

    result = predictor.predict_with_uncertainty(
        temperature=61.3,
        vibration=0.59,
        pressure=97.5,
        rpm=2931,
        load=70.3,
        health_index=0.9768,
    )

    assert result["lower_bound"] >= 0
    assert result["upper_bound"] <= 300


def test_prediction_is_inside_uncertainty_interval():
    predictor = create_predictor()

    result = predictor.predict_with_uncertainty(
        temperature=61.3,
        vibration=0.59,
        pressure=97.5,
        rpm=2931,
        load=70.3,
        health_index=0.9768,
    )

    assert (
        result["lower_bound"]
        <= result["predicted_rul"]
        <= result["upper_bound"]
    )
    