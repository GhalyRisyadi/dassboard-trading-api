import httpx2 as httpx
from fastapi.testclient import TestClient

from app.main import app
from app.services.signals import WATCHLIST
from tests.conftest import FALLING, FLAT, RISING, close_time_of, make_klines

client = TestClient(app)

EXPECTED_KEYS = {"id", "symbol", "side", "confidence", "timeframe", "reason", "createdAt"}
OPEN_CANDLE = 99_999  # harga ekstrem di candle berjalan; tidak boleh memengaruhi sinyal


def all_flat(_symbol: str) -> httpx.Response:
    return httpx.Response(200, json=make_klines(FLAT))


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_signals_shape_matches_frontend_contract(use_binance):
    use_binance(all_flat)
    response = client.get("/signals")
    assert response.status_code == 200

    signals = response.json()
    assert len(signals) == len(WATCHLIST)
    for signal in signals:
        assert set(signal.keys()) == EXPECTED_KEYS
        assert signal["side"] in {"BUY", "SELL", "HOLD"}
        assert signal["confidence"] is None
        assert signal["timeframe"] in {"1m", "5m", "15m", "1h", "4h", "1d"}


def test_created_at_is_close_time_of_last_closed_candle(use_binance):
    # 80 candle dari Binance (indeks 0-79): indeks 79 sedang berjalan, jadi yang terakhir
    # selesai adalah indeks 78.
    use_binance(all_flat)
    for signal in client.get("/signals").json():
        assert isinstance(signal["createdAt"], int)
        assert signal["createdAt"] == close_time_of(78)


def test_buy_and_sell_detected_per_symbol(use_binance):
    series = {"BTCUSDT": RISING[:68], "ETHUSDT": FALLING[:68]}

    def handler(symbol: str) -> httpx.Response:
        closes = series.get(symbol, FLAT)
        return httpx.Response(200, json=make_klines(closes + [OPEN_CANDLE]))

    use_binance(handler)
    by_symbol = {s["symbol"]: s for s in client.get("/signals").json()}

    assert by_symbol["BTCUSDT"]["side"] == "BUY"
    assert by_symbol["ETHUSDT"]["side"] == "SELL"
    assert by_symbol["SOLUSDT"]["side"] == "HOLD"
    assert "memotong ke atas" in by_symbol["BTCUSDT"]["reason"]
    assert "memotong ke bawah" in by_symbol["ETHUSDT"]["reason"]


def test_open_candle_never_affects_signal(use_binance):
    # RISING[:67] adalah HOLD. Candle berjalan dengan harga ekstrem tidak boleh mengubahnya.
    def handler(symbol: str) -> httpx.Response:
        return httpx.Response(200, json=make_klines(RISING[:67] + [OPEN_CANDLE]))

    use_binance(handler)
    assert {s["side"] for s in client.get("/signals").json()} == {"HOLD"}


def test_signals_sorted_newest_first_then_actionable_first(use_binance):
    def handler(symbol: str) -> httpx.Response:
        if symbol == "BTCUSDT":  # candle terakhir lebih lama -> harus paling bawah
            return httpx.Response(200, json=make_klines(RISING[:60] + [0]))
        # Semua simbol lain sama-sama 68 candle selesai, jadi waktunya sama dengan SOLUSDT.
        closes = RISING[:68] if symbol == "SOLUSDT" else FLAT[:68]
        return httpx.Response(200, json=make_klines(closes + [OPEN_CANDLE]))

    use_binance(handler)
    signals = client.get("/signals").json()

    created = [s["createdAt"] for s in signals]
    assert created == sorted(created, reverse=True)
    assert signals[0]["symbol"] == "SOLUSDT" and signals[0]["side"] == "BUY"
    assert signals[-1]["symbol"] == "BTCUSDT"


def test_failed_symbol_is_skipped_not_fatal(use_binance):
    def handler(symbol: str) -> httpx.Response:
        if symbol == "HYPEUSDT":
            return httpx.Response(400, json={"code": -1121, "msg": "Invalid symbol."})
        return all_flat(symbol)

    use_binance(handler)
    response = client.get("/signals")
    assert response.status_code == 200
    symbols = {s["symbol"] for s in response.json()}
    assert "HYPEUSDT" not in symbols
    assert len(symbols) == len(WATCHLIST) - 1


def test_all_symbols_failing_returns_502_with_upstream_status_in_logs(use_binance, caplog):
    use_binance(lambda _symbol: httpx.Response(429, json={"msg": "Too many requests"}))
    response = client.get("/signals")

    assert response.status_code == 502
    assert "Binance" in response.json()["detail"]
    assert "category=http_status" in caplog.text
    assert "status_code=429" in caplog.text
    assert "Too many requests" not in response.json()["detail"]


def test_connection_failure_is_classified_in_logs_not_api_response(use_binance, caplog):
    def fail_connection(_symbol: str) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    use_binance(fail_connection)
    response = client.get("/signals")

    assert response.status_code == 502
    assert response.json()["detail"] == "Gagal mengambil data harga dari Binance"
    assert "category=connection_error" in caplog.text
    assert "connection refused" not in response.json()["detail"]


def test_symbol_with_too_few_candles_is_skipped(use_binance):
    def handler(symbol: str) -> httpx.Response:
        closes = [100.0] * 10 if symbol == "SUIUSDT" else FLAT
        return httpx.Response(200, json=make_klines(closes))

    use_binance(handler)
    symbols = {s["symbol"] for s in client.get("/signals").json()}
    assert "SUIUSDT" not in symbols


def test_cors_allows_frontend_dev_origin(use_binance):
    use_binance(all_flat)
    response = client.get("/signals", headers={"Origin": "http://localhost:5173"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_rejects_unknown_origin(use_binance):
    use_binance(all_flat)
    response = client.get("/signals", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in response.headers


def test_hold_reason_describes_trend_correctly(use_binance):
    rising_trend = RISING[:67]  # HOLD, EMA cepat sudah di bawah EMA lambat setelah turun
    series = {"BTCUSDT": FLAT, "ETHUSDT": rising_trend}

    def handler(symbol: str) -> httpx.Response:
        closes = series.get(symbol, FLAT)
        return httpx.Response(200, json=make_klines(closes + [OPEN_CANDLE]))

    use_binance(handler)
    by_symbol = {s["symbol"]: s for s in client.get("/signals").json()}
    assert "tren datar" in by_symbol["BTCUSDT"]["reason"]
    assert "tren turun" in by_symbol["ETHUSDT"]["reason"]


def test_error_message_is_logged_but_never_returned(use_binance, caplog):
    def fail_tls(_symbol: str) -> httpx.Response:
        raise httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")

    use_binance(fail_tls)
    response = client.get("/signals")

    assert response.status_code == 502
    assert "CERTIFICATE_VERIFY_FAILED" in caplog.text
    assert "CERTIFICATE_VERIFY_FAILED" not in response.text
