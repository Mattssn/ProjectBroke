#!/usr/bin/env python3
"""
Kalshi Sports Betting Bot

An AI-powered trading system for Kalshi prediction markets with:
- Sports odds integration from The Odds API
- Research capabilities via Perplexity AI
- Multi-model decision making via OpenRouter
- Real-time web dashboard for monitoring

Usage:
    python main.py              # Interactive menu
    python main.py dashboard    # Launch web dashboard
    python main.py scan NFL     # Scan specific sport
    python main.py research "Lakers vs Celtics"  # Research matchup

Author: Built with AI assistance
License: MIT
"""
import os
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def print_banner():
    """Print application banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║           KALSHI SPORTS BETTING BOT                           ║
║       AI-Powered Prediction Market Trading                    ║
╠═══════════════════════════════════════════════════════════════╣
║  Features:                                                    ║
║  • Sports Odds Integration (The Odds API)                     ║
║  • AI Research (Perplexity)                                   ║
║  • Multi-Model Decisions (OpenRouter)                         ║
║  • Real-Time Dashboard                                        ║
╚═══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def check_api_keys():
    """Check if required API keys are configured."""
    keys = {
        "KALSHI_API_KEY": os.getenv("KALSHI_API_KEY"),
        "ODDS_API_KEY": os.getenv("ODDS_API_KEY"),
        "PERPLEXITY_API_KEY": os.getenv("PERPLEXITY_API_KEY"),
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY"),
    }
    
    missing = []
    configured = []
    
    for key, value in keys.items():
        if not value or value.startswith("your_"):
            missing.append(key)
        else:
            configured.append(key)
    
    print("\n📋 API Configuration Status:")
    for key in configured:
        print(f"   ✅ {key}: Configured")
    for key in missing:
        print(f"   ❌ {key}: Not configured")
    
    if missing:
        print(f"\n⚠️  Some API keys are missing. Copy .env.example to .env and add your keys.")
    
    return len(missing) == 0


def launch_dashboard():
    """Launch the web dashboard."""
    print("\n🚀 Launching Web Dashboard...")
    print("   Dashboard URL: http://localhost:5000")
    print("   Press Ctrl+C to stop\n")
    
    from web.app import create_app
    app = create_app()
    
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug)


def scan_sport(sport_key: str, max_events: int = 5, include_research: bool = True):
    """Scan a sport for betting opportunities."""
    print(f"\n🔍 Scanning {sport_key} for opportunities...")
    
    from src.decision_engine import AIDecisionEngine
    
    engine = AIDecisionEngine()
    decisions = engine.scan_sport(
        sport_key=sport_key,
        max_events=max_events,
        include_research=include_research
    )
    
    recommendations = engine.get_recommendations(decisions)
    
    print(f"\n📊 Scan Results:")
    print(f"   Events Analyzed: {len(decisions)}")
    print(f"   Recommendations: {len(recommendations)}")
    
    if recommendations:
        print(f"\n🎯 Recommended Bets:")
        for i, rec in enumerate(recommendations, 1):
            print(f"\n   [{i}] {rec.event_name}")
            print(f"       Decision: {rec.decision}")
            print(f"       Bet: {rec.bet_type} {rec.bet_side}")
            print(f"       Confidence: {rec.confidence * 100:.1f}%")
            print(f"       Expected Value: {rec.expected_value * 100:.2f}%")
            print(f"       Reasoning: {rec.reasoning[:100]}...")
    else:
        print("\n   No recommended bets at this time.")
    
    return decisions


def research_matchup(query: str):
    """Research a specific matchup."""
    print(f"\n🔬 Researching: {query}")
    
    from src.perplexity_client import PerplexityClient
    
    client = PerplexityClient()
    
    # Parse query to extract teams
    parts = query.lower().replace(" vs ", " vs. ").replace(" at ", " @ ").split()
    
    result = client.ask(
        question=f"Provide a betting analysis for: {query}. Include recent performance, injuries, and betting trends.",
        model="sonar-pro"
    )
    
    print(f"\n📝 Research Results:")
    print("-" * 60)
    print(result.get("answer", "No results found."))
    print("-" * 60)
    
    if result.get("citations"):
        print(f"\n📚 Sources ({len(result['citations'])} citations)")
    
    return result


def get_portfolio():
    """Display current portfolio status."""
    print("\n💼 Fetching Portfolio Status...")
    
    from src.kalshi_client import KalshiClient
    
    client = KalshiClient()
    
    balance = client.get_balance()
    positions = client.get_positions()
    
    if balance:
        print(f"\n   Available Balance: ${balance.get('balance', 0) / 100:.2f}")
        print(f"   Portfolio Value: ${balance.get('portfolio_value', 0) / 100:.2f}")
    else:
        print("\n   ⚠️  Could not fetch balance. Check your Kalshi API credentials.")
    
    if positions and positions.get("market_positions"):
        print(f"\n   Open Positions: {len(positions['market_positions'])}")
        for pos in positions["market_positions"][:5]:
            print(f"      • {pos.get('ticker', 'N/A')}: {pos.get('position', 'N/A').upper()}")
    else:
        print("\n   No open positions.")
    
    return balance, positions


def interactive_menu():
    """Show interactive menu."""
    while True:
        print("\n" + "=" * 50)
        print("   MAIN MENU")
        print("=" * 50)
        print("   1. 🖥️  Launch Web Dashboard")
        print("   2. 🔍 Scan Sport for Opportunities")
        print("   3. 🔬 Research a Matchup")
        print("   4. 💼 View Portfolio")
        print("   5. 📊 Check API Status")
        print("   6. ❌ Exit")
        print("=" * 50)
        
        try:
            choice = input("\nEnter your choice (1-6): ").strip()
            
            if choice == "1":
                launch_dashboard()
            elif choice == "2":
                print("\nAvailable sports:")
                print("  NFL: americanfootball_nfl")
                print("  NBA: basketball_nba")
                print("  MLB: baseball_mlb")
                print("  NHL: icehockey_nhl")
                print("  NCAAF: americanfootball_ncaaf")
                print("  NCAAB: basketball_ncaab")
                
                sport = input("\nEnter sport key: ").strip()
                if sport:
                    max_events = input("Max events to analyze (default 5): ").strip()
                    max_events = int(max_events) if max_events else 5
                    scan_sport(sport, max_events)
            elif choice == "3":
                query = input("\nEnter matchup (e.g., 'Lakers vs Celtics'): ").strip()
                if query:
                    research_matchup(query)
            elif choice == "4":
                get_portfolio()
            elif choice == "5":
                check_api_keys()
            elif choice == "6":
                print("\nGoodbye! 👋")
                break
            else:
                print("\n⚠️  Invalid choice. Please enter 1-6.")
        
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


def main():
    """Main entry point."""
    print_banner()
    
    parser = argparse.ArgumentParser(
        description="Kalshi Sports Betting Bot - AI-Powered Trading",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Dashboard command
    dashboard_parser = subparsers.add_parser("dashboard", help="Launch web dashboard")
    
    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan a sport for opportunities")
    scan_parser.add_argument("sport", help="Sport key (e.g., americanfootball_nfl)")
    scan_parser.add_argument("--max", type=int, default=5, help="Max events to analyze")
    scan_parser.add_argument("--no-research", action="store_true", help="Skip research step")
    
    # Research command
    research_parser = subparsers.add_parser("research", help="Research a matchup")
    research_parser.add_argument("query", help="Matchup to research")
    
    # Portfolio command
    portfolio_parser = subparsers.add_parser("portfolio", help="View portfolio status")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check API configuration")
    
    args = parser.parse_args()
    
    if args.command == "dashboard":
        check_api_keys()
        launch_dashboard()
    elif args.command == "scan":
        check_api_keys()
        scan_sport(args.sport, args.max, not args.no_research)
    elif args.command == "research":
        research_matchup(args.query)
    elif args.command == "portfolio":
        get_portfolio()
    elif args.command == "status":
        check_api_keys()
    else:
        # No command - show interactive menu
        check_api_keys()
        interactive_menu()


if __name__ == "__main__":
    main()
