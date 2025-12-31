"""
Kalshi Sports Betting Dashboard - Simplified (no external AI)

Clean, budget-friendly version:
- The Odds API (free tier: 500 req/month)
- ESPN API (free) for team data
- Heuristic scoring only (no paid AI services)
"""
import os
import json
import traceback
from datetime import datetime, timezone
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import threading
import time

# Import our modules
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.kalshi_client import KalshiClient
from src.sports_odds_client import SportsOddsClient
from src.decision_engine import AIDecisionEngine, BetDecision


# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Global instances
kalshi_client = None
odds_client = None
decision_engine = None

# Bot state
bot_state = {
    "running": False,
    "auto_trade": False,
    "last_scan": None,
    "current_sport": None,
    "scan_interval": 300,
    "errors": []
}

# Bot configuration
bot_config = {
    "min_confidence": float(os.getenv("MIN_CONFIDENCE", "0.6")),
    "min_edge": float(os.getenv("MIN_EDGE", "0.03")),
    "max_bet_pct": float(os.getenv("MAX_BET_PCT", "0.02")),
    "max_position_size": int(os.getenv("MAX_POSITION_SIZE", "1000")),
    "enabled_sports": ["americanfootball_nfl", "basketball_nba"],
    "auto_execute": False,
    "use_research": True,  # ESPN research (free)
    "max_daily_trades": 10,
    "max_daily_loss": 100.0,
}

# Trading stats
trading_stats = {
    "trades_today": 0,
    "daily_pnl": 0.0,
    "total_analyzed": 0,
    "total_recommended": 0,
    "last_reset": datetime.now(timezone.utc).date().isoformat()
}

# Dashboard cache
dashboard_cache = {
    "portfolio": None,
    "positions": None,
    "recent_trades": None,
    "decisions": [],
    "last_update": None
}
cache_lock = threading.Lock()

# Scanner thread
scanner_thread = None
scanner_stop_event = threading.Event()

# Debug settings
debug_config = {
    "log_level": "INFO",
    "log_decisions": True,
}
debug_log_buffer = []


def init_clients():
    """Initialize API clients."""
    global kalshi_client, odds_client, decision_engine
    
    kalshi_client = KalshiClient()
    odds_client = SportsOddsClient()
    decision_engine = AIDecisionEngine()

    print("[INIT] Clients initialized")
    print("[INIT] Data sources: Odds API (free tier) + ESPN (free)")
    print("[INIT] No external AI providers in use")


def add_debug_log(level: str, component: str, message: str):
    """Add log entry for dashboard."""
    global debug_log_buffer
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "component": component,
        "message": message
    }
    debug_log_buffer.append(entry)
    debug_log_buffer = debug_log_buffer[-500:]


def reset_daily_stats():
    """Reset daily stats."""
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


def serialize_decision(d):
    """Serialize BetDecision to dict."""
    if isinstance(d, dict):
        return d
    if hasattr(d, 'to_dict'):
        return d.to_dict()
    return {
        "event_id": getattr(d, 'event_id', None),
        "event_name": getattr(d, 'event_name', None),
        "sport": getattr(d, 'sport', None),
        "home_team": getattr(d, 'home_team', None),
        "away_team": getattr(d, 'away_team', None),
        "commence_time": getattr(d, 'commence_time', None),
        "decision": getattr(d, 'decision', None),
        "bet_type": getattr(d, 'bet_type', None),
        "bet_side": getattr(d, 'bet_side', None),
        "bet_amount_usd": getattr(d, 'bet_amount_usd', None),
        "confidence": getattr(d, 'confidence', 0),
        "expected_value": getattr(d, 'expected_value', 0),
        "win_probability": getattr(d, 'win_probability', 0),
        "reasoning": getattr(d, 'reasoning', ''),
        "key_insights": getattr(d, 'key_insights', []) or [],
        "risk_factors": getattr(d, 'risk_factors', []) or [],
        "odds_snapshot": getattr(d, 'odds_snapshot', None),
        "research_summary": getattr(d, 'research_summary', None),
        "created_at": getattr(d, 'created_at', None),
        "model_used": getattr(d, 'model_used', None)
    }


