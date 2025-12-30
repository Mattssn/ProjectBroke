#!/usr/bin/env python3
"""
ESPN API Diagnostic Script

Run this on your server to see exactly why ESPN isn't working.
Usage: python3 test_espn.py
"""
import sys

print("=" * 60)
print("ESPN API DIAGNOSTIC")
print("=" * 60)

# Test 1: Basic requests
print("\n[TEST 1] Basic requests import...")
try:
    import requests
    print(f"  ✓ requests version: {requests.__version__}")
except ImportError as e:
    print(f"  ✗ Failed to import requests: {e}")
    sys.exit(1)

# Test 2: Session with proxy bypass
print("\n[TEST 2] Creating session with proxy bypass...")
session = requests.Session()
session.trust_env = False  # CRITICAL: ignore system proxy
session.proxies = {"http": None, "https": None}  # CRITICAL: no proxy
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})
print("  ✓ Session created with proxy bypass")

# Test 3: Direct ESPN request
print("\n[TEST 3] Direct ESPN API request...")
url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams"
try:
    response = session.get(url, timeout=15)
    print(f"  Status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        teams = data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
        print(f"  ✓ SUCCESS! Found {len(teams)} NFL teams")
        if teams:
            first_team = teams[0].get("team", {}).get("displayName", "Unknown")
            print(f"  First team: {first_team}")
    else:
        print(f"  ✗ HTTP Error: {response.status_code}")
        print(f"  Response: {response.text[:200]}")
except Exception as e:
    print(f"  ✗ Request failed: {type(e).__name__}: {e}")

# Test 4: Check your FreeSportsDataClient
print("\n[TEST 4] Checking FreeSportsDataClient...")
try:
    # Try to import from the project
    sys.path.insert(0, '.')
    from src.free_sports_data import FreeSportsDataClient
    
    client = FreeSportsDataClient()
    
    # Check if proxy bypass is set
    print(f"  trust_env: {client.session.trust_env}")
    print(f"  proxies: {client.session.proxies}")
    
    if not client.session.trust_env and client.session.proxies == {"http": None, "https": None}:
        print("  ✓ Proxy bypass is correctly configured!")
    else:
        print("  ✗ PROXY BYPASS NOT SET! This is your problem!")
        print("  Fix: Add these lines after 'self.session = requests.Session()':")
        print("       self.session.trust_env = False")
        print("       self.session.proxies = {'http': None, 'https': None}")
    
    # Try a real request
    print("\n[TEST 5] Testing FreeSportsDataClient.get_standings()...")
    standings = client.get_standings("americanfootball_nfl")
    teams = standings.get("teams", {})
    print(f"  Got {len(teams)} teams in standings")
    
    if teams:
        first_team = list(teams.keys())[0]
        record = teams[first_team]
        print(f"  ✓ SUCCESS! Example: {first_team}: {record.get('wins')}-{record.get('losses')}")
    else:
        print("  ✗ No standings data returned")
        
except ImportError as e:
    print(f"  ✗ Cannot import FreeSportsDataClient: {e}")
    print("  Make sure you're running this from the ProjectBroke directory")
except Exception as e:
    print(f"  ✗ Error: {type(e).__name__}: {e}")

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
print("""
If Test 3 passed but Test 4/5 failed:
  → Your free_sports_data.py doesn't have the proxy fix!
  → Add these 2 lines after 'self.session = requests.Session()':
      self.session.trust_env = False
      self.session.proxies = {"http": None, "https": None}

If Test 3 failed:
  → ESPN is blocked at the network level
  → The bot will work fine with odds-only analysis

Run this from your ProjectBroke directory:
  cd ~/ProjectBroke && python3 test_espn.py
""")
