# =========================================================
# M5 - Prediction History Tests
# =========================================================

import pytest

from app.prediction_history import PredictionHistory


def create_prediction(rul: float):
    return {
        "predicted_rul": rul,
        "lower_bound": max(0, rul - 20),
        "upper_bound": rul + 20,
        "risk_level": "LOW",
        "health_status": "GOOD",
    }


# ---------------------------------------------------------
# History creation
# ---------------------------------------------------------

def test_history_starts_empty():

    history = PredictionHistory()

    assert history.size() == 0
    assert history.get_history() == []
    assert history.get_latest() is None
    assert history.get_previous() is None


# ---------------------------------------------------------
# Store prediction
# ---------------------------------------------------------

def test_prediction_is_stored():

    history = PredictionHistory()

    prediction = create_prediction(110)

    result = history.add_prediction(
        **prediction
    )

    assert result["predicted_rul"] == 110
    assert result["lower_bound"] == 90
    assert result["upper_bound"] == 130

    assert history.size() == 1


# ---------------------------------------------------------
# Multiple predictions
# ---------------------------------------------------------

def test_multiple_predictions_are_stored():

    history = PredictionHistory()

    history.add_prediction(
        **create_prediction(120)
    )

    history.add_prediction(
        **create_prediction(110)
    )

    history.add_prediction(
        **create_prediction(100)
    )

    assert history.size() == 3

    predictions = history.get_history()

    assert predictions[0]["predicted_rul"] == 120
    assert predictions[1]["predicted_rul"] == 110
    assert predictions[2]["predicted_rul"] == 100


# ---------------------------------------------------------
# History limit
# ---------------------------------------------------------

def test_history_is_limited():

    history = PredictionHistory(
        max_size=3
    )

    history.add_prediction(
        **create_prediction(120)
    )

    history.add_prediction(
        **create_prediction(110)
    )

    history.add_prediction(
        **create_prediction(100)
    )

    history.add_prediction(
        **create_prediction(90)
    )

    assert history.size() == 3

    predictions = history.get_history()

    assert predictions[0]["predicted_rul"] == 110
    assert predictions[1]["predicted_rul"] == 100
    assert predictions[2]["predicted_rul"] == 90


# ---------------------------------------------------------
# Previous prediction
# ---------------------------------------------------------

def test_previous_prediction_is_available():

    history = PredictionHistory()

    history.add_prediction(
        **create_prediction(120)
    )

    history.add_prediction(
        **create_prediction(110)
    )

    previous = history.get_previous()

    assert previous is not None
    assert previous["predicted_rul"] == 120


# ---------------------------------------------------------
# Latest prediction
# ---------------------------------------------------------

def test_latest_prediction_is_available():

    history = PredictionHistory()

    history.add_prediction(
        **create_prediction(120)
    )

    history.add_prediction(
        **create_prediction(110)
    )

    latest = history.get_latest()

    assert latest is not None
    assert latest["predicted_rul"] == 110


# ---------------------------------------------------------
# Stable trend
# ---------------------------------------------------------

def test_stable_trend():

    history = PredictionHistory()

    history.add_prediction(
        **create_prediction(100)
    )

    history.add_prediction(
        **create_prediction(103)
    )

    assert history.calculate_trend() == "STABLE"


# ---------------------------------------------------------
# Improving trend
# ---------------------------------------------------------

def test_improving_trend():

    history = PredictionHistory()

    history.add_prediction(
        **create_prediction(100)
    )

    history.add_prediction(
        **create_prediction(110)
    )

    assert history.calculate_trend() == "IMPROVING"


# ---------------------------------------------------------
# Degrading trend
# ---------------------------------------------------------

def test_degrading_trend():

    history = PredictionHistory()

    history.add_prediction(
        **create_prediction(110)
    )

    history.add_prediction(
        **create_prediction(100)
    )

    assert history.calculate_trend() == "DEGRADING"


# ---------------------------------------------------------
# Insufficient history
# ---------------------------------------------------------

def test_insufficient_history_returns_stable():

    history = PredictionHistory()

    history.add_prediction(
        **create_prediction(100)
    )

    assert history.calculate_trend() == "STABLE"


# ---------------------------------------------------------
# Trend details
# ---------------------------------------------------------

def test_trend_details():

    history = PredictionHistory()

    history.add_prediction(
        **create_prediction(120)
    )

    history.add_prediction(
        **create_prediction(100)
    )

    details = history.get_trend_details()

    assert details["trend"] == "DEGRADING"
    assert details["previous_rul"] == 120
    assert details["current_rul"] == 100
    assert details["difference"] == -20
    assert details["history_count"] == 2


# ---------------------------------------------------------
# Clear history
# ---------------------------------------------------------

def test_clear_history():

    history = PredictionHistory()

    history.add_prediction(
        **create_prediction(120)
    )

    history.add_prediction(
        **create_prediction(110)
    )

    assert history.size() == 2

    history.clear()

    assert history.size() == 0
    assert history.get_history() == []
    assert history.get_latest() is None


# ---------------------------------------------------------
# Negative RUL
# ---------------------------------------------------------

def test_negative_rul_is_rejected():

    history = PredictionHistory()

    with pytest.raises(ValueError):

        history.add_prediction(
            **create_prediction(-10)
        )


# ---------------------------------------------------------
# Invalid bounds
# ---------------------------------------------------------

def test_invalid_bounds_are_rejected():

    history = PredictionHistory()

    with pytest.raises(ValueError):

        history.add_prediction(
            predicted_rul=100,
            lower_bound=110,
            upper_bound=90,
            risk_level="LOW",
            health_status="GOOD",
        )