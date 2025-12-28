"""
AI Decision Engine

Orchestrates the analysis pipeline combining:
- Sports Odds API for real-time betting lines
- Perplexity for research on teams, injuries, trends
- OpenRouter AI for decision making
- Kalshi for prediction market execution

This module provides the intelligent decision-making layer that
analyzes all available data and generates actionable betting decisions.
"""
import os
import json
import time
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
import logging

from .kalshi_client import KalshiClient
from .sports_odds_client import SportsOddsClient
from .perplexity_client import PerplexityClient
from .openrouter_client import OpenRouterClient


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BetDecision:
    """Data structure for a betting decision."""
    event_id: str
    event_name: str
    sport: str
    home_team: str
    away_team: str
    commence_time: str
    
    decision: str  # 'place_bet' or 'skip'
    bet_type: Optional[str] = None  # 'moneyline', 'spread', 'total'
    bet_side: Optional[str] = None  # 'home', 'away', 'over', 'under'
    bet_amount_usd: Optional[float] = None
    confidence: float = 0.0
    expected_value: float = 0.0
    win_probability: float = 0.0
    
    reasoning: str = ""
    key_insights: List[str] = None
    risk_factors: List[str] = None
    
    # Source data
    odds_snapshot: Dict = None
    research_summary: Dict = None
    kalshi_market: Dict = None
    
    created_at: str = None
    model_used: str = None
    
    def __post_init__(self):
        if self.key_insights is None:
            self.key_insights = []
        if self.risk_factors is None:
            self.risk_factors = []
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class DecisionLog:
    """Log entry for an AI decision."""
    timestamp: str
    event_id: str
    decision_type: str
    model: str
    input_summary: Dict
    output: Dict
    execution_time_ms: int
    
    def to_dict(self) -> Dict:
        return asdict(self)


