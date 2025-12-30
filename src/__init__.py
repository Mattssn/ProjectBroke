"""
Kalshi Sports Betting Bot - Source Package (No Perplexity)

Core modules:
- kalshi_client: Kalshi API for trading
- sports_odds_client: The Odds API for betting lines (free tier)
- free_sports_data: ESPN API for team data (free)
- openrouter_client: AI for decisions (GPT-4o-mini)
- decision_engine: Main analysis engine

NO PERPLEXITY REQUIRED!
"""

from .kalshi_client import KalshiClient
from .sports_odds_client import SportsOddsClient
from .openrouter_client import OpenRouterClient
from .decision_engine import AIDecisionEngine, BetDecision

__all__ = [
    'KalshiClient',
    'SportsOddsClient', 
    'OpenRouterClient',
    'AIDecisionEngine',
    'BetDecision'
]
