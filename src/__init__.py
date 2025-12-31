"""
Kalshi Sports Betting Bot - Source Package (No Third-Party AI)

Core modules:
- kalshi_client: Kalshi API for trading
- sports_odds_client: The Odds API for betting lines (free tier)
- free_sports_data: ESPN API for team data (free)
- decision_engine: Main analysis engine (heuristics only)
"""

from .kalshi_client import KalshiClient
from .sports_odds_client import SportsOddsClient
from .decision_engine import AIDecisionEngine, BetDecision

__all__ = [
    'KalshiClient',
    'SportsOddsClient',
    'AIDecisionEngine',
    'BetDecision'
]
