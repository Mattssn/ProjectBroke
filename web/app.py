"""
Kalshi Sports Betting Dashboard

Web dashboard providing:
- Live portfolio overview
- Real-time trading activity
- Performance charts
- Risk metrics
- AI decision logs
- Sports odds monitoring

Built with Flask and modern frontend technologies.
"""
import os
import json
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import threading
import time

# Import our modules
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.kalshi_client import KalshiClient
from src.sports_odds_client import SportsOddsClient
from src.perplexity_client import PerplexityClient
from src.openrouter_client import OpenRouterClient
from src.decision_engine import AIDecisionEngine, BetDecision


# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Global instances
kalshi_client = None
odds_client = None
decision_engine = None

# Cache for dashboard data
dashboard_cache = {
    "portfolio": None,
    "positions": None,
    "recent_trades": None,
    "sports_odds": {},
    "decisions": [],
    "last_update": None
}
cache_lock = threading.Lock()


def init_clients():
    """Initialize API clients."""
    global kalshi_client, odds_client, decision_engine
    
    kalshi_client = KalshiClient()
    odds_client = SportsOddsClient()
    decision_engine = AIDecisionEngine()


def update_cache():
    """Background thread to update cached data."""
    global dashboard_cache
    
    while True:
        try:
            with cache_lock:
                # Update portfolio
                if kalshi_client:
                    balance = kalshi_client.get_balance() or {}
                    positions = kalshi_client.get_positions() or {}
                    fills = kalshi_client.get_fills(limit=50) or {}
                    
                    dashboard_cache["portfolio"] = {
                        "balance_cents": balance.get("balance", 0),
                        "balance_usd": balance.get("balance", 0) / 100,
                        "portfolio_value_cents": balance.get("portfolio_value", 0),
                        "portfolio_value_usd": balance.get("portfolio_value", 0) / 100,
                    }
                    
                    dashboard_cache["positions"] = positions.get("market_positions", [])
                    dashboard_cache["recent_trades"] = fills.get("fills", [])[:20]
                
                dashboard_cache["last_update"] = datetime.now(timezone.utc).isoformat()
                
        except Exception as e:
            print(f"Cache update error: {e}")
        
        time.sleep(30)  # Update every 30 seconds


# ==================== API Routes ====================

@app.route('/api/portfolio')
def get_portfolio():
    """Get current portfolio summary."""
    with cache_lock:
        return jsonify({
            "success": True,
            "data": dashboard_cache.get("portfolio", {}),
            "updated_at": dashboard_cache.get("last_update")
        })


@app.route('/api/positions')
def get_positions():
    """Get current positions."""
    with cache_lock:
        return jsonify({
            "success": True,
            "data": dashboard_cache.get("positions", []),
            "updated_at": dashboard_cache.get("last_update")
        })


@app.route('/api/trades')
def get_trades():
    """Get recent trades/fills."""
    with cache_lock:
        return jsonify({
            "success": True,
            "data": dashboard_cache.get("recent_trades", []),
            "updated_at": dashboard_cache.get("last_update")
        })


