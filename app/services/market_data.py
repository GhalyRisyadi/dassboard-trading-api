from dataclasses import dataclass

import httpx2 as httpx

BINANCE_URL = "https://api.binance.com"


class MarketDataUnavailable(Exception):
    """Data harga tidak bisa diambil dari bursa."""


@dataclass(frozen=True)
class Candle:
    close_time: int  # milidetik sejak epoch
    close: float


async def fetch_closed_candles(
    client: httpx.AsyncClient, symbol: str, interval: str, limit: int = 200
) -> list[Candle]:
    """Ambil candle dari Binance, hanya yang sudah selesai.

    Candle terakhir dari Binance selalu candle yang sedang berjalan dan harganya masih
    berubah. Memakainya membuat sinyal bisa muncul lalu hilang sebelum candle ditutup,
    jadi dibuang di sini.
    """
    response = await client.get(
        f"{BINANCE_URL}/api/v3/klines",
        params={"symbol": symbol, "interval": interval, "limit": limit},
    )
    response.raise_for_status()

    # Tiap baris: [openTime, open, high, low, close, volume, closeTime, ...]
    rows = response.json()
    candles = [Candle(close_time=int(row[6]), close=float(row[4])) for row in rows]
    return candles[:-1]