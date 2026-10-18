import asyncio

import httpx2 as httpx

from app.services import market_data
from tests.conftest import FLAT, make_klines


def test_fetch_uses_configured_base_url(monkeypatch):
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(200, json=make_klines(FLAT))

    monkeypatch.setattr(market_data, "BINANCE_URL", "https://data-api.binance.vision")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await market_data.fetch_closed_candles(client, "BTCUSDT", "1h", 80)

    candles = asyncio.run(run())

    assert seen[0].startswith("https://data-api.binance.vision/api/v3/klines?")
    assert "symbol=BTCUSDT" in seen[0]
    assert len(candles) == len(FLAT) - 1  # candle berjalan dibuang
