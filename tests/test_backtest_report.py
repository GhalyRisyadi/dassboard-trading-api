from app.backtest.engine import BacktestResult
from app.backtest.report import format_result


def make_result(trades: int) -> BacktestResult:
    return BacktestResult(
        candles=100, start_time=0, end_time=86_400_000 * 10, trades=[], total_return=0.0,
        buy_hold_return=-0.02, max_drawdown=0.0, buy_hold_max_drawdown=0.0, exposure=0.0,
    )  # fmt: skip


def test_zero_drawdown_is_not_printed_as_negative_zero():
    text = format_result("BTCUSDT", "1h", make_result(0), requested_days=10)
    assert "-0.0%" not in text
    assert "+0.0%" in text


def test_few_trades_and_short_history_are_flagged():
    text = format_result("NEWUSDT", "1h", make_result(0), requested_days=365)
    assert "terlalu sedikit untuk menarik kesimpulan" in text
    assert "pair baru listing" in text
