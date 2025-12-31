# Kalshi Sports Bot (Simplified)

A lightweight Python toolkit for experimenting with Kalshi prediction markets. It provides a small Flask dashboard, a command-line menu, and helper clients for Kalshi and The Odds API. The decision engine relies on free odds data, free ESPN context, and a heuristic scorer—no paid AI services are required.

## Features
- Interactive CLI for scanning markets, launching the dashboard, and checking portfolio status.
- Flask dashboard with JSON endpoints for bot control, portfolio insights, and trade helpers.
- Odds and context ingestion from The Odds API and ESPN, combined with heuristic scoring to suggest trades.
- Optional auto-trading flow (disabled by default) that requires valid Kalshi credentials.

## Prerequisites
- Python 3.9+
- API keys (set via environment variables or a local `.env` file):
  - `KALSHI_API_KEY` and `KALSHI_API_SECRET` for authenticated Kalshi trading (required for real orders and portfolio data).
  - `ODDS_API_KEY` for The Odds API (required for scanning odds).

## Installation
1. Clone the repository and move into it:
   ```bash
   git clone <repo-url>
   cd ProjectBroke
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration
Environment variables can be loaded from a `.env` file in the project root. At minimum, set your API keys:
```bash
KALSHI_API_KEY=your_key
KALSHI_API_SECRET=your_secret
ODDS_API_KEY=your_odds_api_key
```

## Project layout
- `main.py` – command-line entry point with an interactive menu and subcommands for scanning, dashboard launch, and portfolio checks.
- `web/app.py` – Flask dashboard exposing JSON endpoints for bot status, manual scans, and basic trading helpers.
- `src/decision_engine.py` – builds betting recommendations from odds data and heuristic scoring.
- `src/kalshi_client.py` – Kalshi REST client with RSA signing support.
- `src/sports_odds_client.py` – wrapper for The Odds API odds and event retrieval.

## Running the CLI
All commands load environment variables from `.env` if present.

- Interactive menu: `python main.py`
- Launch dashboard server: `python main.py dashboard`
- Scan a sport: `python main.py scan americanfootball_nfl --max 5`
- View portfolio balances (requires Kalshi credentials): `python main.py portfolio`
- Check which API keys are configured: `python main.py status`

## Dashboard
Start the Flask dashboard with `python main.py dashboard` (or run `web/app.py` directly). It uses the same environment variables as the CLI. The dashboard keeps a rolling cache of decisions, portfolio data, and recent trades while the background scanner iterates through the enabled sports list.

Key API routes:
- Bot control: `/api/bot/status`, `/api/bot/start`, `/api/bot/stop`, `/api/bot/config` (GET/POST), `/api/bot/auto-trade` (POST), `/api/bot/scan-now` (POST)
- Portfolio & history: `/api/portfolio`, `/api/positions`, `/api/trades`
- Decisions & logs: `/api/decisions`, `/api/debug/logs`, `/api/debug/settings`
- Trading helpers: `/api/trade/place` (POST), `/api/trade/cancel/<order_id>` (DELETE), `/api/orders`
- Health & stats: `/api/health`, `/api/stats`, `/api/errors`

Scanning uses The Odds API for price snapshots plus optional free ESPN data. Recommendations are produced by a simple heuristic scorer (no paid AI). Auto-trading is disabled by default; toggling it only updates in-memory state—you must still provide valid Kalshi credentials for real orders.

## Development and testing
Run the Flask app directly during development:
```bash
python web/app.py
```

If you add tests under `tests/` or `web/`, you can run them with:
```bash
python -m pytest
```

## Notes and limitations
- The decision engine uses heuristic scoring based on odds edges and bookmaker coverage.
- API clients print errors to stdout but do not include retry/backoff beyond basic rate-limit handling.
- This code is for experimentation and should be used responsibly—understand the risks before trading.

## License
MIT License. See [LICENSE](LICENSE) for details.
