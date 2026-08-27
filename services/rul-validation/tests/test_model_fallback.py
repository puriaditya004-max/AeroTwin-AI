from app.predictor import RULPredictor


def test_predictor_has_model_source():
    predictor = RULPredictor()

    assert predictor.model is not None
    assert predictor.model_source is not None


def test_predictor_can_generate_rul():
    predictor = RULPredictor()

    rul = predictor.predict(
        temperature=61.3,
        vibration=0.59,
        pressure=97.5,
        rpm=2931.0,
        load=70.3,
        health_index=0.97,
    )

    assert isinstance(rul, float)
    assert rul >= 0


def test_local_fallback_is_available():
    predictor = RULPredictor()

    assert predictor.model_source in [
        "local:rul_xgboost.joblib",
        "mlflow:AeroTwin-M5-RUL-XGBoost:2",
    ]