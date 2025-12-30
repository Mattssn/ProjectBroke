#!/usr/bin/env python3
"""
ESPN API Debug - See exactly what's being returned
"""
import requests
import json

print("=" * 60)
print("ESPN STANDINGS DEBUG")
print("=" * 60)

# Create session with proxy bypass
session = requests.Session()
session.trust_env = False
session.proxies = {"http": None, "https": None}
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})

# Test standings endpoint
url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/standings"
print(f"\nFetching: {url}")

response = session.get(url, timeout=15)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    
    # Print structure
    print(f"\nTop-level keys: {list(data.keys())}")
    
    # Check for 'children' (old format)
    if "children" in data:
        print(f"\nFound 'children' key with {len(data['children'])} items")
        for i, child in enumerate(data['children'][:2]):
            print(f"  Child {i}: {child.get('name', 'no name')}")
            standings = child.get("standings", {})
            entries = standings.get("entries", [])
            print(f"    Entries: {len(entries)}")
            if entries:
                first = entries[0]
                print(f"    First entry keys: {list(first.keys())}")
                team = first.get("team", {})
                print(f"    Team: {team.get('displayName', 'N/A')}")
    
    # Check for other formats
    if "standings" in data:
        print(f"\nFound 'standings' key")
        print(f"  Keys: {list(data['standings'].keys())[:5]}")
    
    # Save full response for inspection
    with open("espn_standings_debug.json", "w") as f:
        json.dump(data, f, indent=2)
    print("\n✓ Full response saved to espn_standings_debug.json")
    
else:
    print(f"Error: {response.text[:500]}")

# Also test teams endpoint since we know that works
print("\n" + "=" * 60)
print("TEAMS ENDPOINT (for comparison)")
print("=" * 60)

url2 = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams"
response2 = session.get(url2, timeout=15)
data2 = response2.json()

print(f"Top-level keys: {list(data2.keys())}")
sports = data2.get("sports", [])
if sports:
    leagues = sports[0].get("leagues", [])
    if leagues:
        teams = leagues[0].get("teams", [])
        print(f"Found {len(teams)} teams via sports[0].leagues[0].teams")

# Test injuries
print("\n" + "=" * 60)
print("INJURIES ENDPOINT")
print("=" * 60)

url3 = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/injuries"
response3 = session.get(url3, timeout=15)
print(f"Status: {response3.status_code}")
if response3.status_code == 200:
    data3 = response3.json()
    print(f"Top-level keys: {list(data3.keys())}")
    if "injuries" in data3:
        print(f"Found {len(data3['injuries'])} team injury reports")

print("\n" + "=" * 60)
print("DONE - Check espn_standings_debug.json for full data")
print("=" * 60)
