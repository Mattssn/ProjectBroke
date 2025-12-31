"""
Heuristic Decision Engine (no external AI)

Uses only free data sources:
- The Odds API (free tier: 500 req/month) for betting lines
- ESPN API (free) for team data when available
"""
import os
import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
    bet_type: Optional[str] = None
    bet_side: Optional[str] = None
    bet_amount_usd: Optional[float] = None
    confidence: float = 0.0
    expected_value: float = 0.0
    win_probability: float = 0.0
    
    reasoning: str = ""
    key_insights: List[str] = None
    risk_factors: List[str] = None
    
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
    
    def to_dict(self) -> Dict:
        return {
            "event_id": self.event_id,
            "event_name": self.event_name,
            "sport": self.sport,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "commence_time": self.commence_time,
            "decision": self.decision,
            "bet_type": self.bet_type,
            "bet_side": self.bet_side,
            "bet_amount_usd": self.bet_amount_usd,
            "confidence": self.confidence,
            "expected_value": self.expected_value,
            "win_probability": self.win_probability,
            "reasoning": self.reasoning,
            "key_insights": self.key_insights or [],
            "risk_factors": self.risk_factors or [],
            "odds_snapshot": self.odds_snapshot,
            "research_summary": self.research_summary,
            "kalshi_market": self.kalshi_market,
            "created_at": self.created_at,
            "model_used": self.model_used
        }