class AIDecisionEngine:
    """
    Main decision engine that orchestrates all AI analysis.
    """
    
    # Default models for different tasks
    DEFAULT_MODELS = {
        "analysis": "openai/gpt-4o",
        "decision": "anthropic/claude-3.5-sonnet",
        "fast_check": "openai/gpt-4o-mini"
    }
    
    # Sport mapping between Odds API and Kalshi
    SPORT_MAPPING = {
        "americanfootball_nfl": "NFL",
        "americanfootball_ncaaf": "NCAAF",
        "basketball_nba": "NBA",
        "basketball_ncaab": "NCAAB",
        "baseball_mlb": "MLB",
        "icehockey_nhl": "NHL",
        "soccer_usa_mls": "MLS",
    }
    
    def __init__(self):
        # Initialize all clients
        self.kalshi = KalshiClient()
        self.odds = SportsOddsClient()
        self.perplexity = PerplexityClient()
        self.openrouter = OpenRouterClient()
        
        # Decision logs
        self.decision_logs: List[DecisionLog] = []
        
        # Configuration
        self.min_confidence = float(os.getenv("MIN_CONFIDENCE", "0.6"))
        self.min_edge = float(os.getenv("MIN_EDGE", "0.03"))  # 3% edge
        self.max_bet_pct = float(os.getenv("MAX_BET_PCT", "0.02"))  # 2% of bankroll
        
        # Cache for research to avoid duplicate API calls
        self._research_cache: Dict[str, Dict] = {}
        self._cache_ttl = 3600  # 1 hour
    
    def _log_decision(self, event_id: str, decision_type: str, 
                      model: str, input_data: Dict, output: Dict,
                      execution_time_ms: int):
        """Log a decision for later analysis."""
        log = DecisionLog(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_id=event_id,
            decision_type=decision_type,
            model=model,
            input_summary=input_data,
            output=output,
            execution_time_ms=execution_time_ms
        )
        self.decision_logs.append(log)
        logger.info(f"Decision logged: {decision_type} for {event_id}")
    
    def get_decision_logs(self, limit: int = 100) -> List[Dict]:
        """Get recent decision logs."""
        return [log.to_dict() for log in self.decision_logs[-limit:]]
    
    # ==================== Research Methods ====================
    
    def research_event(self, home_team: str, away_team: str, 
                       sport: str, event_date: str = None) -> Dict:
        """
        Conduct comprehensive research on an event.
        
        Returns combined research from Perplexity including:
        - Team analysis
        - Matchup history
        - Injury reports
        - Betting trends
        """
        cache_key = f"{home_team}_{away_team}_{sport}"
        
        # Check cache
        if cache_key in self._research_cache:
            cached = self._research_cache[cache_key]
            if time.time() - cached.get("_cached_at", 0) < self._cache_ttl:
                return cached
        
        logger.info(f"Researching: {home_team} vs {away_team}")
        start_time = time.time()
        
        research = {
            "home_team": {},
            "away_team": {},
            "matchup": {},
            "injuries": {"home": {}, "away": {}},
            "betting_trends": {}
        }
        
        try:
            # Research home team
            home_research = self.perplexity.research_team(home_team, sport)
            research["home_team"] = {
                "analysis": home_research.get("answer", ""),
                "citations": home_research.get("citations", [])
            }
            
            # Research away team
            away_research = self.perplexity.research_team(away_team, sport)
            research["away_team"] = {
                "analysis": away_research.get("answer", ""),
                "citations": away_research.get("citations", [])
            }
            
            # Matchup analysis
            matchup = self.perplexity.research_matchup(
                home_team, away_team, sport, event_date
            )
            research["matchup"] = {
                "analysis": matchup.get("answer", ""),
                "citations": matchup.get("citations", [])
            }
            
            # Injury reports
            home_injuries = self.perplexity.get_injury_report(home_team, sport)
            away_injuries = self.perplexity.get_injury_report(away_team, sport)
            research["injuries"]["home"] = home_injuries.get("answer", "")
            research["injuries"]["away"] = away_injuries.get("answer", "")
            
            # Betting trends
            trends = self.perplexity.get_betting_trends(
                matchup=f"{home_team} vs {away_team}"
            )
            research["betting_trends"] = trends.get("answer", "")
            
        except Exception as e:
            logger.error(f"Research error: {e}")
            research["error"] = str(e)
        
        research["_cached_at"] = time.time()
        research["research_time_seconds"] = time.time() - start_time
        
        # Cache the result
        self._research_cache[cache_key] = research
        
        return research
    
    # ==================== Odds Analysis ====================
    
    def get_odds_for_sport(self, sport_key: str) -> List[Dict]:
        """Get current odds for a sport."""
        return self.odds.get_odds(
            sport=sport_key,
            regions="us",
            markets="h2h,spreads,totals",
            odds_format="american"
        )
    
    def analyze_odds_value(self, event_odds: Dict) -> Dict:
        """
        Analyze odds for value betting opportunities.
        
        Returns analysis of each betting market.
        """
        analysis = {
            "event_id": event_odds.get("id"),
            "home_team": event_odds.get("home_team"),
            "away_team": event_odds.get("away_team"),
            "markets": {}
        }
        
        for bookmaker in event_odds.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                market_key = market.get("key")
                
                if market_key not in analysis["markets"]:
                    analysis["markets"][market_key] = {
                        "best_home": {"odds": float("-inf"), "book": None},
                        "best_away": {"odds": float("-inf"), "book": None},
                        "worst_home": {"odds": float("inf"), "book": None},
                        "worst_away": {"odds": float("inf"), "book": None},
                        "all_odds": []
                    }
                
                for outcome in market.get("outcomes", []):
                    name = outcome.get("name")
                    odds = outcome.get("price", 0)
                    point = outcome.get("point")
                    book = bookmaker.get("title")
                    
                    analysis["markets"][market_key]["all_odds"].append({
                        "name": name,
                        "odds": odds,
                        "point": point,
                        "bookmaker": book
                    })
                    
                    if name == event_odds.get("home_team"):
                        if odds > analysis["markets"][market_key]["best_home"]["odds"]:
                            analysis["markets"][market_key]["best_home"] = {"odds": odds, "book": book, "point": point}
                        if odds < analysis["markets"][market_key]["worst_home"]["odds"]:
                            analysis["markets"][market_key]["worst_home"] = {"odds": odds, "book": book, "point": point}
                    elif name == event_odds.get("away_team"):
                        if odds > analysis["markets"][market_key]["best_away"]["odds"]:
                            analysis["markets"][market_key]["best_away"] = {"odds": odds, "book": book, "point": point}
                        if odds < analysis["markets"][market_key]["worst_away"]["odds"]:
                            analysis["markets"][market_key]["worst_away"] = {"odds": odds, "book": book, "point": point}
        
        # Calculate consensus and line discrepancies
        for market_key, data in analysis["markets"].items():
            home_odds = [o["odds"] for o in data["all_odds"] if o["name"] == analysis["home_team"]]
            away_odds = [o["odds"] for o in data["all_odds"] if o["name"] == analysis["away_team"]]
            
            if home_odds:
                data["home_consensus"] = sum(home_odds) / len(home_odds)
                data["home_std_dev"] = (sum((x - data["home_consensus"])**2 for x in home_odds) / len(home_odds)) ** 0.5
            
            if away_odds:
                data["away_consensus"] = sum(away_odds) / len(away_odds)
                data["away_std_dev"] = (sum((x - data["away_consensus"])**2 for x in away_odds) / len(away_odds)) ** 0.5
        
        return analysis
    
    # ==================== Kalshi Integration ====================
    
    def find_matching_kalshi_market(self, event_info: Dict) -> Optional[Dict]:
        """
        Find a matching Kalshi market for a sports event.
        
        This is a heuristic search - Kalshi markets may not always
        have exact matches for every game.
        """
        home_team = event_info.get("home_team", "")
        away_team = event_info.get("away_team", "")
        sport = event_info.get("sport_key", "")
        
        # Search Kalshi markets
        kalshi_markets = self.kalshi.get_markets(limit=500, status="open")
        
        # Try to find matching market
        for market in kalshi_markets:
            title = market.get("title", "").lower()
            
            # Check if team names appear in title
            if (home_team.lower() in title or away_team.lower() in title):
                return market
        
        return None
    
    # ==================== Main Decision Logic ====================
    
    def analyze_event(self, event_odds: Dict, sport_key: str,
                      include_research: bool = True,
                      model: str = None) -> BetDecision:
        """
        Complete analysis of a single event.
        
        Args:
            event_odds: Odds data from Sports Odds API
            sport_key: Sport identifier
            include_research: Whether to include Perplexity research
            model: Override default AI model
        
        Returns:
            BetDecision with complete analysis
        """
        model = model or self.DEFAULT_MODELS["decision"]
        start_time = time.time()
        
        event_id = event_odds.get("id", "unknown")
        home_team = event_odds.get("home_team", "")
        away_team = event_odds.get("away_team", "")
        commence_time = event_odds.get("commence_time", "")
        
        logger.info(f"Analyzing: {home_team} vs {away_team}")
        
        # Step 1: Analyze odds
        odds_analysis = self.analyze_odds_value(event_odds)
        
        # Step 2: Research (optional but recommended)
        research = {}
        if include_research:
            sport_name = self.SPORT_MAPPING.get(sport_key, sport_key)
            research = self.research_event(home_team, away_team, sport_name)
        
        # Step 3: Check for Kalshi market
        kalshi_market = self.find_matching_kalshi_market({
            "home_team": home_team,
            "away_team": away_team,
            "sport_key": sport_key
        })
        
        # Step 4: Generate AI decision
        portfolio = self.kalshi.get_balance() or {}
        
        decision_input = {
            "event_id": event_id,
            "home_team": home_team,
            "away_team": away_team,
            "commence_time": commence_time,
            "sport": sport_key
        }
        
        ai_decision = self.openrouter.generate_bet_decision(
            event_info=decision_input,
            odds_analysis=odds_analysis,
            perplexity_research=research,
            portfolio_context=portfolio,
            model=model
        )
        
        # Log the decision
        execution_time = int((time.time() - start_time) * 1000)
        self._log_decision(
            event_id=event_id,
            decision_type="full_analysis",
            model=model,
            input_data={"odds": len(event_odds.get("bookmakers", [])), "research": bool(research)},
            output=ai_decision,
            execution_time_ms=execution_time
        )
        
        # Build BetDecision
        decision = BetDecision(
            event_id=event_id,
            event_name=f"{away_team} @ {home_team}",
            sport=sport_key,
            home_team=home_team,
            away_team=away_team,
            commence_time=commence_time,
            decision=ai_decision.get("decision", "skip"),
            bet_type=ai_decision.get("bet_type"),
            bet_side=ai_decision.get("bet_side"),
            bet_amount_usd=ai_decision.get("bet_amount_usd"),
            confidence=ai_decision.get("confidence", 0),
            expected_value=ai_decision.get("expected_value", 0),
            win_probability=ai_decision.get("win_probability", 0),
            reasoning=ai_decision.get("reasoning", ""),
            key_insights=ai_decision.get("key_insights", []),
            risk_factors=ai_decision.get("risk_factors", []),
            odds_snapshot=odds_analysis,
            research_summary=research,
            kalshi_market=kalshi_market,
            model_used=model
        )
        
        return decision
    
    def scan_sport(self, sport_key: str, 
                   max_events: int = 10,
                   include_research: bool = True) -> List[BetDecision]:
        """
        Scan all events for a sport and generate decisions.
        
        Args:
            sport_key: Sport to scan
            max_events: Maximum events to analyze
            include_research: Include Perplexity research
        
        Returns:
            List of BetDecisions
        """
        logger.info(f"Scanning sport: {sport_key}")
        
        odds_data = self.get_odds_for_sport(sport_key)
        decisions = []
        
        for event in odds_data[:max_events]:
            try:
                decision = self.analyze_event(
                    event_odds=event,
                    sport_key=sport_key,
                    include_research=include_research
                )
                decisions.append(decision)
                
                # Rate limiting
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error analyzing event: {e}")
                continue
        
        return decisions
    
    def get_recommendations(self, decisions: List[BetDecision],
                           min_confidence: float = None) -> List[BetDecision]:
        """
        Filter decisions to only actionable recommendations.
        
        Args:
            decisions: List of analyzed decisions
            min_confidence: Minimum confidence threshold
        
        Returns:
            Filtered list of recommended bets
        """
        min_conf = min_confidence or self.min_confidence
        
        return [
            d for d in decisions
            if d.decision == "place_bet"
            and d.confidence >= min_conf
            and d.expected_value > 0
        ]
    
    def get_portfolio_summary(self) -> Dict:
        """Get current portfolio state for the dashboard."""
        balance_data = self.kalshi.get_balance() or {}
        positions_data = self.kalshi.get_positions() or {}
        fills_data = self.kalshi.get_fills(limit=50) or {}
        
        return {
            "balance": balance_data.get("balance", 0) / 100,  # Convert cents to dollars
            "portfolio_value": balance_data.get("portfolio_value", 0) / 100,
            "positions": positions_data.get("market_positions", []),
            "recent_fills": fills_data.get("fills", [])[:10],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Convenience function
def get_engine() -> AIDecisionEngine:
    """Get a configured AI Decision Engine."""
    return AIDecisionEngine()
