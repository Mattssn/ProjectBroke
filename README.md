# Kalshi Sports Bot (Simplified)

A lightweight Python toolkit for experimenting with Kalshi prediction markets. It combines a small Flask dashboard, a command-line menu, and helper clients for Kalshi, The Odds API, and OpenRouter. The default decision engine uses free odds data plus a low-cost OpenRouter model; Kalshi trading and Perplexity research are optional and require your own credentials.

## Project layout

- `main.py` – command-line entry point with an interactive menu and subcommands for scanning, dashboard launch, research, and portfolio checks.
- `web/app.py` – Flask dashboard exposing JSON endpoints for bot status, manual scans, and basic trading helpers.
- `src/decision_engine.py` – builds betting recommendations from odds data and OpenRouter analysis.
- `src/kalshi_client.py` – Kalshi REST client with RSA signing support.
- `src/sports_odds_client.py` – wrapper for The Odds API odds and event retrieval.
- `src/openrouter_client.py` – helper for calling OpenRouter chat models.
- `src/perplexity_client.py` – optional Perplexity client used only by the CLI research command.

## Requirements

- Python 3.9+
- API keys (set via environment or a local `.env` file):
  - `KALSHI_API_KEY` and `KALSHI_API_SECRET` for authenticated Kalshi trading (required for real orders and portfolio data).
  - `ODDS_API_KEY` for The Odds API (required for scanning odds).
  - `OPENROUTER_API_KEY` for AI scoring via OpenRouter.
  - `PERPLEXITY_API_KEY` only if you plan to use the `research` CLI command.

Install dependencies with:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running the CLI

All commands load environment variables from `.env` if present.

- Interactive menu: `python main.py`
- Launch dashboard server: `python main.py dashboard`
- Scan a sport: `python main.py scan americanfootball_nfl --max 5`
- Research a matchup (requires Perplexity): `python main.py research "Lakers vs Celtics"`
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

Scanning uses The Odds API for price snapshots, optional free ESPN data, and OpenRouter for recommendations. Auto-trading is disabled by default; toggling it only updates in-memory state—you must still provide valid Kalshi credentials for real orders.

## Notes and limitations

- The decision engine defaults to the `openai/gpt-4o-mini` model for lower cost. Change it via the `AI_MODEL` environment variable or the dashboard config API.
- Perplexity is not required for dashboard scans; it is only used by the `research` CLI command.
- API clients print errors to stdout but do not include retry/backoff beyond basic rate-limit handling.
- This code is for experimentation and should be used responsibly—understand the risks before trading.

## License

MIT License. See [LICENSE](LICENSE) for details.