class AIDecisionEngine:
    """
    Simplified decision engine without any third-party AI models.

    Data sources:
    - The Odds API (free tier) for betting lines
    - ESPN API (free) for team stats/injuries
    """
    
    SPORT_MAPPING = {
        "americanfootball_nfl": "NFL",
        "americanfootball_ncaaf": "NCAAF", 
        "basketball_nba": "NBA",
        "basketball_ncaab": "NCAAB",
        "baseball_mlb": "MLB",
        "icehockey_nhl": "NHL",
    }
    
    def __init__(self):
        # Import here to avoid circular imports
        from .sports_odds_client import SportsOddsClient
        from .free_sports_data import FreeSportsDataClient

        self.odds_client = SportsOddsClient()
        self.free_data = FreeSportsDataClient()

        self.min_confidence = float(os.getenv("MIN_CONFIDENCE", "0.6"))
        self.min_edge = float(os.getenv("MIN_EDGE", "0.03"))

        self._on_decision_callback: Optional[Callable] = None
        self.decision_logs = []

        logger.info("[ENGINE] Initialized with heuristic scoring (no external AI)")
        logger.info("[ENGINE] Using free data sources only")
    
    def set_decision_callback(self, callback: Callable):
        """Set callback for real-time decision updates."""
        self._on_decision_callback = callback
    
    # ==================== Odds Processing ====================
    
    def get_odds_for_sport(self, sport_key: str) -> List[Dict]:
        """Get odds from The Odds API."""
        return self.odds_client.get_odds(
            sport=sport_key,
            regions="us",
            markets="h2h,spreads,totals",
            odds_format="american"
        )
    
    def summarize_odds(self, event_odds: Dict) -> Dict:
        """Create concise odds summary."""
        home_team = event_odds.get("home_team", "")
        away_team = event_odds.get("away_team", "")
        
        summary = {
            "home_team": home_team,
            "away_team": away_team,
            "moneyline": {"home": [], "away": []},
            "spread": {"home": [], "away": []},
            "total": {"over": [], "under": []}
        }
        
        for bookmaker in event_odds.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                market_key = market.get("key")
                
                for outcome in market.get("outcomes", []):
                    name = outcome.get("name", "")
                    price = outcome.get("price", 0)
                    point = outcome.get("point")
                    
                    if market_key == "h2h":
                        if name == home_team:
                            summary["moneyline"]["home"].append(price)
                        elif name == away_team:
                            summary["moneyline"]["away"].append(price)
                    elif market_key == "spreads":
                        if name == home_team:
                            summary["spread"]["home"].append({"line": point, "odds": price})
                        elif name == away_team:
                            summary["spread"]["away"].append({"line": point, "odds": price})
                    elif market_key == "totals":
                        if name == "Over":
                            summary["total"]["over"].append({"line": point, "odds": price})
                        elif name == "Under":
                            summary["total"]["under"].append({"line": point, "odds": price})
        
        # Calculate consensus
        def avg(lst): return sum(lst) / len(lst) if lst else 0
        def best(lst): return max(lst) if lst else 0
        
        return {
            "home_team": home_team,
            "away_team": away_team,
            "moneyline": {
                "home_consensus": int(avg(summary["moneyline"]["home"])) if summary["moneyline"]["home"] else 0,
                "away_consensus": int(avg(summary["moneyline"]["away"])) if summary["moneyline"]["away"] else 0,
                "home_best": best(summary["moneyline"]["home"]),
                "away_best": best(summary["moneyline"]["away"]),
            },
            "spread": {
                "home_line": summary["spread"]["home"][0]["line"] if summary["spread"]["home"] else 0,
                "away_line": summary["spread"]["away"][0]["line"] if summary["spread"]["away"] else 0,
                "home_odds": int(avg([s["odds"] for s in summary["spread"]["home"]])) if summary["spread"]["home"] else 0,
                "away_odds": int(avg([s["odds"] for s in summary["spread"]["away"]])) if summary["spread"]["away"] else 0,
            },
            "total": {
                "line": summary["total"]["over"][0]["line"] if summary["total"]["over"] else 0,
                "over_odds": int(avg([t["odds"] for t in summary["total"]["over"]])) if summary["total"]["over"] else 0,
                "under_odds": int(avg([t["odds"] for t in summary["total"]["under"]])) if summary["total"]["under"] else 0,
            },
            "bookmaker_count": len(event_odds.get("bookmakers", []))
        }
    
    # ==================== Free Research ====================
    
    def get_team_research(self, sport_key: str, home_team: str, away_team: str) -> str:
        """
        Get FREE team research from ESPN.
        Falls back gracefully if unavailable.
        """
        try:
            matchup = self.free_data.get_matchup_summary(sport_key, home_team, away_team)
            
            # Check if we got useful data
            home_data = matchup.get("home_team") or {}
            away_data = matchup.get("away_team") or {}
            
            if home_data.get("record") or away_data.get("record"):
                return self.free_data.format_for_ai_prompt(matchup)
            else:
                logger.info(f"[ENGINE] ESPN data unavailable for {home_team} vs {away_team}")
                return self._basic_context(home_team, away_team)
                
        except Exception as e:
            logger.warning(f"[ENGINE] Research fetch failed: {e}")
            return self._basic_context(home_team, away_team)
    
    def _basic_context(self, home_team: str, away_team: str) -> str:
        """Generate basic context when ESPN is unavailable."""
        return f"""=== {away_team} @ {home_team} ===

Team research unavailable - analyzing based on odds only.

Consider:
- Home field advantage (~3 points in NFL)  
- Line movement indicates sharp money
- Look for value in line discrepancies"""
    
    # ==================== Heuristic Decision ====================

    @staticmethod
    def _implied_probability(american_odds: float) -> float:
        """Convert American odds to implied probability."""
        if not american_odds:
            return 0.0
        if american_odds > 0:
            return 100 / (american_odds + 100)
        return -american_odds / (-american_odds + 100)

    def _evaluate_moneyline_edge(self, odds: Dict) -> Dict:
        """Evaluate moneyline edges using consensus vs best prices."""
        home_consensus = odds["moneyline"].get("home_consensus") or 0
        away_consensus = odds["moneyline"].get("away_consensus") or 0
        home_best = odds["moneyline"].get("home_best") or 0
        away_best = odds["moneyline"].get("away_best") or 0

        edges = {}
        for side, best, consensus in [
            ("home", home_best, home_consensus),
            ("away", away_best, away_consensus),
        ]:
            if best == 0 or consensus == 0:
                edges[side] = {"edge": 0.0, "implied_prob": 0.0}
                continue

            consensus_prob = self._implied_probability(consensus)
            best_prob = self._implied_probability(best)
            edge = consensus_prob - best_prob
            edges[side] = {"edge": edge, "implied_prob": best_prob}

        best_side = max(edges.items(), key=lambda item: item[1]["edge"])
        selected_side, metrics = best_side

        return {
            "side": selected_side,
            "edge": metrics["edge"],
            "win_probability": max(0.0, min(1.0, 1 - metrics["implied_prob"] if metrics["implied_prob"] else 0)),
        }
    
    def analyze_event(self, event_odds: Dict, sport_key: str,
                      include_research: bool = True) -> BetDecision:
        """Analyze a single event and return decision."""
        start_time = time.time()
        
        event_id = event_odds.get("id", "unknown")
        home_team = event_odds.get("home_team", "")
        away_team = event_odds.get("away_team", "")
        commence_time = event_odds.get("commence_time", "")
        
        logger.info(f"[ENGINE] Analyzing: {away_team} @ {home_team}")
        
        # Step 1: Summarize odds
        odds_summary = self.summarize_odds(event_odds)
        
        # Step 2: Get free research (ESPN)
        research = ""
        if include_research:
            research = self.get_team_research(sport_key, home_team, away_team)

        # Step 3: Heuristic scoring instead of external AI
        moneyline_eval = self._evaluate_moneyline_edge(odds_summary)
        edge = moneyline_eval.get("edge", 0.0)
        bookmaker_count = odds_summary.get("bookmaker_count", 0)

        decision_flag = "skip"
        bet_type = None
        bet_side = None
        confidence = 0.0
        expected_value = 0.0
        win_probability = 0.0
        reasoning_parts = []

        if bookmaker_count == 0:
            reasoning_parts.append("No bookmaker data available.")
        elif edge >= self.min_edge:
            decision_flag = "place_bet"
            bet_type = "moneyline"
            bet_side = moneyline_eval["side"]
            expected_value = edge
            win_probability = moneyline_eval.get("win_probability", 0.0)
            confidence = min(1.0, max(self.min_confidence, edge * 10 + bookmaker_count * 0.02))
            reasoning_parts.append(
                f"{bet_side.title()} side offers a value edge of {edge:.2%} versus consensus pricing."
            )
        else:
            reasoning_parts.append(
                f"Edge {edge:.2%} below threshold of {self.min_edge:.0%}; skipping."
            )

        if research:
            reasoning_parts.append("ESPN research added for context.")

        elapsed = int((time.time() - start_time) * 1000)
        logger.info(f"[ENGINE] Complete in {elapsed}ms - Decision: {decision_flag}")

        decision = BetDecision(
            event_id=event_id,
            event_name=f"{away_team} @ {home_team}",
            sport=sport_key,
            home_team=home_team,
            away_team=away_team,
            commence_time=commence_time,
            decision=decision_flag,
            bet_type=bet_type,
            bet_side=bet_side,
            bet_amount_usd=None,
            confidence=confidence,
            expected_value=expected_value,
            win_probability=win_probability,
            reasoning=" ".join(reasoning_parts),
            key_insights=[],
            risk_factors=[],
            odds_snapshot=odds_summary,
            research_summary={"source": "espn_free", "text": research[:300] if research else ""},
            model_used="heuristic"
        )

        return decision
    
    def scan_sport(self, sport_key: str, max_events: int = 10,
                   include_research: bool = True,
                   on_decision: Callable = None) -> List[BetDecision]:
        """
        Scan a sport for betting opportunities.
        
        Args:
            sport_key: Sport to scan (e.g., 'americanfootball_nfl')
            max_events: Max events to analyze
            include_research: Include ESPN research
            on_decision: Callback for each decision (real-time updates)
        """
        logger.info(f"[SCAN] Starting: {sport_key}, max_events={max_events}")
        
        callback = on_decision or self._on_decision_callback
        
        # Get odds from The Odds API
        odds_data = self.get_odds_for_sport(sport_key)
        logger.info(f"[SCAN] Got {len(odds_data)} events from Odds API")
        
        decisions = []
        events_to_process = odds_data[:max_events]
        
        for idx, event in enumerate(events_to_process):
            logger.info(f"[SCAN] Event {idx + 1}/{len(events_to_process)}")
            
            try:
                decision = self.analyze_event(
                    event_odds=event,
                    sport_key=sport_key,
                    include_research=include_research
                )
                decisions.append(decision)
                
                # Real-time callback
                if callback:
                    try:
                        callback(decision)
                    except Exception as e:
                        logger.error(f"[SCAN] Callback error: {e}")
                
                # Rate limiting
                if idx < len(events_to_process) - 1:
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"[SCAN] Error analyzing event: {e}")
                continue
        
        logger.info(f"[SCAN] Complete: {len(decisions)} decisions")
        return decisions
    
    def get_recommendations(self, decisions: List[BetDecision],
                           min_confidence: float = None) -> List[BetDecision]:
        """Filter to only recommended bets."""
        min_conf = min_confidence or self.min_confidence
        return [
            d for d in decisions
            if d.decision == "place_bet"
            and d.confidence >= min_conf
            and d.expected_value > 0
        ]
    
    def get_decision_logs(self, limit: int = 100) -> List[Dict]:
        """Get recent decision logs."""
        return self.decision_logs[-limit:]


# Convenience function
def get_engine() -> AIDecisionEngine:
    """Get configured decision engine."""
    return AIDecisionEngine()
