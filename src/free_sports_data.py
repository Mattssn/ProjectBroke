"""
Free Sports Data Client

Aggregates data from FREE public APIs:
- ESPN API (unofficial) - scores, standings, news, injuries, team stats
- Other free sources as needed

This replaces expensive Perplexity calls for basic sports research.
"""
import os
import time
import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import json

logger = logging.getLogger(__name__)


class FreeSportsDataClient:
    """
    Client for free sports data APIs.
    Replaces Perplexity for basic team/injury/news research.
    """
    
    # ESPN API base URLs (unofficial but publicly accessible)
    ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports"
    ESPN_CORE = "https://sports.core.api.espn.com/v2/sports"
    
    # Sport mappings
    SPORT_CONFIG = {
        "americanfootball_nfl": {
            "espn_sport": "football",
            "espn_league": "nfl",
        },
        "americanfootball_ncaaf": {
            "espn_sport": "football", 
            "espn_league": "college-football",
        },
        "basketball_nba": {
            "espn_sport": "basketball",
            "espn_league": "nba",
        },
        "basketball_ncaab": {
            "espn_sport": "basketball",
            "espn_league": "mens-college-basketball",
        },
        "baseball_mlb": {
            "espn_sport": "baseball",
            "espn_league": "mlb",
        },
        "icehockey_nhl": {
            "espn_sport": "hockey",
            "espn_league": "nhl",
        },
    }
    
    def __init__(self):
        self.session = requests.Session()
        # CRITICAL FIX: Bypass system proxy that may block ESPN
        self.session.trust_env = False
        self.session.proxies = {"http": None, "https": None}
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self._cache = {}
        self._cache_ttl = 300  # 5 minute cache
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached data if not expired."""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return data
        return None
    
    def _set_cache(self, key: str, data: Any):
        """Cache data with timestamp."""
        self._cache[key] = (data, time.time())
    
    def _make_request(self, url: str, params: Dict = None) -> Optional[Dict]:
        """Make HTTP request with error handling."""
        try:
            logger.debug(f"[ESPN] Requesting: {url}")
            response = self.session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            logger.debug(f"[ESPN] Success: got {len(str(data))} bytes")
            return data
        except requests.exceptions.Timeout:
            logger.warning(f"[ESPN] Timeout: {url}")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"[ESPN] Connection error: {url} - {e}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.warning(f"[ESPN] HTTP error: {url} - {e}")
            return None
        except Exception as e:
            logger.warning(f"[ESPN] Request failed: {url} - {e}")
            return None
    
    def _get_espn_config(self, sport_key: str) -> Dict:
        """Get ESPN config for a sport."""
        return self.SPORT_CONFIG.get(sport_key, {
            "espn_sport": "football",
            "espn_league": "nfl"
        })
    
    # ==================== Team Data ====================
    
    def get_teams(self, sport_key: str) -> List[Dict]:
        """Get all teams for a sport."""
        cache_key = f"teams_{sport_key}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        config = self._get_espn_config(sport_key)
        url = f"{self.ESPN_BASE}/{config['espn_sport']}/{config['espn_league']}/teams"
        
        data = self._make_request(url)
        if not data:
            return []
        
        teams = []
        for team_group in data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", []):
            team = team_group.get("team", {})
            teams.append({
                "id": team.get("id"),
                "name": team.get("displayName"),
                "abbreviation": team.get("abbreviation"),
                "location": team.get("location"),
                "logo": team.get("logos", [{}])[0].get("href") if team.get("logos") else None
            })
        
        self._set_cache(cache_key, teams)
        return teams
    
    def find_team(self, sport_key: str, team_name: str) -> Optional[Dict]:
        """Find a team by name (fuzzy match)."""
        teams = self.get_teams(sport_key)
        team_name_lower = team_name.lower()
        
        for team in teams:
            if (team_name_lower in team.get("name", "").lower() or
                team_name_lower in team.get("location", "").lower() or
                team.get("abbreviation", "").lower() == team_name_lower):
                return team
        
        return None
    
    # ==================== Standings ====================
    
    def get_standings(self, sport_key: str) -> Dict:
        """Get current standings."""
        cache_key = f"standings_{sport_key}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        config = self._get_espn_config(sport_key)
        url = f"{self.ESPN_BASE}/{config['espn_sport']}/{config['espn_league']}/standings"
        
        data = self._make_request(url)
        if not data:
            return {}
        
        standings = {"divisions": [], "teams": {}}
        
        for group in data.get("children", []):
            division_name = group.get("name", "")
            
            for standing in group.get("standings", {}).get("entries", []):
                team = standing.get("team", {})
                team_id = team.get("id")
                stats = {s.get("name"): s.get("value") for s in standing.get("stats", [])}
                
                standings["teams"][team.get("displayName", "")] = {
                    "id": team_id,
                    "name": team.get("displayName"),
                    "division": division_name,
                    "wins": int(stats.get("wins", 0)),
                    "losses": int(stats.get("losses", 0)),
                    "ties": int(stats.get("ties", 0)),
                    "win_pct": float(stats.get("winPercent", 0)),
                    "points_for": float(stats.get("pointsFor", 0)),
                    "points_against": float(stats.get("pointsAgainst", 0)),
                    "point_diff": float(stats.get("pointDifferential", 0)),
                    "streak": stats.get("streak", ""),
                    "home_record": stats.get("homeRecord", ""),
                    "away_record": stats.get("awayRecord", ""),
                }
        
        self._set_cache(cache_key, standings)
        return standings
    
    def get_team_record(self, sport_key: str, team_name: str) -> Optional[Dict]:
        """Get a specific team's record."""
        standings = self.get_standings(sport_key)
        
        # Try exact match first
        if team_name in standings.get("teams", {}):
            return standings["teams"][team_name]
        
        # Fuzzy match
        team_name_lower = team_name.lower()
        for name, record in standings.get("teams", {}).items():
            if team_name_lower in name.lower():
                return record
        
        return None
    
    # ==================== Injuries ====================
    
    def get_injuries(self, sport_key: str, team_name: str = None) -> List[Dict]:
        """Get injury report for a sport or specific team."""
        cache_key = f"injuries_{sport_key}_{team_name or 'all'}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        config = self._get_espn_config(sport_key)
        
        # Try to get team-specific injuries
        if team_name:
            team = self.find_team(sport_key, team_name)
            if team:
                url = f"{self.ESPN_BASE}/{config['espn_sport']}/{config['espn_league']}/teams/{team['id']}/injuries"
                data = self._make_request(url)
                if data:
                    injuries = self._parse_injuries(data)
                    self._set_cache(cache_key, injuries)
                    return injuries
        
        # Fall back to league-wide injuries
        url = f"{self.ESPN_BASE}/{config['espn_sport']}/{config['espn_league']}/injuries"
        data = self._make_request(url)
        
        if not data:
            return []
        
        injuries = self._parse_injuries(data, team_filter=team_name)
        self._set_cache(cache_key, injuries)
        return injuries
    
    def _parse_injuries(self, data: Dict, team_filter: str = None) -> List[Dict]:
        """Parse injury data from ESPN response."""
        injuries = []
        
        for team_data in data.get("injuries", data.get("teams", [])):
            team_info = team_data.get("team", {})
            team_name = team_info.get("displayName", "")
            
            if team_filter and team_filter.lower() not in team_name.lower():
                continue
            
            for injury in team_data.get("injuries", []):
                athlete = injury.get("athlete", {})
                injuries.append({
                    "team": team_name,
                    "player": athlete.get("displayName", "Unknown"),
                    "position": athlete.get("position", {}).get("abbreviation", ""),
                    "status": injury.get("status", ""),
                    "injury": injury.get("type", {}).get("text", injury.get("description", "")),
                    "details": injury.get("longComment", injury.get("shortComment", "")),
                })
        
        return injuries
    
    # ==================== News ====================
    
    def get_news(self, sport_key: str, team_name: str = None, limit: int = 10) -> List[Dict]:
        """Get recent news for a sport or team."""
        cache_key = f"news_{sport_key}_{team_name or 'all'}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached[:limit]
        
        config = self._get_espn_config(sport_key)
        
        # Try team-specific news
        if team_name:
            team = self.find_team(sport_key, team_name)
            if team:
                url = f"{self.ESPN_BASE}/{config['espn_sport']}/{config['espn_league']}/teams/{team['id']}/news"
                data = self._make_request(url)
                if data and data.get("articles"):
                    news = self._parse_news(data)
                    self._set_cache(cache_key, news)
                    return news[:limit]
        
        # League news
        url = f"{self.ESPN_BASE}/{config['espn_sport']}/{config['espn_league']}/news"
        data = self._make_request(url)
        
        if not data:
            return []
        
        news = self._parse_news(data, team_filter=team_name)
        self._set_cache(cache_key, news)
        return news[:limit]
    
    def _parse_news(self, data: Dict, team_filter: str = None) -> List[Dict]:
        """Parse news data from ESPN response."""
        news = []
        
        for article in data.get("articles", []):
            headline = article.get("headline", "")
            
            # Filter by team if specified
            if team_filter:
                categories = [c.get("description", "") for c in article.get("categories", [])]
                if not any(team_filter.lower() in cat.lower() for cat in categories):
                    if team_filter.lower() not in headline.lower():
                        continue
            
            news.append({
                "headline": headline,
                "description": article.get("description", ""),
                "published": article.get("published", ""),
                "link": article.get("links", {}).get("web", {}).get("href", ""),
            })
        
        return news
    
    # ==================== Scoreboard / Recent Games ====================
    
    def get_scoreboard(self, sport_key: str) -> List[Dict]:
        """Get current/recent games."""
        cache_key = f"scoreboard_{sport_key}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        config = self._get_espn_config(sport_key)
        url = f"{self.ESPN_BASE}/{config['espn_sport']}/{config['espn_league']}/scoreboard"
        
        data = self._make_request(url)
        if not data:
            return []
        
        games = []
        for event in data.get("events", []):
            competition = event.get("competitions", [{}])[0]
            competitors = competition.get("competitors", [])
            
            home = next((c for c in competitors if c.get("homeAway") == "home"), {})
            away = next((c for c in competitors if c.get("homeAway") == "away"), {})
            
            games.append({
                "id": event.get("id"),
                "name": event.get("name"),
                "date": event.get("date"),
                "status": event.get("status", {}).get("type", {}).get("description", ""),
                "home_team": home.get("team", {}).get("displayName"),
                "away_team": away.get("team", {}).get("displayName"),
                "home_score": int(home.get("score", 0)),
                "away_score": int(away.get("score", 0)),
                "venue": competition.get("venue", {}).get("fullName"),
            })
        
        self._set_cache(cache_key, games)
        return games
    
    def get_team_recent_games(self, sport_key: str, team_name: str, limit: int = 5) -> List[Dict]:
        """Get a team's recent game results."""
        team = self.find_team(sport_key, team_name)
        if not team:
            return []
        
        config = self._get_espn_config(sport_key)
        url = f"{self.ESPN_BASE}/{config['espn_sport']}/{config['espn_league']}/teams/{team['id']}/schedule"
        
        data = self._make_request(url)
        if not data:
            return []
        
        games = []
        for event in data.get("events", []):
            competition = event.get("competitions", [{}])[0]
            
            # Only completed games
            if event.get("status", {}).get("type", {}).get("completed", False):
                competitors = competition.get("competitors", [])
                home = next((c for c in competitors if c.get("homeAway") == "home"), {})
                away = next((c for c in competitors if c.get("homeAway") == "away"), {})
                
                # Determine if this team won
                team_competitor = home if home.get("team", {}).get("id") == team["id"] else away
                opponent = away if team_competitor == home else home
                
                games.append({
                    "date": event.get("date"),
                    "opponent": opponent.get("team", {}).get("displayName"),
                    "home": team_competitor.get("homeAway") == "home",
                    "team_score": int(team_competitor.get("score", 0)),
                    "opponent_score": int(opponent.get("score", 0)),
                    "won": team_competitor.get("winner", False),
                    "result": "W" if team_competitor.get("winner") else "L"
                })
        
        # Return most recent games
        return games[:limit]
    
    # ==================== Aggregated Research ====================
    
    def get_team_summary(self, sport_key: str, team_name: str) -> Dict:
        """
        Get comprehensive team summary combining all data sources.
        This replaces a Perplexity research call.
        """
        summary = {
            "team_name": team_name,
            "sport": sport_key,
            "record": None,
            "injuries": [],
            "recent_games": [],
            "news": [],
            "generated_at": datetime.now().isoformat()
        }
        
        # Get record/standings
        record = self.get_team_record(sport_key, team_name)
        if record:
            summary["record"] = record
        
        # Get injuries
        injuries = self.get_injuries(sport_key, team_name)
        summary["injuries"] = injuries[:10]  # Top 10 injuries
        
        # Get recent games
        recent = self.get_team_recent_games(sport_key, team_name, limit=5)
        summary["recent_games"] = recent
        
        # Get news
        news = self.get_news(sport_key, team_name, limit=5)
        summary["news"] = news
        
        return summary
    
    def get_matchup_summary(self, sport_key: str, home_team: str, away_team: str) -> Dict:
        """
        Get comprehensive matchup summary.
        This replaces multiple Perplexity research calls.
        """
        home_summary = self.get_team_summary(sport_key, home_team)
        away_summary = self.get_team_summary(sport_key, away_team)
        
        # Calculate some basic analytics
        home_record = home_summary.get("record") or {}
        away_record = away_summary.get("record") or {}
        
        home_recent = home_summary.get("recent_games") or []
        away_recent = away_summary.get("recent_games") or []
        
        home_form = sum(1 for g in home_recent if g.get("won")) / max(len(home_recent), 1)
        away_form = sum(1 for g in away_recent if g.get("won")) / max(len(away_recent), 1)
        
        # Count significant injuries (starters likely out)
        home_injuries_out = len([i for i in home_summary.get("injuries") or [] 
                                  if i.get("status", "").lower() in ["out", "doubtful"]])
        away_injuries_out = len([i for i in away_summary.get("injuries") or []
                                  if i.get("status", "").lower() in ["out", "doubtful"]])
        
        return {
            "home_team": home_summary,
            "away_team": away_summary,
            "analysis": {
                "home_win_pct": home_record.get("win_pct", 0),
                "away_win_pct": away_record.get("win_pct", 0),
                "home_point_diff": home_record.get("point_diff", 0),
                "away_point_diff": away_record.get("point_diff", 0),
                "home_recent_form": f"{home_form:.0%}",
                "away_recent_form": f"{away_form:.0%}",
                "home_injuries_out": home_injuries_out,
                "away_injuries_out": away_injuries_out,
                "home_home_record": home_record.get("home_record", ""),
                "away_away_record": away_record.get("away_record", ""),
            },
            "generated_at": datetime.now().isoformat()
        }
    
    def format_for_ai_prompt(self, matchup_summary: Dict) -> str:
        """
        Format matchup summary as a concise string for AI prompt.
        Much shorter than raw Perplexity output!
        """
        if not matchup_summary:
            return "Research data unavailable."
        
        home = matchup_summary.get("home_team") or {}
        away = matchup_summary.get("away_team") or {}
        analysis = matchup_summary.get("analysis") or {}
        
        home_record = home.get("record") or {}
        away_record = away.get("record") or {}
        
        # Handle case where we have no data
        if not home_record and not away_record:
            home_name = home.get('team_name', 'Home Team')
            away_name = away.get('team_name', 'Away Team')
            return f"Limited data available for {away_name} @ {home_name}. Analyze based on odds."
        
        lines = [
            f"=== MATCHUP: {away.get('team_name', 'Away')} @ {home.get('team_name', 'Home')} ===",
            "",
            f"HOME ({home.get('team_name', 'N/A')}):",
            f"  Record: {home_record.get('wins', 0)}-{home_record.get('losses', 0)} ({analysis.get('home_win_pct', 0):.1%})",
            f"  Home Record: {analysis.get('home_home_record', 'N/A')}",
            f"  Point Diff: {analysis.get('home_point_diff', 0):+.1f}",
            f"  Last 5 Form: {analysis.get('home_recent_form', 'N/A')}",
            f"  Key Injuries Out: {analysis.get('home_injuries_out', 0)}",
        ]
        
        # Add injury details
        home_injuries = home.get("injuries") or []
        if home_injuries:
            inj_str = ', '.join(f"{i['player']} ({i['status']})" for i in home_injuries[:3])
            lines.append(f"  Injuries: {inj_str}")
        
        lines.extend([
            "",
            f"AWAY ({away.get('team_name', 'N/A')}):",
            f"  Record: {away_record.get('wins', 0)}-{away_record.get('losses', 0)} ({analysis.get('away_win_pct', 0):.1%})",
            f"  Away Record: {analysis.get('away_away_record', 'N/A')}",
            f"  Point Diff: {analysis.get('away_point_diff', 0):+.1f}",
            f"  Last 5 Form: {analysis.get('away_recent_form', 'N/A')}",
            f"  Key Injuries Out: {analysis.get('away_injuries_out', 0)}",
        ])
        
        away_injuries = away.get("injuries") or []
        if away_injuries:
            inj_str = ', '.join(f"{i['player']} ({i['status']})" for i in away_injuries[:3])
            lines.append(f"  Injuries: {inj_str}")
        
        # Recent results
        home_recent = home.get("recent_games") or []
        away_recent = away.get("recent_games") or []
        
        if home_recent or away_recent:
            lines.extend(["", "RECENT RESULTS:"])
            for game in home_recent[:3]:
                lines.append(f"  {home.get('team_name', 'Home')}: {game.get('result')} vs {game.get('opponent')} ({game.get('team_score')}-{game.get('opponent_score')})")
            for game in away_recent[:3]:
                lines.append(f"  {away.get('team_name', 'Away')}: {game.get('result')} vs {game.get('opponent')} ({game.get('team_score')}-{game.get('opponent_score')})")
        
        return "\n".join(lines)


# Convenience function
def get_client() -> FreeSportsDataClient:
    """Get a configured free sports data client."""
    return FreeSportsDataClient()


# Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    client = FreeSportsDataClient()
    
    print("Testing ESPN API (with proxy bypass)...")
    
    # Test standings
    print("\n=== NFL Standings ===")
    standings = client.get_standings("americanfootball_nfl")
    for team, record in list(standings.get("teams", {}).items())[:5]:
        print(f"  {team}: {record.get('wins')}-{record.get('losses')}")
    
    # Test injuries
    print("\n=== Chiefs Injuries ===")
    injuries = client.get_injuries("americanfootball_nfl", "Chiefs")
    for inj in injuries[:3]:
        print(f"  {inj.get('player')} ({inj.get('position')}): {inj.get('status')} - {inj.get('injury')}")
    
    # Test matchup summary
    print("\n=== Matchup Summary ===")
    matchup = client.get_matchup_summary("americanfootball_nfl", "Las Vegas Raiders", "New York Giants")
    print(client.format_for_ai_prompt(matchup))
