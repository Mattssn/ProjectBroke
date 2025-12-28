# Kalshi Sports Betting Bot

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Flask](https://img.shields.io/badge/Flask-3.0-orange.svg)](https://flask.palletsprojects.com/)

> **An AI-powered intelligent trading system for Kalshi prediction markets, integrating sports odds, AI research, and multi-model decision making.**

This system combines multiple data sources and AI models to identify and analyze betting opportunities in Kalshi prediction markets, with a focus on sports events.

---

## ✨ Features

### 🎯 **Multi-Source Data Integration**
- **Kalshi API**: Real-time access to prediction market prices, orderbooks, and portfolio management
- **The Odds API**: Live sports betting lines from 50+ bookmakers (DraftKings, FanDuel, BetMGM, etc.)
- **Cross-Market Analysis**: Compare sportsbook odds with Kalshi prediction market prices

### 🤖 **AI-Powered Analysis**
- **Perplexity AI Research**: Automated team research, injury reports, and betting trends analysis
- **OpenRouter Multi-Model**: Access to 400+ AI models (GPT-4, Claude, Gemini, Llama) for decision synthesis
- **Intelligent Decision Engine**: Combines all data sources to generate actionable recommendations

### 📊 **Real-Time Dashboard with Full Bot Control**
- **Portfolio Tracking**: Live balance, positions, and P&L monitoring
- **Activity Feed**: Real-time trade history and execution status
- **AI Decision Log**: Complete audit trail of all AI-generated recommendations
- **Performance Charts**: Visual portfolio performance over time
- **Bot Control Panel**: Start/stop bot, toggle auto-trading, monitor scan status
- **Settings Management**: Adjust all parameters from the web UI
- **Manual Trading**: Place and cancel orders directly from the dashboard
- **On-Demand Scanning**: Trigger immediate market scans for any sport

### 🛡️ **Risk Management**
- **Configurable Thresholds**: Set minimum confidence, edge, and position sizes
- **Automated Filtering**: Only surfaces opportunities meeting your criteria
- **Full Transparency**: Complete reasoning chain for every recommendation

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** installed
- API keys from:
  - [Kalshi](https://kalshi.com/account/api-keys) (trading)
  - [The Odds API](https://the-odds-api.com/) (sports data)
  - [Perplexity AI](https://www.perplexity.ai/settings/api) (research)
  - [OpenRouter](https://openrouter.ai/keys) (AI models)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/kalshi-sports-bot.git
   cd kalshi-sports-bot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure API keys**
   ```bash
   cp .env.example .env
   # Edit .env with your API credentials
   ```

5. **Run the bot**
   ```bash
   python main.py
   ```

---

## 📖 Usage

### Interactive Menu

Run without arguments for the interactive menu:

```bash
python main.py
```

```
╔═══════════════════════════════════════════════════════════════╗
║           KALSHI SPORTS BETTING BOT                           ║
║       AI-Powered Prediction Market Trading                    ║
╠═══════════════════════════════════════════════════════════════╣
║  Features:                                                    ║
║  • Sports Odds Integration (The Odds API)                     ║
║  • AI Research (Perplexity)                                   ║
║  • Multi-Model Decisions (OpenRouter)                         ║
║  • Real-Time Dashboard                                        ║
╚═══════════════════════════════════════════════════════════════╝

   MAIN MENU
==================================================
   1. 🖥️  Launch Web Dashboard
   2. 🔍 Scan Sport for Opportunities
   3. 🔬 Research a Matchup
   4. 💼 View Portfolio
   5. 📊 Check API Status
   6. ❌ Exit
==================================================
```

### Command Line Interface

```bash
# Launch web dashboard
python main.py dashboard

# Scan a sport for opportunities
python main.py scan americanfootball_nfl --max 10

# Research a specific matchup
python main.py research "Chiefs vs Bills"

# View portfolio status
python main.py portfolio

# Check API configuration
python main.py status
```

### Supported Sports

| Sport | Key |
|-------|-----|
| NFL | `americanfootball_nfl` |
| College Football | `americanfootball_ncaaf` |
| NBA | `basketball_nba` |
| College Basketball | `basketball_ncaab` |
| MLB | `baseball_mlb` |
| NHL | `icehockey_nhl` |
| MLS | `soccer_usa_mls` |
| UFC/MMA | `mma_mixed_martial_arts` |

---

## 🏗️ Architecture

```
kalshi-sports-bot/
├── main.py                    # CLI entry point
├── requirements.txt           # Python dependencies
├── .env.example              # Environment template
├── README.md                 # Documentation
│
├── src/                      # Core modules
│   ├── __init__.py
│   ├── kalshi_client.py      # Kalshi API client
│   ├── sports_odds_client.py # The Odds API client
│   ├── perplexity_client.py  # Perplexity AI client
│   ├── openrouter_client.py  # OpenRouter AI client
│   └── decision_engine.py    # AI decision orchestration
│
├── web/                      # Web dashboard
│   ├── app.py               # Flask application + bot control APIs
│   ├── templates/
│   │   └── index.html       # Dashboard UI
│   └── static/
│       ├── css/
│       │   └── dashboard.css # Dashboard styles
│       └── js/
│           └── dashboard.js  # Dashboard JavaScript
│
└── logs/                     # Application logs
```

### Data Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  The Odds API   │     │  Perplexity AI  │     │    OpenRouter   │
│  (Sports Data)  │     │   (Research)    │     │  (AI Decisions) │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    Decision Engine      │
                    │  • Analyze Odds Value   │
                    │  • Research Context     │
                    │  • Generate Decisions   │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │      Kalshi API         │
                    │  • Execute Trades       │
                    │  • Manage Portfolio     │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    Web Dashboard        │
                    │  • Monitor Positions    │
                    │  • Track Decisions      │
                    └─────────────────────────┘
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `KALSHI_API_KEY` | Kalshi API key ID | Required |
| `KALSHI_API_SECRET` | Kalshi private key (PEM) | Required |
| `ODDS_API_KEY` | The Odds API key | Required |
| `PERPLEXITY_API_KEY` | Perplexity AI API key | Required |
| `OPENROUTER_API_KEY` | OpenRouter API key | Required |
| `MIN_CONFIDENCE` | Minimum AI confidence (0-1) | `0.6` |
| `MIN_EDGE` | Minimum expected edge | `0.03` |
| `MAX_BET_PCT` | Max bet as % of bankroll | `0.02` |
| `PORT` | Web dashboard port | `5000` |
| `DEBUG` | Enable debug mode | `false` |

### Decision Thresholds

The AI decision engine uses configurable thresholds:

- **MIN_CONFIDENCE (0.6)**: Only recommend bets where AI confidence ≥ 60%
- **MIN_EDGE (0.03)**: Only recommend bets with ≥ 3% expected value edge
- **MAX_BET_PCT (0.02)**: Limit each bet to 2% of portfolio

---

## 🔌 API Clients

### Kalshi Client

```python
from src.kalshi_client import KalshiClient

client = KalshiClient()

# Get portfolio
balance = client.get_balance()
positions = client.get_positions()

# Get market data
markets = client.get_markets(limit=100, status="open")
orderbook = client.get_market_orderbook("TICKER-123")

# Place order
order = client.create_order(
    ticker="TICKER-123",
    side="yes",
    action="buy",
    count=10,
    type="limit",
    yes_price=45
)
```

### Sports Odds Client

```python
from src.sports_odds_client import SportsOddsClient

client = SportsOddsClient()

# Get available sports
sports = client.get_sports()

# Get odds for NFL
odds = client.get_odds(
    sport="americanfootball_nfl",
    markets=["h2h", "spreads", "totals"],
    bookmakers=["draftkings", "fanduel"]
)

# Find best odds across bookmakers
best = client.find_best_odds(odds, "h2h")
```

### Perplexity Client

```python
from src.perplexity_client import PerplexityClient

client = PerplexityClient()

# Research a team
research = client.research_team("Kansas City Chiefs", "NFL")

# Get injury report
injuries = client.get_injury_report("Kansas City Chiefs", "NFL")

# Analyze matchup
analysis = client.research_matchup(
    team1="Chiefs",
    team2="Bills",
    sport="NFL"
)
```

### OpenRouter Client

```python
from src.openrouter_client import OpenRouterClient

client = OpenRouterClient()

# Get betting decision
decision = client.generate_bet_decision(
    event_info={"teams": ["Chiefs", "Bills"], "date": "2024-01-21"},
    odds_data={"home": -150, "away": +130},
    research_summary="Chiefs are 10-2 at home...",
    kalshi_prices={"yes": 65, "no": 35}
)
```

### Decision Engine

```python
from src.decision_engine import AIDecisionEngine

engine = AIDecisionEngine()

# Scan a sport
decisions = engine.scan_sport("americanfootball_nfl", max_events=5)

# Get recommendations only
recommendations = engine.get_recommendations(decisions)

# Analyze single event
decision = engine.analyze_event(event_data, include_research=True)
```

---

## 📊 Web Dashboard

The web dashboard provides real-time monitoring and full bot control at `http://localhost:5000`:

### Dashboard Overview

- **Portfolio Overview**: Balance, positions, P&L
- **Live Activity Feed**: Recent trades and executions
- **AI Decision Log**: All recommendations with reasoning
- **Performance Charts**: Portfolio value over time

### 🎮 Bot Control Panel

The dashboard header includes a full bot control panel:

| Control | Description |
|---------|-------------|
| **Start/Stop Bot** | Toggle the background market scanner on/off |
| **Auto Trade Toggle** | Enable/disable automatic trade execution |
| **Status Indicator** | Shows current bot state and active sport being scanned |
| **Live Stats** | Events analyzed, recommendations, trades today, daily P&L |

### ⚙️ Settings Page

Click the gear icon to access all configurable parameters:

| Setting | Description | Default |
|---------|-------------|---------|
| Min Confidence | AI confidence threshold (0-1) | 0.6 |
| Min Edge % | Minimum expected value | 3% |
| Max Bet Size % | Bet size as % of bankroll | 2% |
| Max Position Size | Cap on contracts per position | 1000 |
| Max Daily Trades | Daily trade limit (safety) | 10 |
| Max Daily Loss | Stop-loss for the day | $100 |
| Scan Interval | How often bot scans (seconds) | 300 |
| AI Model | Claude, GPT-4o, GPT-4o-mini | Claude 3.5 |
| Enabled Sports | Toggle which sports to scan | NFL, NBA |
| Use Research | Enable Perplexity AI research | On |
| Auto Execute | Allow bot to place trades automatically | Off |

### 💰 Manual Trading Page

Click the dollar icon to access manual trading:

- **Place Orders**: Enter ticker, side (YES/NO), action (BUY/SELL), quantity, price
- **Order Types**: Limit or Market orders
- **Open Orders**: View all resting limit orders
- **Cancel Orders**: Cancel any open order with one click

### 🔍 Scan Now Modal

Click "Scan Now" to trigger an immediate market scan:

- Select sport to scan
- Configure max events to analyze
- Toggle whether to include AI research
- View results immediately in the decisions feed

### API Endpoints

#### Portfolio & Data
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/portfolio` | GET | Get portfolio summary |
| `/api/positions` | GET | Get open positions |
| `/api/trades` | GET | Get recent trades |
| `/api/decisions` | GET | Get AI decisions |
| `/api/decision-logs` | GET | Get detailed decision logs |

#### Bot Control
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/bot/status` | GET | Get bot state, config, and stats |
| `/api/bot/start` | POST | Start the bot scanner |
| `/api/bot/stop` | POST | Stop the bot scanner |
| `/api/bot/config` | GET | Get current configuration |
| `/api/bot/config` | POST | Update configuration |
| `/api/bot/auto-trade` | POST | Toggle auto-trade mode |
| `/api/bot/scan-now` | POST | Trigger immediate scan |

#### Trading
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/trade/place` | POST | Place a new order |
| `/api/trade/cancel/{id}` | DELETE | Cancel an open order |
| `/api/orders` | GET | Get open orders |

#### Market Data
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/odds/{sport}` | GET | Get odds for a sport |
| `/api/sports` | GET | Get available sports |
| `/api/kalshi/markets` | GET | Get Kalshi markets |
| `/api/kalshi/market/{ticker}` | GET | Get market details |
| `/api/analyze` | POST | Analyze specific event |
| `/api/research` | POST | Research a matchup |

#### System
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/errors` | GET | Get recent bot errors |
| `/api/stats` | GET | Get trading statistics |

---

## ⚠️ Disclaimers

### Risk Warning

**Trading involves significant risk of loss.** This software is for educational and informational purposes only. Always:

- Understand the risks before trading
- Never trade with money you can't afford to lose
- Test thoroughly with small amounts first
- Monitor your positions regularly
- Comply with all applicable laws and terms of service

### Not Financial Advice

This bot provides AI-generated analysis and recommendations. These are **not financial advice**. The developers are not responsible for any trading losses.

### API Usage

- Respect rate limits on all APIs
- Keep your API keys secure
- Monitor your API usage and costs
- The Odds API has usage-based pricing

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Kalshi](https://kalshi.com) - Prediction market platform
- [The Odds API](https://the-odds-api.com) - Sports betting data
- [Perplexity AI](https://perplexity.ai) - AI research
- [OpenRouter](https://openrouter.ai) - Multi-model AI access
