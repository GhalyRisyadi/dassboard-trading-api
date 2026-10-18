import asyncio
import logging
import math

import httpx2 as httpx

from app.schemas import ChartInterval, Signal
from app.services.ema_cross import Evaluation, evaluate_ema_cross
from app.services.market_data import MarketDataUnavailable, fetch_closed_candles

logger = logging.getLogger(__name__)

# Sama dengan WATCHLIST di frontend (src/services/market.ts).
WATCHLIST = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "SUIUSDT", "HYPEUSDT"]
TIMEFRAME: ChartInterval = "1h"
FAST_PERIOD = 12
SLOW_PERIOD = 26
CANDLE_LIMIT = 200


def _format_price(value: float) -> str:
    return f"{value:,.2f}" if value >= 100 else f"{value:.4f}"


def _reason(evaluation: Evaluation) -> str:
    numbers = f"EMA {FAST_PERIOD} = {_format_price(evaluation.fast)}, EMA {SLOW_PERIOD} = {_format_price(evaluation.slow)}"
    if evaluation.side == "BUY":
        return f"EMA {FAST_PERIOD} memotong ke atas EMA {SLOW_PERIOD} pada candle terakhir ({numbers})"
    if evaluation.side == "SELL":
        return f"EMA {FAST_PERIOD} memotong ke bawah EMA {SLOW_PERIOD} pada candle terakhir ({numbers})"
    if math.isclose(evaluation.fast, evaluation.slow, rel_tol=1e-9):
        trend = "datar"
    elif evaluation.fast > evaluation.slow:
        trend = "naik"
    else:
        trend = "turun"
    return f"Belum ada persilangan baru, tren {trend} ({numbers})"


def _failure_details(error: Exception) -> tuple[str, int | None]:
    if isinstance(error, httpx.HTTPStatusError):
        return "http_status", error.response.status_code
    if isinstance(error, httpx.TimeoutException):
        return "timeout", None
    if isinstance(error, httpx.RequestError):
        return "connection_error", None
    return "data_or_processing_error", None


async def _signal_for(client: httpx.AsyncClient, symbol: str) -> Signal | None:
    candles = await fetch_closed_candles(client, symbol, TIMEFRAME, CANDLE_LIMIT)
    evaluation = evaluate_ema_cross([c.close for c in candles], FAST_PERIOD, SLOW_PERIOD)
    if evaluation is None:
        return None

    last = candles[-1]
    return Signal(
        id=f"{symbol}-{TIMEFRAME}-{last.close_time}",
        symbol=symbol,
        side=evaluation.side,
        # Strategi berbasis aturan tidak menghasilkan probabilitas, jadi sengaja kosong.
        confidence=None,
        timeframe=TIMEFRAME,
        reason=_reason(evaluation),
        created_at=last.close_time,
    )


async def get_signals(client: httpx.AsyncClient) -> list[Signal]:
    results = await asyncio.gather(
        *(_signal_for(client, symbol) for symbol in WATCHLIST), return_exceptions=True
    )

    signals: list[Signal] = []
    failures = 0
    for symbol, result in zip(WATCHLIST, results):
        if isinstance(result, Exception):
            failures += 1
            category, status_code = _failure_details(result)
            logger.warning(
                "Binance market-data request failed symbol=%s category=%s status_code=%s error_type=%s",
                symbol,
                category,
                status_code,
                type(result).__name__,
            )
        elif isinstance(result, BaseException):
            raise result
        elif result is not None:
            signals.append(result)

    if failures == len(WATCHLIST):
        raise MarketDataUnavailable("Gagal mengambil data harga dari Binance")

    # Terbaru di atas; pada waktu yang sama, BUY dan SELL di atas HOLD.
    return sorted(signals, key=lambda signal: (-signal.created_at, signal.side == "HOLD"))