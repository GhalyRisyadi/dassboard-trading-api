from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

EXPECTED_KEYS = {"id", "symbol", "side", "confidence", "timeframe", "reason", "createdAt"}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_signals_shape_matches_frontend_contract():
    response = client.get("/signals")
    assert response.status_code == 200

    signals = response.json()
    assert len(signals) == 3
    for signal in signals:
        assert set(signal.keys()) == EXPECTED_KEYS
        assert signal["side"] in {"BUY", "SELL", "HOLD"}
        assert 0 <= signal["confidence"] <= 100
        assert signal["timeframe"] in {"1m", "5m", "15m", "1h", "4h", "1d"}


def test_created_at_is_epoch_milliseconds():
    # Epoch dalam milidetik untuk tahun 2020 ke atas selalu di atas 1.5 triliun.
    for signal in client.get("/signals").json():
        assert isinstance(signal["createdAt"], int)
        assert signal["createdAt"] > 1_500_000_000_000


def test_cors_allows_frontend_dev_origin():
    response = client.get("/signals", headers={"Origin": "http://localhost:5173"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_rejects_unknown_origin():
    response = client.get("/signals", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in response.headers