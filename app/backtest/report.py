from datetime import datetime, timezone

from app.backtest.engine import BacktestResult
from app.backtest.history import DAY_MS

MIN_TRADES_FOR_CONCLUSION = 30


def _date(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:+.1f}%"


def _ratio(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}"


def format_result(
    symbol: str, interval: str, result: BacktestResult, requested_days: int
) -> str:
    covered_days = (result.end_time - result.start_time) / DAY_MS
    wins = sum(1 for t in result.trades if t.net_return > 0)
    win_rate = "n/a" if result.win_rate is None else f"{result.win_rate * 100:.1f}%"

    lines = [
        f"{symbol} {interval}  {_date(result.start_time)} sampai {_date(result.end_time)}"
        f"  ({result.candles:,} candle, {covered_days:.0f} hari)",
        f"  Transaksi              : {len(result.trades)} (menang {wins}, {win_rate})",
        f"  Return strategi        : {_pct(result.total_return)}",
        f"  Return tahan terus     : {_pct(result.buy_hold_return)}",
        f"  Penurunan terbesar     : {_pct(-result.max_drawdown or 0.0)} "
        f"(tahan terus: {_pct(-result.buy_hold_max_drawdown or 0.0)})",
        f"  Waktu memegang posisi  : {result.exposure * 100:.1f}%",
        f"  Rata-rata menang/kalah : {_pct(result.average_win)} / {_pct(result.average_loss)}",
        f"  Profit factor          : {_ratio(result.profit_factor)}",
    ]

    if len(result.trades) < MIN_TRADES_FOR_CONCLUSION:
        lines.append(
            f"  ! Hanya {len(result.trades)} transaksi: terlalu sedikit untuk menarik "
            f"kesimpulan (minimal sekitar {MIN_TRADES_FOR_CONCLUSION})."
        )
    if covered_days < requested_days * 0.9:
        lines.append(
            f"  ! Data hanya mencakup {covered_days:.0f} dari {requested_days} hari yang "
            "diminta (pair baru listing)."
        )
    if any(t.open_at_end for t in result.trades):
        lines.append("  ! Satu posisi masih terbuka di akhir data dan ditutup paksa.")
    return "\n".join(lines)


def format_trades(result: BacktestResult) -> str:
    lines = ["  Daftar transaksi:"]
    for trade in result.trades:
        flag = " (ditutup paksa)" if trade.open_at_end else ""
        lines.append(
            f"    {_date(trade.entry_time)} -> {_date(trade.exit_time)}  "
            f"{trade.entry_price:,.4f} -> {trade.exit_price:,.4f}  "
            f"{_pct(trade.net_return)}{flag}"
        )
    return "\n".join(lines)
