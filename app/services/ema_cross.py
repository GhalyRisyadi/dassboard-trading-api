from dataclasses import dataclass

from app.schemas import SignalSide
from app.services.indicators import ema


@dataclass(frozen=True)
class Evaluation:
    side: SignalSide
    fast: float
    slow: float


def _classify(previous_gap: float, gap: float) -> SignalSide:
    """Tentukan sinyal dari selisih EMA cepat dan EMA lambat pada dua candle berurutan."""
    if previous_gap <= 0 < gap:
        return "BUY"
    if previous_gap >= 0 > gap:
        return "SELL"
    return "HOLD"


def _check_periods(fast_period: int, slow_period: int) -> None:
    if fast_period >= slow_period:
        raise ValueError("fast_period harus lebih kecil dari slow_period")


def evaluate_ema_cross(
    closes: list[float], fast_period: int = 12, slow_period: int = 26
) -> Evaluation | None:
    """Strategi persilangan EMA pada harga penutupan candle yang SUDAH selesai.

    BUY  : EMA cepat memotong ke atas EMA lambat pada candle terakhir.
    SELL : EMA cepat memotong ke bawah EMA lambat pada candle terakhir.
    HOLD : tidak ada persilangan baru.

    Mengembalikan None kalau data belum cukup untuk membandingkan dua titik.
    """
    _check_periods(fast_period, slow_period)

    fast_values = ema(closes, fast_period)
    slow_values = ema(closes, slow_period)
    if len(slow_values) < 2:
        return None

    # EMA cepat lebih panjang daripada EMA lambat; ambil bagian ujung yang sejajar.
    fast_values = fast_values[-len(slow_values) :]

    previous_gap = fast_values[-2] - slow_values[-2]
    gap = fast_values[-1] - slow_values[-1]

    return Evaluation(
        side=_classify(previous_gap, gap), fast=fast_values[-1], slow=slow_values[-1]
    )


def ema_cross_sides(
    closes: list[float], fast_period: int = 12, slow_period: int = 26
) -> list[SignalSide | None]:
    """Sinyal untuk SETIAP candle, dihitung sekali jalan (dipakai backtest).

    Elemen ke-i sama persis dengan `evaluate_ema_cross(closes[: i + 1])`, karena EMA di
    candle ke-i hanya bergantung pada candle ke-0 sampai ke-i. Ada tes yang menjaga
    kesamaan itu. None berarti data belum cukup.
    """
    _check_periods(fast_period, slow_period)

    sides: list[SignalSide | None] = [None] * len(closes)
    fast_values = ema(closes, fast_period)
    slow_values = ema(closes, slow_period)
    if len(slow_values) < 2:
        return sides

    first_index = slow_period - 1  # posisi slow_values[0] di dalam `closes`
    fast_aligned = fast_values[slow_period - fast_period :]
    for j in range(1, len(slow_values)):
        previous_gap = fast_aligned[j - 1] - slow_values[j - 1]
        gap = fast_aligned[j] - slow_values[j]
        sides[first_index + j] = _classify(previous_gap, gap)
    return sides
