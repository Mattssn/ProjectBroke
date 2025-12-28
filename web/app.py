"""
Kalshi Sports Betting Dashboard - Enhanced with Bot Control

Full-featured web dashboard providing:
- Live portfolio overview and monitoring
- Real-time trading activity feed
- Bot control panel (start/stop, parameters)
- Manual trade execution
- AI decision configuration
- Market scanner controls
- Settings management

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

# Bot state management
bot_state = {
    "running": False,
    "auto_trade": False,
    "last_scan": None,
    "current_sport": None,
    "scan_interval": 300,  # 5 minutes default
    "errors": []
}

# Bot configuration (modifiable at runtime)
bot_config = {
    "min_confidence": float(os.getenv("MIN_CONFIDENCE", "0.6")),
    "min_edge": float(os.getenv("MIN_EDGE", "0.03")),
    "max_bet_pct": float(os.getenv("MAX_BET_PCT", "0.02")),
    "max_position_size": int(os.getenv("MAX_POSITION_SIZE", "1000")),
    "min_profit_cents": int(os.getenv("MIN_PROFIT_CENTS", "2")),
    "enabled_sports": ["americanfootball_nfl", "basketball_nba"],
    "auto_execute": False,
    "use_research": True,
    "max_daily_trades": 10,
    "max_daily_loss": 100.0,  # dollars
    "preferred_model": "anthropic/claude-3.5-sonnet"
}

# Trading stats
trading_stats = {
    "trades_today": 0,
    "daily_pnl": 0.0,
    "total_analyzed": 0,
    "total_recommended": 0,
    "last_reset": datetime.now(timezone.utc).date().isoformat()
}

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

# Background scanner thread
scanner_thread = None
scanner_stop_event = threading.Event()


def init_clients():
    """Initialize API clients."""
    global kalshi_client, odds_client, decision_engine
    
    kalshi_client = KalshiClient()
    odds_client = SportsOddsClient()
    decision_engine = AIDecisionEngine()


def reset_daily_stats():
    """Reset daily trading statistics."""
    global trading_stats
    today = datetime.now(timezone.utc).date().isoformat()
    if trading_stats["last_reset"] != today:
        trading_stats = {
            "trades_today": 0,
            "daily_pnl": 0.0,
            "total_analyzed": 0,
            "total_recommended": 0,
            "last_reset": today
        }


def background_scanner():
    """Background thread for continuous market scanning."""
    global bot_state, trading_stats
    
    while not scanner_stop_event.is_set():
        if bot_state["running"]:
            try:
                reset_daily_stats()
                
                # Check daily limits
                if trading_stats["trades_today"] >= bot_config["max_daily_trades"]:
                    bot_state["errors"].append({
                        "time": datetime.now(timezone.utc).isoformat(),
                        "message": "Daily trade limit reached"
                    })
                    time.sleep(60)
                    continue
                
                if trading_stats["daily_pnl"] <= -bot_config["max_daily_loss"]:
                    bot_state["errors"].append({
                        "time": datetime.now(timezone.utc).isoformat(),
                        "message": "Daily loss limit reached"
                    })
                    time.sleep(60)
                    continue
                
                # Scan each enabled sport
                for sport in bot_config["enabled_sports"]:
                    if scanner_stop_event.is_set():
                        break
                    
                    bot_state["current_sport"] = sport
                    
                    try:
                        decisions = decision_engine.scan_sport(
                            sport_key=sport,
                            max_events=5,
                            include_research=bot_config["use_research"]
                        )
                        
                        trading_stats["total_analyzed"] += len(decisions)
                        
                        # Filter recommendations
                        recommendations = [
                            d for d in decisions
                            if d.decision == "place_bet"
                            and d.confidence >= bot_config["min_confidence"]
                            and d.expected_value >= bot_config["min_edge"]
                        ]
                        
                        trading_stats["total_recommended"] += len(recommendations)
                        
                        # Store decisions
                        with cache_lock:
                            for d in decisions:
                                dashboard_cache["decisions"].append({
                                    "decision": d.__dict__,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                })
                            # Keep only last 200 decisions
                            dashboard_cache["decisions"] = dashboard_cache["decisions"][-200:]
                        
                        # Auto-execute if enabled
                        if bot_config["auto_execute"] and bot_state["auto_trade"]:
                            for rec in recommendations[:3]:  # Max 3 per scan
                                if trading_stats["trades_today"] >= bot_config["max_daily_trades"]:
                                    break
                                
                                # Execute trade logic would go here
                                # For safety, this is left as a placeholder
                                trading_stats["trades_today"] += 1
                    
                    except Exception as e:
                        bot_state["errors"].append({
                            "time": datetime.now(timezone.utc).isoformat(),
                            "message": f"Scan error for {sport}: {str(e)}"
                        })
                    
                    # Rate limiting between sports
                    time.sleep(2)
                
                bot_state["last_scan"] = datetime.now(timezone.utc).isoformat()
                bot_state["current_sport"] = None
                
            except Exception as e:
                bot_state["errors"].append({
                    "time": datetime.now(timezone.utc).isoformat(),
                    "message": f"Scanner error: {str(e)}"
                })
            
            # Keep only last 50 errors
            bot_state["errors"] = bot_state["errors"][-50:]
        
        # Wait for next scan interval
        scanner_stop_event.wait(bot_state["scan_interval"])


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


# ==================== Bot Control API Routes ====================

@app.route('/api/bot/status')
def get_bot_status():
    """Get current bot status and state."""
    return jsonify({
        "success": True,
        "state": bot_state,
        "config": bot_config,
        "stats": trading_stats
    })


@app.route('/api/bot/start', methods=['POST'])
def start_bot():
    """Start the bot scanner."""
    global bot_state, scanner_thread
    
    if bot_state["running"]:
        return jsonify({"success": False, "error": "Bot is already running"})
    
    bot_state["running"] = True
    bot_state["errors"] = []
    
    # Start scanner thread if not running
    if scanner_thread is None or not scanner_thread.is_alive():
        scanner_stop_event.clear()
        scanner_thread = threading.Thread(target=background_scanner, daemon=True)
        scanner_thread.start()
    
    return jsonify({
        "success": True,
        "message": "Bot started",
        "state": bot_state
    })


@app.route('/api/bot/stop', methods=['POST'])
def stop_bot():
    """Stop the bot scanner."""
    global bot_state
    
    bot_state["running"] = False
    bot_state["current_sport"] = None
    
    return jsonify({
        "success": True,
        "message": "Bot stopped",
        "state": bot_state
    })


@app.route('/api/bot/config', methods=['GET', 'POST'])
def bot_configuration():
    """Get or update bot configuration."""
    global bot_config
    
    if request.method == 'GET':
        return jsonify({
            "success": True,
            "config": bot_config
        })
    
    # POST - Update configuration
    data = request.get_json()
    
    # Validate and update each field
    if "min_confidence" in data:
        val = float(data["min_confidence"])
        if 0 <= val <= 1:
            bot_config["min_confidence"] = val
    
    if "min_edge" in data:
        val = float(data["min_edge"])
        if 0 <= val <= 0.5:
            bot_config["min_edge"] = val
    
    if "max_bet_pct" in data:
        val = float(data["max_bet_pct"])
        if 0 < val <= 0.1:
            bot_config["max_bet_pct"] = val
    
    if "max_position_size" in data:
        val = int(data["max_position_size"])
        if 1 <= val <= 10000:
            bot_config["max_position_size"] = val
    
    if "enabled_sports" in data:
        if isinstance(data["enabled_sports"], list):
            bot_config["enabled_sports"] = data["enabled_sports"]
    
    if "auto_execute" in data:
        bot_config["auto_execute"] = bool(data["auto_execute"])
    
    if "use_research" in data:
        bot_config["use_research"] = bool(data["use_research"])
    
    if "max_daily_trades" in data:
        val = int(data["max_daily_trades"])
        if 1 <= val <= 100:
            bot_config["max_daily_trades"] = val
    
    if "max_daily_loss" in data:
        val = float(data["max_daily_loss"])
        if val > 0:
            bot_config["max_daily_loss"] = val
    
    if "preferred_model" in data:
        bot_config["preferred_model"] = str(data["preferred_model"])
    
    if "scan_interval" in data:
        val = int(data["scan_interval"])
        if 60 <= val <= 3600:
            bot_state["scan_interval"] = val
    
    return jsonify({
        "success": True,
        "message": "Configuration updated",
        "config": bot_config
    })


@app.route('/api/bot/auto-trade', methods=['POST'])
def toggle_auto_trade():
    """Toggle auto-trade mode."""
    global bot_state
    
    data = request.get_json()
    enabled = data.get("enabled", False)
    
    bot_state["auto_trade"] = bool(enabled)
    
    return jsonify({
        "success": True,
        "auto_trade": bot_state["auto_trade"],
        "message": f"Auto-trade {'enabled' if bot_state['auto_trade'] else 'disabled'}"
    })


@app.route('/api/bot/scan-now', methods=['POST'])
def trigger_scan():
    """Trigger an immediate scan."""
    data = request.get_json() or {}
    sport = data.get("sport", "americanfootball_nfl")
    max_events = data.get("max_events", 5)
    include_research = data.get("include_research", bot_config["use_research"])
    
    try:
        decisions = decision_engine.scan_sport(
            sport_key=sport,
            max_events=max_events,
            include_research=include_research
        )
        
        recommendations = decision_engine.get_recommendations(decisions)
        
        # Store decisions
        with cache_lock:
            for d in decisions:
                dashboard_cache["decisions"].append({
                    "decision": d.__dict__,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            dashboard_cache["decisions"] = dashboard_cache["decisions"][-200:]
        
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


# ==================== Trading API Routes ====================

@app.route('/api/trade/place', methods=['POST'])
def place_trade():
    """Place a manual trade order."""
    data = request.get_json()
    
    required = ["ticker", "side", "action", "count"]
    for field in required:
        if field not in data:
            return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400
    
    try:
        order = kalshi_client.create_order(
            ticker=data["ticker"],
            side=data["side"],  # 'yes' or 'no'
            action=data["action"],  # 'buy' or 'sell'
            count=int(data["count"]),
            type=data.get("type", "limit"),
            yes_price=data.get("yes_price"),
            no_price=data.get("no_price")
        )
        
        if order:
            return jsonify({
                "success": True,
                "message": "Order placed successfully",
                "order": order
            })
        else:
            return jsonify({"success": False, "error": "Order failed"}), 500
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/trade/cancel/<order_id>', methods=['DELETE'])
def cancel_trade(order_id):
    """Cancel an open order."""
    try:
        result = kalshi_client.cancel_order(order_id)
        return jsonify({
            "success": True,
            "message": f"Order {order_id} cancelled",
            "result": result
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/orders')
def get_orders():
    """Get open orders."""
    try:
        orders = kalshi_client.get_orders(status="resting")
        return jsonify({
            "success": True,
            "orders": orders.get("orders", []) if orders else []
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== Portfolio API Routes ====================

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


# ==================== Market Data API Routes ====================

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


@app.route('/api/kalshi/market/<ticker>')
def get_kalshi_market(ticker):
    """Get detailed market info."""
    try:
        market = kalshi_client.get_market(ticker)
        orderbook = kalshi_client.get_market_orderbook(ticker)
        return jsonify({
            "success": True,
            "market": market,
            "orderbook": orderbook
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== Analysis API Routes ====================

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
            dashboard_cache["decisions"] = dashboard_cache["decisions"][-200:]
        
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


# ==================== System API Routes ====================

@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "bot_running": bot_state["running"],
        "auto_trade": bot_state["auto_trade"],
        "clients": {
            "kalshi": kalshi_client is not None,
            "odds": odds_client is not None,
            "decision_engine": decision_engine is not None
        }
    })


@app.route('/api/errors')
def get_errors():
    """Get recent bot errors."""
    return jsonify({
        "success": True,
        "errors": bot_state["errors"][-20:]
    })


@app.route('/api/stats')
def get_stats():
    """Get trading statistics."""
    reset_daily_stats()
    return jsonify({
        "success": True,
        "stats": trading_stats
    })


# ==================== Page Routes ====================

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')


# ==================== Main ====================

def create_app():
    """Create and configure the Flask application."""
    init_clients()
    
    # Start background cache updater
    cache_thread = threading.Thread(target=update_cache, daemon=True)
    cache_thread.start()
    
    # Start scanner thread (but don't start scanning)
    global scanner_thread
    scanner_thread = threading.Thread(target=background_scanner, daemon=True)
    scanner_thread.start()
    
    return app


if __name__ == '__main__':
    app = create_app()
    
    # Get port from environment or use default
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    print(f"Starting dashboard on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
