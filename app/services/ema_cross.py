from dataclasses import dataclass

from app.schemas import SignalSide
from app.services.indicators import ema


@dataclass(frozen=True)
class Evaluation:
    side: SignalSide
    fast: float
    slow: float


def evaluate_ema_cross(
    closes: list[float], fast_period: int = 12, slow_period: int = 26
) -> Evaluation | None:
    """Strategi persilangan EMA pada harga penutupan candle yang SUDAH selesai.

    BUY  : EMA cepat memotong ke atas EMA lambat pada candle terakhir.
    SELL : EMA cepat memotong ke bawah EMA lambat pada candle terakhir.
    HOLD : tidak ada persilangan baru.

    Mengembalikan None kalau data belum cukup untuk membandingkan dua titik.
    """
    if fast_period >= slow_period:
        raise ValueError("fast_period harus lebih kecil dari slow_period")

    fast_values = ema(closes, fast_period)
    slow_values = ema(closes, slow_period)
    if len(slow_values) < 2:
        return None

    # EMA cepat lebih panjang daripada EMA lambat; ambil bagian ujung yang sejajar.
    fast_values = fast_values[-len(slow_values) :]

    previous_gap = fast_values[-2] - slow_values[-2]
    gap = fast_values[-1] - slow_values[-1]

    if previous_gap <= 0 < gap:
        side: SignalSide = "BUY"
    elif previous_gap >= 0 > gap:
        side = "SELL"
    else:
        side = "HOLD"

    return Evaluation(side=side, fast=fast_values[-1], slow=slow_values[-1])
