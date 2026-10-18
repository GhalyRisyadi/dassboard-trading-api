import pytest

from app.services.ema_cross import evaluate_ema_cross
from app.services.indicators import ema
from tests.conftest import FALLING, FLAT, RISING


def test_ema_matches_hand_calculation():
    # SMA awal = (10+11+12)/3 = 11, k = 0.5 -> 13*0.5 + 11*0.5 = 12 -> 14*0.5 + 12*0.5 = 13
    assert ema([10, 11, 12, 13, 14], 3) == [11, 12, 13]


def test_ema_returns_empty_when_data_too_short():
    assert ema([1, 2], 3) == []


def test_ema_rejects_invalid_period():
    with pytest.raises(ValueError):
        ema([1, 2, 3], 0)


def test_buy_on_upward_cross():
    result = evaluate_ema_cross(RISING[:68])
    assert result is not None and result.side == "BUY"
    assert result.fast > result.slow


def test_hold_one_candle_before_cross():
    result = evaluate_ema_cross(RISING[:67])
    assert result is not None and result.side == "HOLD"


def test_hold_after_cross_has_passed():
    result = evaluate_ema_cross(RISING[:69])
    assert result is not None and result.side == "HOLD"


def test_sell_on_downward_cross():
    result = evaluate_ema_cross(FALLING[:68])
    assert result is not None and result.side == "SELL"
    assert result.fast < result.slow


def test_flat_prices_give_hold():
    result = evaluate_ema_cross(FLAT)
    assert result is not None and result.side == "HOLD"


def test_none_when_not_enough_candles():
    assert evaluate_ema_cross([100.0] * 26) is None
    assert evaluate_ema_cross([100.0] * 27) is not None


def test_rejects_fast_period_not_smaller_than_slow():
    with pytest.raises(ValueError):
        evaluate_ema_cross(FLAT, fast_period=26, slow_period=26)
