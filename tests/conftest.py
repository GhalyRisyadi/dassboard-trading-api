import httpx2 as httpx
import pytest

from app.main import app, get_http_client

START_MS = 1_700_000_000_000
HOUR_MS = 3_600_000

# Deret harga sintetis: turun 60 candle lalu naik tajam. EMA 12 memotong ke atas
# EMA 26 tepat pada candle ke-68, dan tidak ada persilangan lain.
RISING = [200 - i for i in range(60)] + [140 + 4 * i for i in range(1, 40)]
# Cermin dari RISING (naik lalu turun): persilangan ke bawah pada candle ke-68.
FALLING = [400 - c for c in RISING]
FLAT = [100.0] * 80


def make_klines(closes: list[float]) -> list[list]:
    """Meniru respons /api/v3/klines Binance. Elemen terakhir = candle berjalan."""
    rows = []
    for i, close in enumerate(closes):
        open_time = START_MS + i * HOUR_MS
        rows.append(
            [open_time, str(close), str(close), str(close), str(close), "1",
             open_time + HOUR_MS - 1, "1", 1, "0", "0", "0"]
        )  # fmt: skip
    return rows


def close_time_of(index: int) -> int:
    return START_MS + index * HOUR_MS + HOUR_MS - 1


@pytest.fixture
def use_binance():
    """Pasang Binance palsu: `handler(symbol) -> httpx.Response`."""

    def install(handler):
        def transport_handler(request: httpx.Request) -> httpx.Response:
            return handler(request.url.params["symbol"])

        async def fake_client():
            async with httpx.AsyncClient(transport=httpx.MockTransport(transport_handler)) as c:
                yield c

        app.dependency_overrides[get_http_client] = fake_client

    yield install
    app.dependency_overrides.clear()
