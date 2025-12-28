"""
Perplexity AI Client

Client for Perplexity's Sonar API providing:
- Real-time web search and research
- Citation-backed answers
- Domain filtering for trusted sources
- Streaming responses

API Documentation: https://docs.perplexity.ai/
"""
import os
import json
import requests
from typing import List, Dict, Optional, Any, Generator


class PerplexityClient:
    """
    Client for Perplexity Sonar API for research and fact-finding.
    """
    
    BASE_URL = "https://api.perplexity.ai"
    
    # Available models
    MODELS = {
        "sonar": "sonar",           # Fast, lightweight
        "sonar-pro": "sonar-pro",   # Deeper reasoning, 2x citations
    }
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def chat(self, messages: List[Dict], model: str = "sonar-pro",
             temperature: float = 0.2, max_tokens: int = 4096,
             search_domain_filter: List[str] = None,
             return_citations: bool = True,
             return_related_questions: bool = False,
             stream: bool = False) -> Dict:
        """
        Send a chat completion request.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use ('sonar' or 'sonar-pro')
            temperature: Response randomness (0-2)
            max_tokens: Maximum tokens in response
            search_domain_filter: List of domains to restrict search
            return_citations: Include source citations
            return_related_questions: Include suggested follow-up questions
            stream: Enable streaming response
        
        Returns:
            Dict with response content and metadata
        """
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "return_citations": return_citations,
            "return_related_questions": return_related_questions,
            "stream": stream
        }
        
        if search_domain_filter:
            payload["search_domain_filter"] = search_domain_filter
        
        try:
            response = self.session.post(
                f"{self.BASE_URL}/chat/completions",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Perplexity API error: {e}")
            return {"error": str(e)}
    
    def chat_stream(self, messages: List[Dict], model: str = "sonar-pro",
                    temperature: float = 0.2, max_tokens: int = 4096,
                    search_domain_filter: List[str] = None) -> Generator[str, None, None]:
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
        
        if search_domain_filter:
            payload["search_domain_filter"] = search_domain_filter
        
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
    
    def ask(self, question: str, model: str = "sonar-pro",
            context: str = None, domains: List[str] = None) -> Dict:
        """
        Simple question-answering interface.
        
        Args:
            question: The question to ask
            model: Model to use
            context: Optional context to include
            domains: Optional list of domains to search
        
        Returns:
            Dict with 'answer', 'citations', and 'sources'
        """
        messages = []
        
        if context:
            messages.append({
                "role": "system",
                "content": context
            })
        
        messages.append({
            "role": "user",
            "content": question
        })
        
        response = self.chat(
            messages=messages,
            model=model,
            search_domain_filter=domains,
            return_citations=True
        )
        
        if "error" in response:
            return response
        
        # Extract content and citations
        choice = response.get("choices", [{}])[0]
        message = choice.get("message", {})
        
        return {
            "answer": message.get("content", ""),
            "citations": response.get("citations", []),
            "model": response.get("model"),
            "usage": response.get("usage", {})
        }
    
    # ==================== Sports Research Methods ====================
    
    def research_team(self, team_name: str, sport: str = None) -> Dict:
        """
        Research a sports team's recent performance, injuries, news.
        
        Args:
            team_name: Name of the team
            sport: Optional sport context
        
        Returns:
            Research results with citations
        """
        sport_context = f" ({sport})" if sport else ""
        
        question = f"""
        Provide a comprehensive analysis of {team_name}{sport_context}:
        
        1. Recent Performance: Last 5-10 games, win/loss record, scoring trends
        2. Current Injuries: Key players injured or questionable
        3. Recent News: Any significant team news, trades, coaching changes
        4. Current Form: Hot/cold streaks, momentum indicators
        5. Key Statistics: Relevant stats that indicate team strength
        
        Focus on information relevant for betting analysis.
        """
        
        return self.ask(
            question=question,
            context="You are a sports analyst providing factual, data-driven research for betting analysis. Always cite your sources.",
            domains=["espn.com", "cbssports.com", "sports.yahoo.com", 
                    "bleacherreport.com", "theathletic.com"]
        )
    
    def research_matchup(self, team1: str, team2: str, 
                         sport: str = None, event_date: str = None) -> Dict:
        """
        Research a specific matchup between two teams.
        
        Args:
            team1: First team
            team2: Second team
            sport: Sport type
            event_date: Date of the matchup
        
        Returns:
            Matchup analysis with predictions and citations
        """
        date_context = f" on {event_date}" if event_date else ""
        sport_context = f" {sport}" if sport else ""
        
        question = f"""
        Analyze the upcoming{sport_context} matchup between {team1} and {team2}{date_context}:
        
        1. Head-to-Head History: Recent meetings and outcomes
        2. Current Form: Both teams' recent performance
        3. Key Injuries: Impact players missing or questionable
        4. Statistical Comparison: Key metrics comparison
        5. Expert Predictions: What analysts are saying
        6. Betting Line Movement: How lines have moved (if applicable)
        7. Key Factors: What will determine the outcome
        
        Provide factual analysis useful for betting decisions.
        """
        
        return self.ask(
            question=question,
            context="You are a sports betting analyst providing objective matchup analysis. Focus on facts and statistics.",
            domains=["espn.com", "cbssports.com", "sports.yahoo.com", 
                    "actionnetwork.com", "covers.com"]
        )
    
    def get_injury_report(self, team_name: str, sport: str) -> Dict:
        """Get current injury report for a team."""
        question = f"""
        What is the current injury report for {team_name} ({sport})?
        
        List all injured players with:
        - Player name and position
        - Injury type
        - Status (Out, Doubtful, Questionable, Probable)
        - Expected return date if known
        
        Include any players who recently returned from injury.
        """
        
        return self.ask(
            question=question,
            context="Provide current, accurate injury information.",
            domains=["espn.com", "cbssports.com", "rotowire.com", "fantasypros.com"]
        )
    
    def get_betting_trends(self, team_name: str = None, 
                          matchup: str = None) -> Dict:
        """Get betting trends and public money information."""
        if matchup:
            question = f"""
            What are the current betting trends for {matchup}?
            
            Include:
            - Line movement (opening vs current)
            - Public betting percentages
            - Sharp money indicators
            - Any notable betting action
            """
        else:
            question = f"""
            What are the recent betting trends for {team_name}?
            
            Include:
            - Against the spread (ATS) record
            - Over/under trends
            - Home/away performance
            - Public betting patterns
            """
        
        return self.ask(
            question=question,
            context="Provide betting trends and analysis data.",
            domains=["actionnetwork.com", "covers.com", "vegasinsider.com", 
                    "sportsline.com", "oddshark.com"]
        )
    
    def research_weather_impact(self, event_location: str, 
                                event_date: str, sport: str) -> Dict:
        """Research weather conditions that may impact an event."""
        question = f"""
        What will the weather conditions be for the {sport} event 
        in {event_location} on {event_date}?
        
        Include:
        - Temperature forecast
        - Precipitation likelihood
        - Wind conditions
        - How weather typically affects {sport} games
        - Historical performance in similar conditions
        """
        
        return self.ask(
            question=question,
            context="Provide weather analysis relevant to sports betting.",
            domains=["weather.com", "accuweather.com", "espn.com"]
        )


# Convenience function
def get_client() -> PerplexityClient:
    """Get a configured Perplexity client."""
    return PerplexityClient()
