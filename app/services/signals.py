import time

from app.schemas import Signal

MINUTE_MS = 60_000


def get_signals() -> list[Signal]:
    """DATA CONTOH. Belum ada model AI. Nanti fungsi ini diganti dengan
    logika sinyal sungguhan, selama bentuk kembaliannya tetap list[Signal]."""
    now = int(time.time() * 1000)

    signals = [
        Signal(
            id="sample-1",
            symbol="BTCUSDT",
            side="BUY",
            confidence=78,
            timeframe="1h",
            reason="Contoh: harga menembus rata-rata pergerakan dengan volume naik",
            created_at=now - 4 * MINUTE_MS,
        ),
        Signal(
            id="sample-2",
            symbol="ETHUSDT",
            side="HOLD",
            confidence=55,
            timeframe="15m",
            reason="Contoh: harga bergerak menyamping, belum ada arah jelas",
            created_at=now - 18 * MINUTE_MS,
        ),
        Signal(
            id="sample-3",
            symbol="SOLUSDT",
            side="SELL",
            confidence=71,
            timeframe="4h",
            reason="Contoh: momentum melemah setelah kenaikan tajam",
            created_at=now - 47 * MINUTE_MS,
        ),
        Signal(
            id="sample-4",
            symbol="HYPEUSDT",
            side="BUY",
            confidence=81,
            timeframe="5m",
            reason="Contoh: buy lah",
            created_at=now - 50 * MINUTE_MS,
        ),
    ]

    return sorted(signals, key=lambda signal: signal.created_at, reverse=True)