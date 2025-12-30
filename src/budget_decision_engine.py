"""
Budget Decision Engine

Uses FREE data sources + cheap AI model for ~98% cost reduction:
- ESPN API (free) for standings, injuries, news, recent games
- GPT-4o-mini (~$0.15/1M input, $0.60/1M output) instead of Claude Sonnet
- Summarized odds (not full dump)
- Concise prompts

Cost comparison:
- Original: ~$0.54 per scan (5 events)
- Budget:   ~$0.01 per scan (5 events)
"""
import os
import json
import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass

from .free_sports_data import FreeSportsDataClient
from .sports_odds_client import SportsOddsClient
from .openrouter_client import OpenRouterClient
from .kalshi_client import KalshiClient

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


class BudgetDecisionEngine:
    """
    Budget-friendly decision engine using free data sources.
    
    Cost: ~$0.002 per event vs ~$0.11 per event (original)
    """
    
    # Use the cheapest effective model
    DEFAULT_MODEL = "openai/gpt-4o-mini"  # ~50x cheaper than Claude Sonnet
    
    SPORT_MAPPING = {
        "americanfootball_nfl": "NFL",
        "americanfootball_ncaaf": "NCAAF", 
        "basketball_nba": "NBA",
        "basketball_ncaab": "NCAAB",
        "baseball_mlb": "MLB",
        "icehockey_nhl": "NHL",
    }
    
    def __init__(self, model: str = None):
        self.free_data = FreeSportsDataClient()
        self.odds = SportsOddsClient()
        self.ai = OpenRouterClient()
        self.kalshi = KalshiClient()
        
        self.model = model or self.DEFAULT_MODEL
        self.min_confidence = float(os.getenv("MIN_CONFIDENCE", "0.6"))
        
        self._on_decision_callback: Optional[Callable] = None
        self.decision_logs = []
    
    def set_decision_callback(self, callback: Callable):
        self._on_decision_callback = callback
    
    def summarize_odds(self, event_odds: Dict) -> Dict:
        """
        Create a CONCISE odds summary instead of dumping everything.
        Reduces tokens by ~80%.
        """
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
            book_name = bookmaker.get("key", "")
            
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
        
        # Calculate consensus/best odds
        def avg(lst): return sum(lst) / len(lst) if lst else 0
        def best(lst): return max(lst) if lst else 0
        
        return {
            "home_team": home_team,
            "away_team": away_team,
            "moneyline": {
                "home_consensus": int(avg(summary["moneyline"]["home"])),
                "away_consensus": int(avg(summary["moneyline"]["away"])),
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
    
    def get_free_research(self, sport_key: str, home_team: str, away_team: str) -> str:
        """
        Get research from FREE ESPN API instead of Perplexity.
        Returns a concise formatted string for the AI prompt.
        """
        try:
            matchup = self.free_data.get_matchup_summary(sport_key, home_team, away_team)
            return self.free_data.format_for_ai_prompt(matchup)
        except Exception as e:
            logger.warning(f"Free data fetch failed: {e}")
            return f"Research unavailable. Analyzing {away_team} @ {home_team} based on odds only."
    
    def generate_decision(self, event_odds: Dict, sport_key: str, 
                          include_research: bool = True) -> BetDecision:
        """
        Generate a betting decision using free data + cheap AI.
        
        Total cost: ~$0.002 per event
        """
        start_time = time.time()
        
        event_id = event_odds.get("id", "unknown")
        home_team = event_odds.get("home_team", "")
        away_team = event_odds.get("away_team", "")
        commence_time = event_odds.get("commence_time", "")
        
        logger.info(f"[BUDGET] Analyzing: {away_team} @ {home_team}")
        
        # Step 1: Summarize odds (not full dump)
        odds_summary = self.summarize_odds(event_odds)
        
        # Step 2: Get FREE research
        research_text = ""
        if include_research:
            research_text = self.get_free_research(sport_key, home_team, away_team)
        
        # Step 3: Build CONCISE prompt (key to saving tokens!)
        prompt = self._build_concise_prompt(odds_summary, research_text)
        
        # Step 4: Call cheap AI model
        logger.info(f"[BUDGET] Calling {self.model}...")
        
        try:
            response = self.ai.get_json_response(
                prompt=prompt,
                model=self.model,
                system_prompt="""You are a sports betting analyst. Analyze the data and respond with a JSON betting decision.
Be concise. Only recommend bets with clear edge (>5% expected value)."""
            )
            
            if "error" in response:
                logger.error(f"AI error: {response['error']}")
                response = {"decision": "skip", "reasoning": "AI analysis failed"}
        
        except Exception as e:
            logger.error(f"AI call failed: {e}")
            response = {"decision": "skip", "reasoning": str(e)}
        
        execution_time = int((time.time() - start_time) * 1000)
        logger.info(f"[BUDGET] Complete in {execution_time}ms - Decision: {response.get('decision', 'skip')}")
        
        # Build decision object
        decision = BetDecision(
            event_id=event_id,
            event_name=f"{away_team} @ {home_team}",
            sport=sport_key,
            home_team=home_team,
            away_team=away_team,
            commence_time=commence_time,
            decision=response.get("decision", "skip"),
            bet_type=response.get("bet_type"),
            bet_side=response.get("bet_side"),
            bet_amount_usd=response.get("bet_amount_usd"),
            confidence=response.get("confidence", 0),
            expected_value=response.get("expected_value", 0),
            win_probability=response.get("win_probability", 0),
            reasoning=response.get("reasoning", ""),
            key_insights=response.get("key_insights", []),
            risk_factors=response.get("risk_factors", []),
            odds_snapshot=odds_summary,
            research_summary={"text": research_text[:500]},  # Truncate for storage
            model_used=self.model
        )
        
        return decision
    
    def _build_concise_prompt(self, odds: Dict, research: str) -> str:
        """
        Build a SHORT prompt to minimize tokens.
        Target: <1000 tokens input
        """
        prompt = f"""Analyze this betting opportunity:

ODDS:
- Moneyline: {odds['home_team']} {odds['moneyline']['home_consensus']}, {odds['away_team']} {odds['moneyline']['away_consensus']}
- Spread: {odds['home_team']} {odds['spread']['home_line']} ({odds['spread']['home_odds']}), {odds['away_team']} {odds['spread']['away_line']} ({odds['spread']['away_odds']})
- Total: {odds['total']['line']} (O {odds['total']['over_odds']} / U {odds['total']['under_odds']})
- Sources: {odds['bookmaker_count']} bookmakers

{research if research else 'No additional research available.'}

Respond in JSON:
{{
  "decision": "place_bet" or "skip",
  "bet_type": "moneyline", "spread", or "total" (if betting),
  "bet_side": "home", "away", "over", or "under" (if betting),
  "confidence": 0.0-1.0,
  "expected_value": percentage as decimal (e.g., 0.05 for 5%),
  "win_probability": 0.0-1.0,
  "reasoning": "brief explanation",
  "key_insights": ["insight1", "insight2"],
  "risk_factors": ["risk1", "risk2"]
}}

Only recommend bets with confidence >0.6 and expected_value >0.03."""
        
        return prompt
    
    def scan_sport(self, sport_key: str, max_events: int = 10,
                   include_research: bool = True,
                   on_decision: Callable = None) -> List[BetDecision]:
        """
        Scan a sport for betting opportunities.
        """
        logger.info(f"[BUDGET-SCAN] Starting: {sport_key}, max_events={max_events}")
        
        callback = on_decision or self._on_decision_callback
        
        # Get odds
        odds_data = self.odds.get_odds(
            sport=sport_key,
            regions="us",
            markets="h2h,spreads,totals",
            odds_format="american"
        )
        
        logger.info(f"[BUDGET-SCAN] Got {len(odds_data)} events")
        
        decisions = []
        
        for idx, event in enumerate(odds_data[:max_events]):
            logger.info(f"[BUDGET-SCAN] Event {idx + 1}/{min(len(odds_data), max_events)}")
            
            try:
                decision = self.generate_decision(
                    event_odds=event,
                    sport_key=sport_key,
                    include_research=include_research
                )
                decisions.append(decision)
                
                if callback:
                    try:
                        callback(decision)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
                
                # Small delay for rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error analyzing event: {e}")
                continue
        
        logger.info(f"[BUDGET-SCAN] Complete: {len(decisions)} decisions")
        return decisions
    
    def get_recommendations(self, decisions: List[BetDecision]) -> List[BetDecision]:
        """Filter to only recommended bets."""
        return [
            d for d in decisions
            if d.decision == "place_bet"
            and d.confidence >= self.min_confidence
            and d.expected_value > 0
        ]
    
    def get_decision_logs(self, limit: int = 100) -> List[Dict]:
        return self.decision_logs[-limit:]


# For backwards compatibility - use budget engine as default
AIDecisionEngine = BudgetDecisionEngine


def get_engine() -> BudgetDecisionEngine:
    """Get a budget decision engine."""
    return BudgetDecisionEngine()


# Quick test
if __name__ == "__main__":
    engine = BudgetDecisionEngine()
    
    # Test with mock odds
    mock_event = {
        "id": "test123",
        "home_team": "Kansas City Chiefs",
        "away_team": "Buffalo Bills",
        "commence_time": "2024-01-21T18:30:00Z",
        "bookmakers": [
            {
                "key": "draftkings",
                "markets": [
                    {"key": "h2h", "outcomes": [
                        {"name": "Kansas City Chiefs", "price": -150},
                        {"name": "Buffalo Bills", "price": 130}
                    ]},
                    {"key": "spreads", "outcomes": [
                        {"name": "Kansas City Chiefs", "price": -110, "point": -3.5},
                        {"name": "Buffalo Bills", "price": -110, "point": 3.5}
                    ]},
                    {"key": "totals", "outcomes": [
                        {"name": "Over", "price": -110, "point": 47.5},
                        {"name": "Under", "price": -110, "point": 47.5}
                    ]}
                ]
            }
        ]
    }
    
    print("Testing odds summary...")
    summary = engine.summarize_odds(mock_event)
    print(json.dumps(summary, indent=2))