@app.route('/api/odds/<sport>')
def get_odds(sport):
    """Get current odds for a sport."""
    try:
        odds = odds_client.get_odds(
            sport=sport,
            regions="us",
            markets="h2h,spreads,totals",
            odds_format="american"
        )
        return jsonify({
            "success": True,
            "sport": sport,
            "events": odds,
            "count": len(odds)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/sports')
def get_sports():
    """Get list of available sports."""
    try:
        sports = odds_client.get_sports()
        return jsonify({
            "success": True,
            "sports": [s for s in sports if s.get("active")]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/analyze', methods=['POST'])
def analyze_event():
    """Analyze a specific event."""
    data = request.get_json()
    
    event_id = data.get("event_id")
    sport = data.get("sport")
    include_research = data.get("include_research", True)
    
    if not event_id or not sport:
        return jsonify({"success": False, "error": "Missing event_id or sport"}), 400
    
    try:
        # Get odds for the event
        odds = odds_client.get_odds(
            sport=sport,
            regions="us",
            markets="h2h,spreads,totals",
            odds_format="american"
        )
        
        # Find the specific event
        event = next((e for e in odds if e.get("id") == event_id), None)
        
        if not event:
            return jsonify({"success": False, "error": "Event not found"}), 404
        
        # Analyze
        decision = decision_engine.analyze_event(
            event_odds=event,
            sport_key=sport,
            include_research=include_research
        )
        
        # Store in cache
        with cache_lock:
            dashboard_cache["decisions"].append({
                "decision": decision.__dict__,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            # Keep only last 100 decisions
            dashboard_cache["decisions"] = dashboard_cache["decisions"][-100:]
        
        return jsonify({
            "success": True,
            "decision": decision.__dict__
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/decisions')
def get_decisions():
    """Get recent AI decisions."""
    with cache_lock:
        return jsonify({
            "success": True,
            "decisions": dashboard_cache.get("decisions", [])[-50:],
            "count": len(dashboard_cache.get("decisions", []))
        })


@app.route('/api/decision-logs')
def get_decision_logs():
    """Get detailed decision logs."""
    try:
        logs = decision_engine.get_decision_logs(limit=100)
        return jsonify({
            "success": True,
            "logs": logs
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/research', methods=['POST'])
def research_matchup():
    """Research a specific matchup."""
    data = request.get_json()
    
    home_team = data.get("home_team")
    away_team = data.get("away_team")
    sport = data.get("sport", "")
    
    if not home_team or not away_team:
        return jsonify({"success": False, "error": "Missing team names"}), 400
    
    try:
        research = decision_engine.research_event(
            home_team=home_team,
            away_team=away_team,
            sport=sport
        )
        
        return jsonify({
            "success": True,
            "research": research
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/scan/<sport>')
def scan_sport(sport):
    """Scan a sport for betting opportunities."""
    max_events = request.args.get('max_events', 5, type=int)
    include_research = request.args.get('research', 'true').lower() == 'true'
    
    try:
        decisions = decision_engine.scan_sport(
            sport_key=sport,
            max_events=max_events,
            include_research=include_research
        )
        
        # Get recommendations
        recommendations = decision_engine.get_recommendations(decisions)
        
        return jsonify({
            "success": True,
            "sport": sport,
            "total_analyzed": len(decisions),
            "recommendations": len(recommendations),
            "decisions": [d.__dict__ for d in decisions],
            "recommended": [d.__dict__ for d in recommendations]
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/kalshi/markets')
def get_kalshi_markets():
    """Get Kalshi markets."""
    limit = request.args.get('limit', 50, type=int)
    status = request.args.get('status', 'open')
    
    try:
        markets = kalshi_client.get_markets(limit=limit, status=status)
        return jsonify({
            "success": True,
            "markets": markets,
            "count": len(markets)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "clients": {
            "kalshi": kalshi_client is not None,
            "odds": odds_client is not None,
            "decision_engine": decision_engine is not None
        }
    })


# ==================== Page Routes ====================

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')


@app.route('/portfolio')
def portfolio_page():
    """Portfolio details page."""
    return render_template('portfolio.html')


@app.route('/analysis')
def analysis_page():
    """Analysis and research page."""
    return render_template('analysis.html')


@app.route('/decisions')
def decisions_page():
    """AI decisions log page."""
    return render_template('decisions.html')


# ==================== Main ====================

def create_app():
    """Create and configure the Flask application."""
    init_clients()
    
    # Start background cache updater
    cache_thread = threading.Thread(target=update_cache, daemon=True)
    cache_thread.start()
    
    return app


if __name__ == '__main__':
    app = create_app()
    
    # Get port from environment or use default
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    print(f"Starting dashboard on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
