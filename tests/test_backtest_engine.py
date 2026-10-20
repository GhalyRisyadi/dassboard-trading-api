import pytest

from app.backtest.engine import (
    BacktestResult,
    HistoricalCandle,
    Trade,
    max_drawdown,
    run_backtest,
)
from app.services.ema_cross import ema_cross_sides
from tests.conftest import FLAT, HOUR_MS, RISING


def candles_from_closes(closes: list[float]) -> list[HistoricalCandle]:
    """Harga buka tiap candle = harga penutupan candle sebelumnya."""
    return [
        HistoricalCandle(open_time=i * HOUR_MS, open=closes[i - 1] if i else closes[0], close=c)
        for i, c in enumerate(closes)
    ]


def first_index(closes: list[float], side: str) -> int:
    return next(i for i, s in enumerate(ema_cross_sides(closes)) if s == side)


def test_entry_is_next_candle_open_and_return_matches_hand_calculation():
    closes = RISING
    buy = first_index(closes, "BUY")
    result = run_backtest(candles_from_closes(closes), fee_rate=0, slippage=0)

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.open_at_end is True
    # Sinyal di candle `buy`, eksekusi di BUKA candle buy + 1 = penutupan candle `buy`.
    assert trade.entry_price == closes[buy]
    assert result.total_return == pytest.approx(closes[-1] / closes[buy] - 1)


def test_costs_are_applied_on_both_sides():
    closes, fee, slip = RISING, 0.001, 0.0005
    buy = first_index(closes, "BUY")
    result = run_backtest(candles_from_closes(closes), fee_rate=fee, slippage=slip)

    expected = (1 - fee) ** 2 * (closes[-1] * (1 - slip)) / (closes[buy] * (1 + slip)) - 1
    assert result.total_return == pytest.approx(expected)
    assert result.trades[0].entry_price == pytest.approx(closes[buy] * (1 + slip))


def test_sell_closes_position_at_next_candle_open():
    closes = RISING + [RISING[-1] - 3 * k for k in range(1, 61)]
    sell = first_index(closes, "SELL")
    candles = candles_from_closes(closes)
    result = run_backtest(candles, fee_rate=0, slippage=0)

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.open_at_end is False
    assert trade.exit_price == candles[sell + 1].open
    assert trade.exit_time == candles[sell + 1].open_time
    assert result.total_return == pytest.approx(trade.net_return)


def test_costs_are_applied_on_a_regular_sell_exit():
    closes, fee, slip = RISING + [RISING[-1] - 3 * k for k in range(1, 61)], 0.001, 0.0005
    buy, sell = first_index(closes, "BUY"), first_index(closes, "SELL")
    candles = candles_from_closes(closes)
    result = run_backtest(candles, fee_rate=fee, slippage=slip)

    entry = candles[buy + 1].open * (1 + slip)
    exit_ = candles[sell + 1].open * (1 - slip)
    expected = (1 - fee) ** 2 * exit_ / entry - 1

    assert result.trades[0].open_at_end is False
    assert result.trades[0].net_return == pytest.approx(expected)
    assert result.total_return == pytest.approx(expected)


def test_entry_does_not_depend_on_the_execution_candles_own_close():
    closes = RISING
    buy = first_index(closes, "BUY")

    normal = run_backtest(candles_from_closes(closes), fee_rate=0, slippage=0)

    shocked = candles_from_closes(closes)
    shocked[buy + 1] = HistoricalCandle(
        shocked[buy + 1].open_time, shocked[buy + 1].open, close=closes[buy + 1] * 10
    )
    after = run_backtest(shocked, fee_rate=0, slippage=0)

    assert after.trades[0].entry_price == normal.trades[0].entry_price


def test_flat_market_makes_no_trades():
    result = run_backtest(candles_from_closes(FLAT), fee_rate=0, slippage=0)
    assert result.trades == []
    assert result.total_return == 0
    assert result.buy_hold_return == 0
    assert result.exposure == 0
    assert result.win_rate is None


def test_costs_make_a_flat_market_lose_money_for_buy_and_hold():
    result = run_backtest(candles_from_closes(FLAT), fee_rate=0.001, slippage=0.0005)
    assert result.buy_hold_return < 0


def test_exposure_counts_candles_in_position():
    closes = RISING
    result = run_backtest(candles_from_closes(closes), fee_rate=0, slippage=0)
    buy = first_index(closes, "BUY")
    start = next(i for i, s in enumerate(ema_cross_sides(closes)) if s is not None) + 1
    in_position = len(closes) - (buy + 1)
    assert result.exposure == pytest.approx(in_position / (len(closes) - start))


def test_too_little_data_raises():
    with pytest.raises(ValueError):
        run_backtest(candles_from_closes([100.0] * 10))


def test_max_drawdown():
    assert max_drawdown([1, 1.2, 0.9, 1.1]) == pytest.approx(0.25)
    assert max_drawdown([1, 2, 3]) == 0


def make_result(returns: list[float]) -> BacktestResult:
    trades = [Trade(0, 1, 1.0, 1.0, r, open_at_end=False) for r in returns]
    return BacktestResult(
        candles=10, start_time=0, end_time=1, trades=trades, total_return=0,
        buy_hold_return=0, max_drawdown=0, buy_hold_max_drawdown=0, exposure=0,
    )  # fmt: skip


def test_trade_statistics():
    result = make_result([0.10, -0.05, 0.02])
    assert result.win_rate == pytest.approx(2 / 3)
    assert result.average_win == pytest.approx(0.06)
    assert result.average_loss == pytest.approx(-0.05)
    assert result.profit_factor == pytest.approx(0.12 / 0.05)


def test_profit_factor_is_none_without_losses():
    assert make_result([0.1, 0.2]).profit_factor is None
