"""
Sports Odds API Client

Client for The Odds API (https://the-odds-api.com) providing:
- Real-time sports betting odds from 50+ bookmakers
- Multiple sports (NFL, NBA, MLB, NHL, Soccer, etc.)
- Various betting markets (moneyline, spreads, totals, props)
- Live scores and historical data

API Documentation: https://the-odds-api.com/liveapi/guides/v4/
"""
import os
import time
import requests
from datetime import datetime
from typing import List, Dict, Optional, Any


class SportsOddsClient:
    """
    Client for The Odds API for sports betting data.
    """
    
    BASE_URL = "https://api.the-odds-api.com/v4"
    
    # Major sports keys
    SPORTS = {
        "nfl": "americanfootball_nfl",
        "ncaaf": "americanfootball_ncaaf",
        "nba": "basketball_nba",
        "ncaab": "basketball_ncaab",
        "wnba": "basketball_wnba",
        "mlb": "baseball_mlb",
        "nhl": "icehockey_nhl",
        "mma": "mma_mixed_martial_arts",
        "soccer_epl": "soccer_epl",
        "soccer_mls": "soccer_usa_mls",
        "soccer_champions": "soccer_uefa_champs_league",
        "tennis_atp": "tennis_atp_us_open",
        "golf_pga": "golf_pga_championship_winner",
    }
    
    # US region bookmakers
    US_BOOKMAKERS = [
        "draftkings", "fanduel", "betmgm", "caesars", 
        "pointsbetus", "bovada", "betonlineag", "betrivers",
        "barstool", "unibet_us", "williamhill_us"
    ]
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ODDS_API_KEY")
        self.session = requests.Session()
        
        # Track API usage
        self.requests_remaining = None
        self.requests_used = None
        
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Execute an API request."""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        
        if params is None:
            params = {}
        params["apiKey"] = self.api_key
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            
            # Track usage from headers
            self.requests_remaining = response.headers.get("x-requests-remaining")
            self.requests_used = response.headers.get("x-requests-used")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Odds API request failed: {e}")
            return None
    
    def get_usage(self) -> Dict:
        """Get API usage statistics."""
        return {
            "remaining": self.requests_remaining,
            "used": self.requests_used
        }
    
    # ==================== Sports ====================
    
    def get_sports(self, all_sports: bool = False) -> List[Dict]:
        """
        Get list of available sports.
        
        Args:
            all_sports: Include out-of-season sports
        
        Returns:
            List of sport objects with keys like 'key', 'group', 'title', 'active'
        """
        params = {}
        if all_sports:
            params["all"] = "true"
        
        return self._make_request("sports", params) or []
    
    def get_in_season_sports(self) -> List[str]:
        """Get list of currently in-season sport keys."""
        sports = self.get_sports()
        return [s["key"] for s in sports if s.get("active")]
    
    # ==================== Events ====================
    
    def get_events(self, sport: str, event_ids: str = None,
                   commence_time_from: str = None,
                   commence_time_to: str = None) -> List[Dict]:
        """
        Get list of events for a sport.
        
        Args:
            sport: Sport key (e.g., 'americanfootball_nfl')
            event_ids: Comma-separated event IDs to filter
            commence_time_from: ISO 8601 datetime filter
            commence_time_to: ISO 8601 datetime filter
        
        Returns:
            List of events with id, home_team, away_team, commence_time
        """
        params = {}
        if event_ids:
            params["eventIds"] = event_ids
        if commence_time_from:
            params["commenceTimeFrom"] = commence_time_from
        if commence_time_to:
            params["commenceTimeTo"] = commence_time_to
        
        return self._make_request(f"sports/{sport}/events", params) or []
    
    # ==================== Odds ====================
    
    def get_odds(self, sport: str, regions: str = "us",
                 markets: str = "h2h", odds_format: str = "american",
                 bookmakers: str = None, event_ids: str = None) -> List[Dict]:
        """
        Get odds for upcoming/live events.
        
        Args:
            sport: Sport key
            regions: Comma-separated regions ('us', 'uk', 'eu', 'au')
            markets: Comma-separated markets ('h2h', 'spreads', 'totals')
            odds_format: 'decimal' or 'american'
            bookmakers: Comma-separated bookmaker keys
            event_ids: Filter to specific events
        
        Returns:
            List of events with bookmaker odds
        """
        params = {
            "regions": regions,
            "markets": markets,
            "oddsFormat": odds_format
        }
        if bookmakers:
            params["bookmakers"] = bookmakers
        if event_ids:
            params["eventIds"] = event_ids
        
        return self._make_request(f"sports/{sport}/odds", params) or []
    
    def get_event_odds(self, sport: str, event_id: str,
                       regions: str = "us", markets: str = "h2h",
                       odds_format: str = "american") -> Optional[Dict]:
        """
        Get detailed odds for a specific event.
        
        This endpoint supports additional markets like player props.
        
        Args:
            sport: Sport key
            event_id: Event ID from get_events()
            regions: Bookmaker regions
            markets: Betting markets (can include player props)
            odds_format: 'decimal' or 'american'
        
        Returns:
            Event with detailed bookmaker odds
        """
        params = {
            "regions": regions,
            "markets": markets,
            "oddsFormat": odds_format
        }
        
        return self._make_request(f"sports/{sport}/events/{event_id}/odds", params)
    
    def get_upcoming_games(self, sport: str, regions: str = "us",
                          markets: str = "h2h,spreads,totals") -> List[Dict]:
        """
        Convenience method to get upcoming games with all main markets.
        
        Returns odds from US bookmakers for moneyline, spreads, and totals.
        """
        return self.get_odds(
            sport=sport,
            regions=regions,
            markets=markets,
            odds_format="american"
        )
    
    # ==================== Scores ====================
    
    def get_scores(self, sport: str, days_from: int = None,
                   event_ids: str = None) -> List[Dict]:
        """
        Get scores for live and recently completed games.
        
        Args:
            sport: Sport key
            days_from: Include completed games from past N days (1-3)
            event_ids: Filter to specific events
        
        Returns:
            List of events with scores
        """
        params = {}
        if days_from:
            params["daysFrom"] = days_from
        if event_ids:
            params["eventIds"] = event_ids
        
        return self._make_request(f"sports/{sport}/scores", params) or []
    
    # ==================== Analysis Helpers ====================
    
    def find_best_odds(self, odds_data: List[Dict], 
                       team: str = None) -> Dict[str, Any]:
        """
        Find the best available odds across bookmakers.
        
        Args:
            odds_data: Response from get_odds()
            team: Optional team name to filter
        
        Returns:
            Dict with best odds for each team in each event
        """
        results = []
        
        for event in odds_data:
            home = event.get("home_team")
            away = event.get("away_team")
            
            if team and team not in [home, away]:
                continue
            
            best_odds = {
                "event_id": event.get("id"),
                "home_team": home,
                "away_team": away,
                "commence_time": event.get("commence_time"),
                "best_home": {"odds": float("-inf"), "bookmaker": None},
                "best_away": {"odds": float("-inf"), "bookmaker": None}
            }
            
            for bookmaker in event.get("bookmakers", []):
                for market in bookmaker.get("markets", []):
                    if market.get("key") == "h2h":
                        for outcome in market.get("outcomes", []):
                            name = outcome.get("name")
                            price = outcome.get("price", 0)
                            
                            if name == home and price > best_odds["best_home"]["odds"]:
                                best_odds["best_home"] = {
                                    "odds": price,
                                    "bookmaker": bookmaker.get("title")
                                }
                            elif name == away and price > best_odds["best_away"]["odds"]:
                                best_odds["best_away"] = {
                                    "odds": price,
                                    "bookmaker": bookmaker.get("title")
                                }
            
            results.append(best_odds)
        
        return results
    
    def get_consensus_odds(self, odds_data: List[Dict]) -> List[Dict]:
        """
        Calculate consensus (average) odds across bookmakers.
        
        Args:
            odds_data: Response from get_odds()
        
        Returns:
            List of events with average odds
        """
        results = []
        
        for event in odds_data:
            home = event.get("home_team")
            away = event.get("away_team")
            
            home_odds = []
            away_odds = []
            
            for bookmaker in event.get("bookmakers", []):
                for market in bookmaker.get("markets", []):
                    if market.get("key") == "h2h":
                        for outcome in market.get("outcomes", []):
                            name = outcome.get("name")
                            price = outcome.get("price", 0)
                            
                            if name == home:
                                home_odds.append(price)
                            elif name == away:
                                away_odds.append(price)
            
            consensus = {
                "event_id": event.get("id"),
                "home_team": home,
                "away_team": away,
                "commence_time": event.get("commence_time"),
                "home_consensus": sum(home_odds) / len(home_odds) if home_odds else None,
                "away_consensus": sum(away_odds) / len(away_odds) if away_odds else None,
                "bookmaker_count": len(event.get("bookmakers", []))
            }
            
            results.append(consensus)
        
        return results
    
    def american_to_implied_prob(self, odds: int) -> float:
        """Convert American odds to implied probability."""
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)
    
    def implied_prob_to_american(self, prob: float) -> int:
        """Convert implied probability to American odds."""
        if prob <= 0 or prob >= 1:
            return 0
        
        if prob > 0.5:
            return int(-100 * prob / (1 - prob))
        else:
            return int(100 * (1 - prob) / prob)


# Convenience function
def get_client() -> SportsOddsClient:
    """Get a configured Sports Odds API client."""
    return SportsOddsClient()
