"""
Enhanced Kalshi API Client

Comprehensive client for Kalshi prediction markets with support for:
- Portfolio management (balance, positions, fills, settlements)
- Market data (events, markets, orderbooks, candlesticks)
- Order management (create, cancel, amend orders)
- Real-time WebSocket connections

Authentication uses RSA key signing as per Kalshi API v2 specification.
"""
import os
import time
import base64
import hashlib
import requests
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, ec
from cryptography.hazmat.backends import default_backend


class KalshiClient:
    """
    Professional Kalshi API client with full portfolio and market support.
    """
    
    def __init__(self, api_key: str = None, api_secret: str = None, base_url: str = None):
        self.api_key = api_key or os.getenv("KALSHI_API_KEY")
        self.api_secret = api_secret or os.getenv("KALSHI_API_SECRET")
        self.base_url = base_url or os.getenv(
            "KALSHI_API_BASE_URL", 
            "https://api.elections.kalshi.com/trade-api/v2"
        )
        self.session = requests.Session()
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = float(os.getenv("API_MIN_INTERVAL", "0.1"))
        self.rate_limit_reset_time = 0
        
        # Load private key if provided
        self.private_key = None
        if self.api_secret:
            self._load_private_key()
    
    def _load_private_key(self):
        """Load the RSA private key for request signing."""
        try:
            key_data = self.api_secret
            
            # Check if it's a file path
            if os.path.isfile(self.api_secret):
                with open(self.api_secret, 'r') as f:
                    key_data = f.read()
            
            # Try loading as PEM
            if "-----BEGIN" in key_data:
                self.private_key = serialization.load_pem_private_key(
                    key_data.encode(),
                    password=None,
                    backend=default_backend()
                )
        except Exception as e:
            print(f"Warning: Could not load private key: {e}")
            self.private_key = None
    
    def _sign_request(self, method: str, path: str, timestamp: str) -> str:
        """Sign a request using the private key."""
        if not self.private_key:
            return ""
        
        try:
            message = f"{timestamp}{method}{path}"
            
            # Sign based on key type
            if hasattr(self.private_key, 'sign'):
                signature = self.private_key.sign(
                    message.encode(),
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
            else:
                signature = b""
            
            return base64.b64encode(signature).decode()
        except Exception as e:
            print(f"Warning: Could not sign request: {e}")
            return ""
    
    def _make_request(self, method: str, endpoint: str, 
                      params: Dict = None, json_data: Dict = None,
                      authenticated: bool = True) -> Optional[Dict]:
        """Execute an API request with rate limiting and error handling."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        
        if current_time < self.rate_limit_reset_time:
            wait_time = self.rate_limit_reset_time - current_time
            print(f"Rate limit cooldown: waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Add authentication headers
        if authenticated and self.api_key:
            timestamp = str(int(time.time() * 1000))
            path = f"/trade-api/v2/{endpoint.lstrip('/')}"
            signature = self._sign_request(method.upper(), path, timestamp)
            
            headers["KALSHI-ACCESS-KEY"] = self.api_key
            headers["KALSHI-ACCESS-TIMESTAMP"] = timestamp
            headers["KALSHI-ACCESS-SIGNATURE"] = signature
        
        try:
            self.last_request_time = time.time()
            
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=30
            )
            
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                self.rate_limit_reset_time = time.time() + retry_after
                print(f"Rate limit hit. Waiting {retry_after}s...")
                time.sleep(retry_after)
                return self._make_request(method, endpoint, params, json_data, authenticated)
            
            response.raise_for_status()
            return response.json() if response.text else {}
            
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return None
    
    # ==================== Portfolio Endpoints ====================
    
    def get_balance(self) -> Optional[Dict]:
        """
        Get account balance and portfolio value.
        
        Returns:
            Dict with 'balance' (available) and 'portfolio_value' (total) in cents
        """
        return self._make_request("GET", "portfolio/balance")
    
    def get_positions(self, ticker: str = None, event_ticker: str = None,
                     limit: int = 100, cursor: str = None,
                     settlement_status: str = "unsettled") -> Optional[Dict]:
        """
        Get current portfolio positions.
        
        Args:
            ticker: Filter by market ticker
            event_ticker: Filter by event ticker
            limit: Number of results (1-1000)
            cursor: Pagination cursor
            settlement_status: 'unsettled', 'settled', or 'all'
        
        Returns:
            Dict with 'market_positions' and 'event_positions' arrays
        """
        params = {"limit": limit, "settlement_status": settlement_status}
        if ticker:
            params["ticker"] = ticker
        if event_ticker:
            params["event_ticker"] = event_ticker
        if cursor:
            params["cursor"] = cursor
        
        return self._make_request("GET", "portfolio/positions", params=params)
    
    def get_fills(self, ticker: str = None, order_id: str = None,
                  min_ts: int = None, max_ts: int = None,
                  limit: int = 100, cursor: str = None) -> Optional[Dict]:
        """
        Get trade fills (executed trades).
        
        Args:
            ticker: Filter by market ticker
            order_id: Filter by order ID
            min_ts: Minimum timestamp
            max_ts: Maximum timestamp
            limit: Number of results
            cursor: Pagination cursor
        
        Returns:
            Dict with 'fills' array containing trade execution details
        """
        params = {"limit": limit}
        if ticker:
            params["ticker"] = ticker
        if order_id:
            params["order_id"] = order_id
        if min_ts:
            params["min_ts"] = min_ts
        if max_ts:
            params["max_ts"] = max_ts
        if cursor:
            params["cursor"] = cursor
        
        return self._make_request("GET", "portfolio/fills", params=params)
    
    def get_settlements(self, limit: int = 100, cursor: str = None) -> Optional[Dict]:
        """
        Get settled positions.
        
        Returns:
            Dict with 'settlements' array
        """
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        
        return self._make_request("GET", "portfolio/settlements", params=params)
    
    def get_orders(self, ticker: str = None, event_ticker: str = None,
                   status: str = None, limit: int = 100) -> Optional[Dict]:
        """
        Get open and historical orders.
        
        Args:
            ticker: Filter by market ticker
            event_ticker: Filter by event ticker
            status: Order status filter ('resting', 'canceled', 'executed')
            limit: Number of results
        
        Returns:
            Dict with 'orders' array
        """
        params = {"limit": limit}
        if ticker:
            params["ticker"] = ticker
        if event_ticker:
            params["event_ticker"] = event_ticker
        if status:
            params["status"] = status
        
        return self._make_request("GET", "portfolio/orders", params=params)
    
    # ==================== Market Data Endpoints ====================
    
    def get_markets(self, limit: int = 100, cursor: str = None,
                    status: str = "open", series_ticker: str = None,
                    event_ticker: str = None) -> List[Dict]:
        """
        Get list of markets.
        
        Args:
            limit: Number of results (1-1000)
            status: 'open', 'closed', or 'settled'
            series_ticker: Filter by series
            event_ticker: Filter by event
        
        Returns:
            List of market dictionaries
        """
        params = {"limit": limit, "status": status}
        if cursor:
            params["cursor"] = cursor
        if series_ticker:
            params["series_ticker"] = series_ticker
        if event_ticker:
            params["event_ticker"] = event_ticker
        
        response = self._make_request("GET", "markets", params=params, authenticated=False)
        return response.get("markets", []) if response else []
    
    def get_market(self, ticker: str) -> Optional[Dict]:
        """Get detailed information for a specific market."""
        response = self._make_request("GET", f"markets/{ticker}", authenticated=False)
        return response.get("market") if response else None
    
    def get_market_orderbook(self, ticker: str, depth: int = 10) -> Optional[Dict]:
        """
        Get orderbook for a market.
        
        Args:
            ticker: Market ticker
            depth: Orderbook depth (default 10)
        
        Returns:
            Dict with 'yes' and 'no' orderbooks containing bids/asks
        """
        params = {"depth": depth}
        return self._make_request("GET", f"markets/{ticker}/orderbook", 
                                  params=params, authenticated=False)
    
    def get_market_candlesticks(self, series_ticker: str, market_ticker: str,
                                 start_ts: int = None, end_ts: int = None,
                                 period_interval: str = "1h") -> Optional[Dict]:
        """
        Get historical price candlesticks.
        
        Args:
            series_ticker: Series ticker
            market_ticker: Market ticker
            start_ts: Start timestamp
            end_ts: End timestamp
            period_interval: '1m', '5m', '1h', '1d', etc.
        
        Returns:
            Dict with 'candles' array
        """
        params = {"period_interval": period_interval}
        if start_ts:
            params["start_ts"] = start_ts
        if end_ts:
            params["end_ts"] = end_ts
        
        return self._make_request(
            "GET", 
            f"series/{series_ticker}/markets/{market_ticker}/candlesticks",
            params=params,
            authenticated=False
        )
    
    def get_trades(self, ticker: str = None, limit: int = 100,
                   cursor: str = None) -> Optional[Dict]:
        """
        Get public trades for all markets or a specific market.
        
        Returns:
            Dict with 'trades' array
        """
        params = {"limit": limit}
        if ticker:
            params["ticker"] = ticker
        if cursor:
            params["cursor"] = cursor
        
        return self._make_request("GET", "markets/trades", params=params, authenticated=False)
    
    def get_events(self, limit: int = 100, status: str = "open",
                   series_ticker: str = None) -> Optional[Dict]:
        """
        Get list of events.
        
        Returns:
            Dict with 'events' array
        """
        params = {"limit": limit, "status": status}
        if series_ticker:
            params["series_ticker"] = series_ticker
        
        return self._make_request("GET", "events", params=params, authenticated=False)
    
    def get_event(self, event_ticker: str) -> Optional[Dict]:
        """Get detailed information for a specific event."""
        response = self._make_request("GET", f"events/{event_ticker}", authenticated=False)
        return response.get("event") if response else None
    
    def get_series(self, series_ticker: str) -> Optional[Dict]:
        """Get series information."""
        response = self._make_request("GET", f"series/{series_ticker}", authenticated=False)
        return response.get("series") if response else None
    
    # ==================== Order Management ====================
    
    def create_order(self, ticker: str, side: str, action: str,
                     count: int, type: str = "limit", 
                     yes_price: int = None, no_price: int = None,
                     client_order_id: str = None,
                     expiration_ts: int = None) -> Optional[Dict]:
        """
        Create a new order.
        
        Args:
            ticker: Market ticker
            side: 'yes' or 'no'
            action: 'buy' or 'sell'
            count: Number of contracts
            type: 'limit' or 'market'
            yes_price: Price in cents for yes contracts (1-99)
            no_price: Price in cents for no contracts (1-99)
            client_order_id: Optional client-provided order ID
            expiration_ts: Optional expiration timestamp
        
        Returns:
            Dict with order details including 'order_id'
        """
        payload = {
            "ticker": ticker,
            "side": side,
            "action": action,
            "count": count,
            "type": type
        }
        
        if yes_price is not None:
            payload["yes_price"] = yes_price
        if no_price is not None:
            payload["no_price"] = no_price
        if client_order_id:
            payload["client_order_id"] = client_order_id
        if expiration_ts:
            payload["expiration_ts"] = expiration_ts
        
        return self._make_request("POST", "portfolio/orders", json_data=payload)
    
    def cancel_order(self, order_id: str) -> Optional[Dict]:
        """Cancel an open order."""
        return self._make_request("DELETE", f"portfolio/orders/{order_id}")
    
    def amend_order(self, order_id: str, count: int = None,
                    yes_price: int = None, no_price: int = None) -> Optional[Dict]:
        """
        Amend an existing order.
        
        Args:
            order_id: Order to amend
            count: New contract count
            yes_price: New yes price
            no_price: New no price
        """
        payload = {}
        if count is not None:
            payload["count"] = count
        if yes_price is not None:
            payload["yes_price"] = yes_price
        if no_price is not None:
            payload["no_price"] = no_price
        
        return self._make_request("POST", f"portfolio/orders/{order_id}/amend", 
                                  json_data=payload)
    
    # ==================== Exchange Info ====================
    
    def get_exchange_status(self) -> Optional[Dict]:
        """Get exchange status and trading schedule."""
        return self._make_request("GET", "exchange/status", authenticated=False)
    
    def get_exchange_schedule(self) -> Optional[Dict]:
        """Get exchange trading schedule."""
        return self._make_request("GET", "exchange/schedule", authenticated=False)


# Convenience function for quick testing
def get_client() -> KalshiClient:
    """Get a configured Kalshi client from environment variables."""
    return KalshiClient()
