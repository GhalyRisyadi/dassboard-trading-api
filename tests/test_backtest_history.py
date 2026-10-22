import asyncio

import httpx2 as httpx

from app.backtest.history import DAY_MS, fetch_history, time_window
from tests.conftest import HOUR_MS, START_MS


def serve(total_candles: int):
    """Binance palsu: `total_candles` candle 1 jam, dengan batas 1000 per permintaan."""
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        requests.append(dict(params))
        start, end, limit = int(params["startTime"]), int(params["endTime"]), int(params["limit"])
        rows = []
        for i in range(total_candles):
            open_time = START_MS + i * HOUR_MS
            if open_time < start or open_time > end:
                continue
            price = str(100 + i)
            rows.append([open_time, price, price, price, price, "1", open_time + HOUR_MS - 1])
            if len(rows) == limit:
                break
        return httpx.Response(200, json=rows)

    return handler, requests


def run(handler, **kwargs):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await fetch_history(client, "BTCUSDT", "1h", **kwargs)

    return asyncio.run(go())


def test_pagination_collects_every_candle_once_in_order():
    handler, requests = serve(2500)
    candles = run(handler, start_ms=START_MS, end_ms=START_MS + 2500 * HOUR_MS)

    assert len(candles) == 2500
    times = [c.open_time for c in candles]
    assert times == sorted(set(times))
    assert times[1] - times[0] == HOUR_MS
    assert len(requests) == 3  # 1000 + 1000 + 500


def test_unfinished_candle_is_dropped():
    handler, _ = serve(2500)
    # `end` jatuh di tengah candle ke-2400, jadi candle itu belum selesai.
    candles = run(handler, start_ms=START_MS, end_ms=START_MS + 2400 * HOUR_MS + 1_800_000)
    assert len(candles) == 2400
    assert candles[-1].open_time == START_MS + 2399 * HOUR_MS


def test_pair_listed_later_returns_only_available_data():
    handler, _ = serve(0)
    assert run(handler, start_ms=START_MS, end_ms=START_MS + 100 * HOUR_MS) == []


def test_http_error_propagates():
    import pytest

    def handler(_request):
        return httpx.Response(429, json={"msg": "Too many requests"})

    with pytest.raises(httpx.HTTPStatusError):
        run(handler, start_ms=START_MS, end_ms=START_MS + HOUR_MS * 10)

def test_time_window_ends_now_by_default():
    now = 1_800_000_000_000
    assert time_window(365, 0, now) == (now - 365 * DAY_MS, now)


def test_time_window_can_shift_into_the_past():
    now = 1_800_000_000_000
    start, end = time_window(365, 365, now)
    assert (start, end) == (now - 730 * DAY_MS, now - 365 * DAY_MS)
    assert end - start == 365 * DAY_MS  # panjang jendela tidak berubah
