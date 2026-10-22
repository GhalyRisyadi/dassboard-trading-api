"""Backtest strategi persilangan EMA pada data historis Binance.

Contoh:
    python -m app.backtest --symbols BTCUSDT ETHUSDT --interval 1h --days 365
"""

import argparse
import asyncio
import time

import httpx2 as httpx

from app.backtest.engine import HistoricalCandle, run_backtest
from app.backtest.history import INTERVAL_MS, fetch_history, time_window
from app.backtest.report import format_result, format_trades
from app.services.signals import WATCHLIST


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--symbols", nargs="+", default=WATCHLIST, help="pair yang diuji")
    parser.add_argument("--interval", choices=sorted(INTERVAL_MS), default="1h")
    parser.add_argument("--days", type=int, default=365, help="panjang data historis (hari)")
    parser.add_argument(
        "--until-days-ago",
        type=int,
        default=0,
        help="geser akhir jendela ke masa lalu (hari), untuk menguji periode yang lebih lama",
    )
    parser.add_argument("--fast", type=int, default=12, help="periode EMA cepat")
    parser.add_argument("--slow", type=int, default=26, help="periode EMA lambat")
    parser.add_argument("--fee-pct", type=float, default=0.1, help="komisi per sisi, dalam persen")
    parser.add_argument(
        "--slippage-pct", type=float, default=0.05, help="slippage per sisi, dalam persen"
    )
    parser.add_argument("--trades", action="store_true", help="tampilkan daftar transaksi")
    args = parser.parse_args()
    if args.until_days_ago < 0:
        parser.error("--until-days-ago tidak boleh negatif")
    return args


async def run(args: argparse.Namespace) -> int:
    start_ms, end_ms = time_window(args.days, args.until_days_ago, int(time.time() * 1000))

    print(
        f"Backtest EMA {args.fast}/{args.slow} | komisi {args.fee_pct}% dan slippage "
        f"{args.slippage_pct}% per sisi | hanya posisi beli, eksekusi di harga buka "
        "candle berikutnya\n"
    )

    failed = 0
    async with httpx.AsyncClient(timeout=20) as client:
        for symbol in args.symbols:
            candles: list[HistoricalCandle] = []
            try:
                candles = await fetch_history(client, symbol, args.interval, start_ms, end_ms)
                result = run_backtest(
                    candles,
                    fast_period=args.fast,
                    slow_period=args.slow,
                    fee_rate=args.fee_pct / 100,
                    slippage=args.slippage_pct / 100,
                )
            except ValueError:
                print(f"{symbol}: data tidak cukup untuk backtest ({len(candles)} candle)\n")
                failed += 1
                continue
            except Exception as error:  # noqa: BLE001 - tampilkan sebab apa pun ke pengguna
                print(f"{symbol}: gagal mengambil data: {error!r}\n")
                failed += 1
                continue

            print(format_result(symbol, args.interval, result, args.days))
            if args.trades:
                print(format_trades(result))
            print()

    return 1 if failed == len(args.symbols) else 0


def main() -> None:
    raise SystemExit(asyncio.run(run(parse_args())))


if __name__ == "__main__":
    main()
