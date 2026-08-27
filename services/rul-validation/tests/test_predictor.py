from app.predictor import RULPredictor


def test_predictor_loads_model():
    predictor = RULPredictor()

    assert predictor.model is not None
    assert predictor.scaler is not None


def test_rul_prediction_returns_valid_value():
    predictor = RULPredictor()

    predicted_rul = predictor.predict(
        temperature=75,
        vibration=1.2,
        pressure=92,
        rpm=2850,
        load=75,
        health_index=0.7,
    )

    assert isinstance(predicted_rul, float)
    assert predicted_rul >= 0


def test_rul_prediction_is_reasonable():
    predictor = RULPredictor()

    predicted_rul = predictor.predict(
        temperature=80,
        vibration=1.5,
        pressure=88,
        rpm=2750,
        load=78,
        health_index=0.5,
    )

    assert predicted_rul >= 0
    assert predicted_rul <= 500