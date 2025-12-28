"""
Kalshi Sports Betting Bot - Source Package

This package contains the core modules for the intelligent sports betting system:
- kalshi_client: Enhanced Kalshi prediction market API client
- sports_odds_client: The Odds API client for sports betting lines
- perplexity_client: Perplexity AI for research and fact-finding
- openrouter_client: OpenRouter for multi-model AI inference
- decision_engine: AI-powered betting decision orchestration
"""

from .kalshi_client import KalshiClient
from .sports_odds_client import SportsOddsClient
from .perplexity_client import PerplexityClient
from .openrouter_client import OpenRouterClient
from .decision_engine import AIDecisionEngine, BetDecision

__all__ = [
    'KalshiClient',
    'SportsOddsClient', 
    'PerplexityClient',
    'OpenRouterClient',
    'AIDecisionEngine',
    'BetDecision'
]
