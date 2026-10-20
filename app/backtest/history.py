import httpx2 as httpx

from app.backtest.engine import HistoricalCandle
from app.services import market_data

INTERVAL_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}
PAGE_LIMIT = 1000  # batas candle per permintaan di Binance
DAY_MS = 86_400_000


async def fetch_history(
    client: httpx.AsyncClient, symbol: str, interval: str, start_ms: int, end_ms: int
) -> list[HistoricalCandle]:
    """Ambil candle historis yang SUDAH selesai, dari `start_ms` sampai `end_ms`.

    Binance membatasi 1000 candle per permintaan, jadi diambil halaman demi halaman.
    Pair yang baru listing hanya mengembalikan data sejak tanggal listing-nya.
    """
    step = INTERVAL_MS[interval]
    candles: list[HistoricalCandle] = []
    cursor = start_ms

    while cursor < end_ms:
        response = await client.get(
            f"{market_data.BINANCE_URL}/api/v3/klines",
            params={
                "symbol": symbol,
                "interval": interval,
                "startTime": cursor,
                "endTime": end_ms,
                "limit": PAGE_LIMIT,
            },
        )
        response.raise_for_status()
        rows = response.json()
        if not rows:
            break

        for row in rows:
            if int(row[6]) > end_ms:  # candle yang belum selesai
                continue
            candles.append(
                HistoricalCandle(open_time=int(row[0]), open=float(row[1]), close=float(row[4]))
            )

        if len(rows) < PAGE_LIMIT:
            break
        cursor = int(rows[-1][0]) + step

    return candles
