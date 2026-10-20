from dataclasses import dataclass

from app.services.ema_cross import ema_cross_sides


@dataclass(frozen=True)
class HistoricalCandle:
    open_time: int  # milidetik sejak epoch
    open: float
    close: float


@dataclass(frozen=True)
class Trade:
    entry_time: int
    exit_time: int
    entry_price: float
    exit_price: float
    # Hasil bersih setelah biaya, sebagai pecahan (0.05 = +5%).
    net_return: float
    # True kalau posisi masih terbuka di akhir data dan ditutup paksa di harga penutupan terakhir.
    open_at_end: bool


@dataclass(frozen=True)
class BacktestResult:
    candles: int
    start_time: int
    end_time: int
    trades: list[Trade]
    total_return: float
    buy_hold_return: float
    max_drawdown: float
    buy_hold_max_drawdown: float
    exposure: float  # porsi candle saat memegang posisi, 0 sampai 1

    @property
    def win_rate(self) -> float | None:
        if not self.trades:
            return None
        return sum(1 for t in self.trades if t.net_return > 0) / len(self.trades)

    @property
    def profit_factor(self) -> float | None:
        """Total keuntungan dibagi total kerugian. None kalau tidak ada kerugian sama sekali."""
        gains = sum(t.net_return for t in self.trades if t.net_return > 0)
        losses = -sum(t.net_return for t in self.trades if t.net_return < 0)
        return gains / losses if losses > 0 else None

    @property
    def average_win(self) -> float | None:
        wins = [t.net_return for t in self.trades if t.net_return > 0]
        return sum(wins) / len(wins) if wins else None

    @property
    def average_loss(self) -> float | None:
        losses = [t.net_return for t in self.trades if t.net_return < 0]
        return sum(losses) / len(losses) if losses else None


def max_drawdown(equity_curve: list[float]) -> float:
    """Penurunan terbesar dari puncak ke lembah, sebagai pecahan positif (0.25 = turun 25%)."""
    peak = float("-inf")
    worst = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        worst = max(worst, (peak - value) / peak)
    return worst


def run_backtest(
    candles: list[HistoricalCandle],
    fast_period: int = 12,
    slow_period: int = 26,
    fee_rate: float = 0.001,
    slippage: float = 0.0005,
) -> BacktestResult:
    """Simulasikan strategi persilangan EMA pada data historis.

    Aturan simulasi:
    - Hanya posisi beli (spot, tanpa leverage dan tanpa short). BUY = masuk, SELL = keluar.
    - Sinyal dihitung dari harga penutupan candle ke-i, tapi eksekusi di harga BUKA candle
      ke-(i + 1). Memakai harga penutupan yang sama untuk menghitung sinyal dan bertransaksi
      akan mengintip masa depan.
    - Biaya per transaksi: `fee_rate` (komisi) dan `slippage` (selisih harga eksekusi yang
      buruk), keduanya berlaku di sisi masuk dan sisi keluar.
    - Seluruh modal masuk tiap transaksi. Posisi yang masih terbuka di akhir data ditutup
      paksa di harga penutupan terakhir.
    - Pembanding "tahan terus" mulai dari candle eksekusi pertama strategi dan membayar biaya
      yang sama satu kali masuk dan satu kali keluar.
    """
    closes = [c.close for c in candles]
    sides = ema_cross_sides(closes, fast_period, slow_period)

    first_signal = next((i for i, side in enumerate(sides) if side is not None), None)
    if first_signal is None or first_signal + 1 >= len(candles):
        raise ValueError("Data terlalu sedikit untuk backtest")
    start = first_signal + 1  # candle eksekusi pertama

    cash = 1.0
    units = 0.0
    entry_equity = 0.0
    entry_price = 0.0
    entry_time = 0
    trades: list[Trade] = []
    equity_curve: list[float] = []
    candles_in_market = 0

    for i in range(start, len(candles)):
        candle = candles[i]
        signal = sides[i - 1]  # sinyal dari candle sebelumnya, dieksekusi di buka candle ini

        if signal == "BUY" and units == 0.0:
            entry_price = candle.open * (1 + slippage)
            entry_equity = cash
            units = cash * (1 - fee_rate) / entry_price
            cash = 0.0
            entry_time = candle.open_time
        elif signal == "SELL" and units > 0.0:
            exit_price = candle.open * (1 - slippage)
            cash = units * exit_price * (1 - fee_rate)
            trades.append(
                Trade(entry_time, candle.open_time, entry_price, exit_price,
                      cash / entry_equity - 1, open_at_end=False)
            )  # fmt: skip
            units = 0.0

        if units > 0.0:
            candles_in_market += 1
        equity_curve.append(cash + units * candle.close)

    if units > 0.0:
        last = candles[-1]
        exit_price = last.close * (1 - slippage)
        cash = units * exit_price * (1 - fee_rate)
        trades.append(
            Trade(entry_time, last.open_time, entry_price, exit_price,
                  cash / entry_equity - 1, open_at_end=True)
        )  # fmt: skip
        equity_curve[-1] = cash

    # Pembanding: beli di buka candle eksekusi pertama, tahan sampai akhir.
    hold_units = (1 - fee_rate) / (candles[start].open * (1 + slippage))
    hold_curve = [hold_units * candles[i].close for i in range(start, len(candles))]
    hold_final = hold_units * candles[-1].close * (1 - slippage) * (1 - fee_rate)
    hold_curve[-1] = hold_final

    return BacktestResult(
        candles=len(candles) - start,
        start_time=candles[start].open_time,
        end_time=candles[-1].open_time,
        trades=trades,
        total_return=equity_curve[-1] - 1,
        buy_hold_return=hold_final - 1,
        max_drawdown=max_drawdown(equity_curve),
        buy_hold_max_drawdown=max_drawdown(hold_curve),
        exposure=candles_in_market / len(equity_curve),
    )