def store_decision(decision):
    """Store decision in cache (real-time callback)."""
    global trading_stats
    
    decision_dict = serialize_decision(decision)
    
    with cache_lock:
        dashboard_cache["decisions"].append({
            "decision": decision_dict,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        dashboard_cache["decisions"] = dashboard_cache["decisions"][-200:]
    
    trading_stats["total_analyzed"] += 1
    if decision_dict.get("decision") == "place_bet":
        trading_stats["total_recommended"] += 1
    
    print(f"[STORED] {decision_dict.get('event_name')} -> {decision_dict.get('decision')} (Total: {len(dashboard_cache['decisions'])})")
    
    if debug_config.get("log_decisions"):
        add_debug_log("INFO", "engine", 
            f"{decision_dict.get('event_name')}: {decision_dict.get('decision')} "
            f"(conf: {decision_dict.get('confidence', 0):.0%})")


def background_scanner():
    """Background scanning thread."""
    global bot_state, trading_stats
    
    while not scanner_stop_event.is_set():
        if bot_state["running"]:
            try:
                reset_daily_stats()
                
                for sport in bot_config["enabled_sports"]:
                    if scanner_stop_event.is_set() or not bot_state["running"]:
                        break
                    
                    bot_state["current_sport"] = sport
                    add_debug_log("INFO", "scanner", f"Scanning {sport}...")
                    
                    try:
                        decisions = decision_engine.scan_sport(
                            sport_key=sport,
                            max_events=5,
                            include_research=bot_config["use_research"],
                            on_decision=store_decision
                        )
                        add_debug_log("INFO", "scanner", f"{sport}: {len(decisions)} analyzed")
                        
                    except Exception as e:
                        add_debug_log("ERROR", "scanner", f"{sport} error: {str(e)}")
                        bot_state["errors"].append({
                            "time": datetime.now(timezone.utc).isoformat(),
                            "message": str(e)
                        })
                    
                    time.sleep(2)
                
                bot_state["last_scan"] = datetime.now(timezone.utc).isoformat()
                bot_state["current_sport"] = None
                
            except Exception as e:
                add_debug_log("ERROR", "scanner", f"Error: {str(e)}")
            
            bot_state["errors"] = bot_state["errors"][-50:]
        
        scanner_stop_event.wait(bot_state["scan_interval"])


def update_cache():
    """Update portfolio cache."""
    global dashboard_cache
    
    while True:
        try:
            with cache_lock:
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
            print(f"Cache error: {e}")
        
        time.sleep(30)


# ==================== API Routes ====================

@app.route('/api/bot/status')
def get_bot_status():
    return jsonify({
        "success": True,
        "state": bot_state,
        "config": bot_config,
        "stats": trading_stats
    })


@app.route('/api/bot/start', methods=['POST'])
def start_bot():
    global bot_state, scanner_thread
    
    if bot_state["running"]:
        return jsonify({"success": False, "error": "Already running"})
    
    bot_state["running"] = True
    bot_state["errors"] = []
    
    if scanner_thread is None or not scanner_thread.is_alive():
        scanner_stop_event.clear()
        scanner_thread = threading.Thread(target=background_scanner, daemon=True)
        scanner_thread.start()
    
    add_debug_log("INFO", "system", "Bot started")
    return jsonify({"success": True, "message": "Bot started"})


@app.route('/api/bot/stop', methods=['POST'])
def stop_bot():
    global bot_state
    bot_state["running"] = False
    bot_state["current_sport"] = None
    add_debug_log("INFO", "system", "Bot stopped")
    return jsonify({"success": True, "message": "Bot stopped"})


@app.route('/api/bot/config', methods=['GET', 'POST'])
def bot_configuration():
    global bot_config
    
    if request.method == 'GET':
        return jsonify({"success": True, "config": bot_config})
    
    data = request.get_json()
    
    for key in ["min_confidence", "min_edge", "max_bet_pct"]:
        if key in data:
            bot_config[key] = float(data[key])
    
    for key in ["max_position_size", "max_daily_trades"]:
        if key in data:
            bot_config[key] = int(data[key])
    
    if "max_daily_loss" in data:
        bot_config["max_daily_loss"] = float(data["max_daily_loss"])
    
    if "enabled_sports" in data:
        bot_config["enabled_sports"] = data["enabled_sports"]
    
    if "use_research" in data:
        bot_config["use_research"] = bool(data["use_research"])
    
    if "auto_execute" in data:
        bot_config["auto_execute"] = bool(data["auto_execute"])
    
    
    if "scan_interval" in data:
        bot_state["scan_interval"] = int(data["scan_interval"])
    
    return jsonify({"success": True, "config": bot_config})


@app.route('/api/bot/auto-trade', methods=['POST'])
def toggle_auto_trade():
    global bot_state
    data = request.get_json()
    bot_state["auto_trade"] = bool(data.get("enabled", False))
    return jsonify({
        "success": True,
        "auto_trade": bot_state["auto_trade"]
    })


@app.route('/api/bot/scan-now', methods=['POST'])
def trigger_scan():
    data = request.get_json() or {}
    sport = data.get("sport", "americanfootball_nfl")
    max_events = data.get("max_events", 5)
    include_research = data.get("include_research", bot_config["use_research"])
    
    print(f"[SCAN] Starting: {sport}, max_events={max_events}")
    add_debug_log("INFO", "system", f"Manual scan: {sport}")
    
    def run_scan():
        try:
            bot_state["current_sport"] = sport
            
            decisions = decision_engine.scan_sport(
                sport_key=sport,
                max_events=max_events,
                include_research=include_research,
                on_decision=store_decision
            )
            
            bot_state["current_sport"] = None
            recs = len([d for d in decisions if d.decision == "place_bet"])
            print(f"[SCAN] Complete: {len(decisions)} analyzed, {recs} recommendations")
            add_debug_log("INFO", "system", f"Scan complete: {recs}/{len(decisions)} recommended")
            
        except Exception as e:
            print(f"[SCAN] Error: {e}")
            traceback.print_exc()
            bot_state["current_sport"] = None
            add_debug_log("ERROR", "system", f"Scan error: {str(e)}")
    
    scan_thread = threading.Thread(target=run_scan, daemon=True)
    scan_thread.start()
    
    return jsonify({
        "success": True,
        "message": f"Scan started for {sport}",
        "sport": sport,
        "max_events": max_events
    })


# ==================== Portfolio Routes ====================

@app.route('/api/portfolio')
def get_portfolio():
    with cache_lock:
        return jsonify({
            "success": True,
            "data": dashboard_cache.get("portfolio", {}),
            "updated_at": dashboard_cache.get("last_update")
        })


@app.route('/api/positions')
def get_positions():
    with cache_lock:
        return jsonify({
            "success": True,
            "data": dashboard_cache.get("positions", [])
        })


@app.route('/api/trades')
def get_trades():
    with cache_lock:
        return jsonify({
            "success": True,
            "data": dashboard_cache.get("recent_trades", [])
        })


@app.route('/api/decisions')
def get_decisions():
    with cache_lock:
        decisions = dashboard_cache.get("decisions", [])
    print(f"[API] Returning {len(decisions)} decisions")
    return jsonify({
        "success": True,
        "decisions": decisions[-50:],
        "count": len(decisions)
    })


# ==================== Trading Routes ====================

@app.route('/api/trade/place', methods=['POST'])
def place_trade():
    data = request.get_json()
    required = ["ticker", "side", "action", "count"]
    for field in required:
        if field not in data:
            return jsonify({"success": False, "error": f"Missing: {field}"}), 400
    
    try:
        order = kalshi_client.create_order(
            ticker=data["ticker"],
            side=data["side"],
            action=data["action"],
            count=int(data["count"]),
            type=data.get("type", "limit"),
            yes_price=data.get("yes_price"),
            no_price=data.get("no_price")
        )
        return jsonify({"success": True, "order": order}) if order else jsonify({"success": False, "error": "Failed"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/trade/cancel/<order_id>', methods=['DELETE'])
def cancel_trade(order_id):
    try:
        result = kalshi_client.cancel_order(order_id)
        return jsonify({"success": True, "result": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/orders')
def get_orders():
    try:
        orders = kalshi_client.get_orders(status="resting")
        return jsonify({"success": True, "orders": orders.get("orders", []) if orders else []})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== Debug Routes ====================

@app.route('/api/debug/settings', methods=['GET', 'POST'])
def debug_settings():
    global debug_config
    if request.method == 'GET':
        return jsonify({"success": True, "settings": debug_config})
    
    data = request.get_json()
    if "log_level" in data:
        debug_config["log_level"] = data["log_level"]
    if "log_decisions" in data:
        debug_config["log_decisions"] = bool(data["log_decisions"])
    
    return jsonify({"success": True, "settings": debug_config})


@app.route('/api/debug/logs')
def get_debug_logs():
    limit = request.args.get('limit', 100, type=int)
    return jsonify({"success": True, "logs": debug_log_buffer[-limit:]})


@app.route('/api/debug/logs/clear', methods=['POST'])
def clear_debug_logs():
    global debug_log_buffer
    debug_log_buffer = []
    return jsonify({"success": True})


@app.route('/api/debug/decisions')
def debug_decisions():
    with cache_lock:
        decisions = dashboard_cache.get("decisions", [])
    return jsonify({
        "total": len(decisions),
        "latest": decisions[-3:] if decisions else [],
        "stats": trading_stats
    })


# ==================== Other Routes ====================

@app.route('/api/health')
def health_check():
    with cache_lock:
        decision_count = len(dashboard_cache.get("decisions", []))
    return jsonify({
        "status": "healthy",
        "bot_running": bot_state["running"],
        "decisions_cached": decision_count,
        "data_sources": ["odds_api", "espn_free"]
    })


@app.route('/api/stats')
def get_stats():
    reset_daily_stats()
    return jsonify({"success": True, "stats": trading_stats})


@app.route('/api/errors')
def get_errors():
    return jsonify({"success": True, "errors": bot_state["errors"][-20:]})


@app.route('/')
def index():
    return render_template('index.html')


# ==================== Main ====================

def create_app():
    init_clients()
    
    cache_thread = threading.Thread(target=update_cache, daemon=True)
    cache_thread.start()
    
    global scanner_thread
    scanner_thread = threading.Thread(target=background_scanner, daemon=True)
    scanner_thread.start()
    
    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 5000))
    print(f"\n{'='*50}")
    print("KALSHI SPORTS BOT - HEURISTIC VERSION")
    print(f"{'='*50}")
    print(f"Dashboard: http://localhost:{port}")
    print("Data: Odds API (free) + ESPN (free)")
    print("External AI Providers: REMOVED")
    print(f"{'='*50}\n")
    app.run(host='0.0.0.0', port=port, debug=False)
