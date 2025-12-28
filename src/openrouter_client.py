"""
OpenRouter AI Client

Unified client for 400+ AI models through OpenRouter:
- OpenAI (GPT-4, GPT-4o, o1, etc.)
- Anthropic (Claude 3.5, Claude 3)
- Google (Gemini Pro, Ultra)
- Meta (Llama 3.1, Llama 3)
- Mistral, DeepSeek, and many more

API Documentation: https://openrouter.ai/docs
"""
import os
import json
import requests
from typing import List, Dict, Optional, Any, Generator


class OpenRouterClient:
    """
    Client for OpenRouter unified AI API.
    """
    
    BASE_URL = "https://openrouter.ai/api/v1"
    
    # Popular models for different tasks
    MODELS = {
        # Reasoning models
        "gpt-4o": "openai/gpt-4o",
        "claude-sonnet": "anthropic/claude-3.5-sonnet",
        "claude-opus": "anthropic/claude-3-opus",
        "gemini-pro": "google/gemini-pro-1.5",
        "deepseek-r1": "deepseek/deepseek-r1",
        
        # Fast/cheap models
        "gpt-4o-mini": "openai/gpt-4o-mini",
        "claude-haiku": "anthropic/claude-3-haiku",
        "llama-70b": "meta-llama/llama-3.1-70b-instruct",
        "mistral-large": "mistralai/mistral-large",
        
        # Specialized
        "perplexity-sonar": "perplexity/sonar-pro",  # Web search
        "qwen-72b": "qwen/qwen-2.5-72b-instruct",
    }
    
    def __init__(self, api_key: str = None, app_name: str = "KalshiSportsBot"):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.app_name = app_name
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/kalshi-sports-bot",
            "X-Title": app_name
        })
    
    def chat(self, messages: List[Dict], model: str = "openai/gpt-4o",
             temperature: float = 0.7, max_tokens: int = 4096,
             top_p: float = 1.0, stream: bool = False,
             tools: List[Dict] = None,
             response_format: Dict = None) -> Dict:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier (full OpenRouter model ID)
            temperature: Response randomness (0-2)
            max_tokens: Maximum tokens in response
            top_p: Nucleus sampling parameter
            stream: Enable streaming response
            tools: List of tool definitions for function calling
            response_format: Optional structured output format
        
        Returns:
            Dict with response content and metadata
        """
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": stream
        }
        
        if tools:
            payload["tools"] = tools
        if response_format:
            payload["response_format"] = response_format
        
        try:
            response = self.session.post(
                f"{self.BASE_URL}/chat/completions",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"OpenRouter API error: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response: {e.response.text}")
            return {"error": str(e)}
    
    def chat_stream(self, messages: List[Dict], model: str = "openai/gpt-4o",
                    temperature: float = 0.7, max_tokens: int = 4096) -> Generator[str, None, None]:
        """
        Send a streaming chat completion request.
        
        Yields content chunks as they arrive.
        """
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        
        try:
            response = self.session.post(
                f"{self.BASE_URL}/chat/completions",
                json=payload,
                stream=True,
                timeout=120
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        data = line_str[6:]
                        if data == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data)
                            content = chunk.get('choices', [{}])[0].get('delta', {}).get('content', '')
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
                            
        except requests.exceptions.RequestException as e:
            yield f"Error: {e}"
    
    def ask(self, question: str, model: str = "openai/gpt-4o",
            system_prompt: str = None, temperature: float = 0.7) -> str:
        """
        Simple question-answering interface.
        
        Args:
            question: The question to ask
            model: Model to use
            system_prompt: Optional system prompt
            temperature: Response temperature
        
        Returns:
            Response text
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": question})
        
        response = self.chat(messages=messages, model=model, temperature=temperature)
        
        if "error" in response:
            return f"Error: {response['error']}"
        
        return response.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    def get_json_response(self, prompt: str, model: str = "openai/gpt-4o",
                          system_prompt: str = None) -> Dict:
        """
        Get a JSON-formatted response.
        
        Args:
            prompt: The prompt requesting structured data
            model: Model to use
            system_prompt: Optional system context
        
        Returns:
            Parsed JSON dict
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({
                "role": "system",
                "content": "You are a helpful assistant that always responds in valid JSON format."
            })
        
        messages.append({"role": "user", "content": prompt})
        
        response = self.chat(
            messages=messages,
            model=model,
            temperature=0.2,  # Lower temperature for more consistent JSON
            response_format={"type": "json_object"}
        )
        
        if "error" in response:
            return {"error": response["error"]}
        
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "{}")
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON response", "raw": content}
    
    def get_models(self) -> List[Dict]:
        """Get list of available models."""
        try:
            response = self.session.get(f"{self.BASE_URL}/models", timeout=30)
            response.raise_for_status()
            return response.json().get("data", [])
        except requests.exceptions.RequestException as e:
            print(f"Failed to get models: {e}")
            return []
    
    def get_generation_stats(self, generation_id: str) -> Optional[Dict]:
        """
        Get detailed stats for a generation (after completion).
        
        Returns native token counts and actual cost.
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/generation?id={generation_id}",
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return None
    
    # ==================== Sports Betting Analysis ====================
    
    def analyze_betting_opportunity(self, odds_data: Dict, 
                                    research_data: Dict,
                                    model: str = "openai/gpt-4o") -> Dict:
        """
        Analyze a betting opportunity using AI.
        
        Args:
            odds_data: Odds from Sports Odds API
            research_data: Research from Perplexity
            model: Model to use for analysis
        
        Returns:
            Dict with recommendation, confidence, reasoning
        """
        prompt = f"""
        Analyze this sports betting opportunity and provide a recommendation.
        
        ## Odds Data
        {json.dumps(odds_data, indent=2)}
        
        ## Research Data
        {json.dumps(research_data, indent=2)}
        
        Provide your analysis in JSON format with these fields:
        - recommendation: "bet_home", "bet_away", "bet_over", "bet_under", or "no_bet"
        - confidence: float between 0 and 1
        - edge_percentage: estimated edge over the market (can be negative)
        - reasoning: detailed explanation
        - key_factors: list of most important factors
        - risks: list of potential risks
        - suggested_stake: percentage of bankroll (0-5%)
        """
        
        return self.get_json_response(
            prompt=prompt,
            model=model,
            system_prompt="""You are an expert sports betting analyst with deep knowledge of 
            statistics, probability, and sports dynamics. Provide objective, data-driven analysis.
            Be conservative with confidence levels. Always consider the vig/juice in your edge calculations."""
        )
    
    def compare_odds_to_kalshi(self, sports_odds: Dict, 
                               kalshi_market: Dict,
                               research: Dict = None,
                               model: str = "openai/gpt-4o") -> Dict:
        """
        Compare sportsbook odds to Kalshi market prices for arbitrage.
        
        Args:
            sports_odds: Odds from traditional sportsbooks
            kalshi_market: Kalshi market data
            research: Optional research context
            model: Model to use
        
        Returns:
            Dict with arbitrage analysis
        """
        prompt = f"""
        Compare traditional sportsbook odds with Kalshi prediction market prices 
        to identify potential arbitrage or value opportunities.
        
        ## Sportsbook Odds
        {json.dumps(sports_odds, indent=2)}
        
        ## Kalshi Market
        {json.dumps(kalshi_market, indent=2)}
        
        {"## Research Context" + chr(10) + json.dumps(research, indent=2) if research else ""}
        
        Analyze in JSON format:
        - implied_prob_sportsbook: implied probability from sportsbook
        - implied_prob_kalshi: implied probability from Kalshi
        - probability_difference: difference in implied probabilities
        - arbitrage_opportunity: boolean
        - arbitrage_profit_pct: potential profit percentage if arbitrage exists
        - value_bet: which side offers value (if any)
        - recommended_action: specific recommendation
        - reasoning: detailed explanation
        """
        
        return self.get_json_response(
            prompt=prompt,
            model=model,
            system_prompt="""You are an expert in sports betting and prediction markets.
            Analyze odds differences to find arbitrage and value betting opportunities.
            Account for fees on both platforms in your calculations."""
        )
    
    def generate_bet_decision(self, 
                              event_info: Dict,
                              odds_analysis: Dict,
                              perplexity_research: Dict,
                              portfolio_context: Dict = None,
                              model: str = "anthropic/claude-3.5-sonnet") -> Dict:
        """
        Generate a final betting decision using all available data.
        
        This is the main decision-making function that synthesizes all inputs.
        
        Args:
            event_info: Basic event information
            odds_analysis: Odds and value analysis
            perplexity_research: Research from Perplexity
            portfolio_context: Current portfolio state
            model: Model to use for decision
        
        Returns:
            Comprehensive decision with all details
        """
        prompt = f"""
        Make a betting decision based on all available information.
        
        ## Event Information
        {json.dumps(event_info, indent=2)}
        
        ## Odds Analysis
        {json.dumps(odds_analysis, indent=2)}
        
        ## Research Summary
        {json.dumps(perplexity_research, indent=2)}
        
        ## Portfolio Context
        {json.dumps(portfolio_context or {}, indent=2)}
        
        Provide your decision in JSON format:
        {{
            "decision": "place_bet" or "skip",
            "bet_type": "moneyline", "spread", "total", "prop", or null,
            "bet_side": "home", "away", "over", "under", or null,
            "bet_amount_usd": float or null,
            "confidence": float 0-1,
            "expected_value": float (positive = good bet),
            "win_probability": float 0-1,
            "reasoning": "string",
            "key_insights": ["list", "of", "insights"],
            "risk_factors": ["list", "of", "risks"],
            "timing_recommendation": "bet now", "wait for line movement", "avoid"
        }}
        """
        
        return self.get_json_response(
            prompt=prompt,
            model=model,
            system_prompt="""You are a professional sports bettor making decisions for a 
            systematic betting operation. Be disciplined and only recommend bets with 
            positive expected value. Factor in bankroll management and avoid excessive risk.
            A 55% edge is excellent; don't expect unrealistic returns."""
        )


# Convenience function
def get_client() -> OpenRouterClient:
    """Get a configured OpenRouter client."""
    return OpenRouterClient()
