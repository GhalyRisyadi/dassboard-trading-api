# Crypto Trading Dashboard

## Project purpose

 The goal of this project is to develop a cryptocurrency market dashboard with an AI model deployed as part of the application. The model is expected to analyze Binance market data and forecast coin prices and their movement direction one to three days ahead. Potential inputs include price and volume, transaction counts, large-trade and order-flow indicators that may act as proxies for whale activity, and other features demonstrated through validation to be predictive. A forecast horizon describes the model's intended capability, not a guarantee of accuracy. Large-trade indicators do not by themselves identify whale holders or their off-exchange movements.

The AI forecasting model is a project goal and is not implemented yet. The current backend provides rule-based EMA crossover signals and a historical backtest; the dashboard displays Binance market data and candlestick charts. The application is for market monitoring and strategy evaluation: it does not connect to exchange accounts, place trades, or provide financial advice.

The product is split across two repositories:

- This repository (`dashboard-trading-api`) contains the backend API and historical backtest tool.
- The companion frontend repository is `crypto-dashboard` (often checked out beside this repository). It contains the browser dashboard and its visual design.

Treat each repository's source code and package manifest as the source of truth for its current implementation. The frontend's README may lag behind its code; in particular, the current signals service fetches signals from this API.

## Backend: this repository

### Language and framework

- Python 3
- FastAPI for HTTP routes, request handling, CORS, and interactive OpenAPI documentation.
- Pydantic for API response models and validation.
- Uvicorn as the ASGI server.
- `httpx2` for asynchronous HTTP requests to Binance.
- `pytest` for automated tests.

Runtime dependencies are declared in `requirements.txt`; development dependencies are in `requirements-dev.txt`.

### API and signal behavior

- `GET /health` returns the service health status.
- `GET /signals` returns the latest signal for each supported market pair, using the `Signal` response schema. JSON field names use camelCase to match the frontend type.
- Signals use the EMA 12/26 crossover on completed 1-hour candles: `BUY` on an upward cross, `SELL` on a downward cross, and `HOLD` when there is no new cross. This is a deterministic rule, not an AI prediction, so `confidence` is `null`.
- Market candles come from Binance's public klines REST endpoint. The in-progress candle is excluded so a signal does not change before its candle closes.
- Requests for watched pairs run concurrently. A failed pair is skipped; if all pairs fail, `/signals` returns HTTP 502.
- `CORS_ORIGINS` configures permitted frontend origins. `BINANCE_URL` configures the Binance API base URL.

Keep the API's `Signal` fields, enum values, timestamp units, and camelCase JSON representation compatible with `crypto-dashboard/src/types/signals.ts` when changing the response contract.

### Backtesting

Run the historical EMA crossover backtest with `python -m app.backtest`. It fetches Binance candle history and reports strategy return, buy-and-hold return, maximum drawdown, exposure, and trade statistics. The simulator is spot-only and long-only, executes a signal at the next candle's open, and applies configurable per-side commission and slippage. It does not model spread, liquidity, or taxes. Historical results do not guarantee future performance.

### Backend commands

From this repository root:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
python -m pytest -q
python -m app.backtest --symbols BTCUSDT ETHUSDT --interval 1h --days 365
```

The interactive API documentation is available at `http://localhost:8000/docs` while the server is running. The service and backtest need internet access to retrieve Binance market data.

## Frontend: companion `crypto-dashboard` repository

### Language, framework, and packages

- TypeScript and Vue 3 using the Composition API and `<script setup>`.
- Vite for development and production builds.
- Vue Router for page navigation and Pinia for application state.
- Tailwind CSS 4 for styling, including its Vite plugin.
- `lightweight-charts` for candlestick charts.
- ESLint, oxlint, Prettier, and `vue-tsc` for code quality and type checking.

The frontend reads `VITE_API_URL` for the backend base URL, defaulting to `http://localhost:8000`. Its market services also request ticker and candle data directly from Binance, including live updates over Binance WebSocket. The signals service calls this backend's `/signals` endpoint. The Portfolio page is currently a placeholder; the app does not execute trades or manage exchange accounts.

### Current design system

There is no separate design-token file or formal component-library package. The visual system is implemented with Tailwind utility classes and shared components under `src/components/ui/`:

- Dark dashboard canvas (`gray-950`), cards (`gray-900`), borders and interactive surfaces (`gray-800`), primary text (`gray-100`), and secondary text (`gray-400`).
- Green communicates positive movement and `BUY`; red communicates negative movement and `SELL`; gray communicates neutral values and `HOLD`.
- Cards, tables, price badges, and signal badges use compact spacing, subtle borders, and rounded corners through Tailwind utilities.

When extending the frontend, follow these existing component and color conventions. Do not describe these utility classes as a formal token system unless one is added to the frontend.

### Frontend commands

From the `crypto-dashboard` repository root:

```sh
npm install
npm run dev
npm run type-check
npm run build
npm run lint
```

The lint scripts currently include `--fix` and may modify files; inspect their effects before running them when you only intend to check code.

## Main source locations

- `app/main.py`: FastAPI application, routes, CORS, and HTTP client setup.
- `app/schemas.py`: API response types.
- `app/services/`: Binance market data and EMA signal logic.
- `app/backtest/`: historical candle loading, simulator, and reports.
- `tests/`: API, indicator, signal, history, and backtest tests.
- Frontend `src/services/` and `src/stores/`: external data access and shared state.
- Frontend `src/features/`, `src/components/ui/`, and `src/assets/main.css`: dashboard views and styling.

