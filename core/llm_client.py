"""
Vanta LLM Client
================
Gemini LLM integration for enhanced agent reasoning.
"""

import os
import time
from typing import Optional, Dict, Any
from functools import lru_cache

# Lazy import to avoid startup overhead if not configured
_gemini_client = None


class GeminiClient:
    """
    Wrapper for Google Gemini API with graceful fallback.
    
    Features:
    - Singleton pattern for efficiency
    - Rate limiting protection
    - Graceful error handling
    """
    
    def __init__(self, api_key: str):
        """Initialize Gemini client with API key."""
        import google.generativeai as genai
        
        self.api_key = api_key
        genai.configure(api_key=api_key)
        
        # Use Gemini 1.5 Flash for fast responses
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self._last_call_time = 0
        self._min_interval = 0.5  # Minimum seconds between calls
        
    def _rate_limit(self):
        """Enforce rate limiting between API calls."""
        elapsed = time.time() - self._last_call_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call_time = time.time()
    
    def generate_reasoning(
        self,
        context: Dict[str, Any],
        agent_role: str
    ) -> Optional[str]:
        """
        Generate agent reasoning using Gemini.
        
        Args:
            context: Dictionary with action/assessment details
            agent_role: 'optimizer', 'risk_officer', or 'negotiator'
            
        Returns:
            LLM-generated reasoning text, or None on failure
        """
        try:
            self._rate_limit()
            
            prompt = self._build_reasoning_prompt(context, agent_role)
            response = self.model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.7,
                    'max_output_tokens': 300,
                }
            )
            
            if response and response.text:
                return response.text.strip()
            return None
            
        except Exception as e:
            # Log error but don't crash - fallback will be used
            print(f"[LLM] Gemini API error: {e}")
            return None
    
    def _build_reasoning_prompt(
        self,
        context: Dict[str, Any],
        agent_role: str
    ) -> str:
        """Build a role-specific prompt for the agent."""
        
        if agent_role == "optimizer":
            return f"""You are the Optimizer Agent in Vanta, a payment operations AI system.
Your role is to maximize payment success rates while minimizing latency.

You are proposing the following action:
- Action Type: {context.get('action_type', 'unknown')}
- Description: {context.get('description', 'N/A')}
- Expected Success Rate Improvement: {context.get('expected_improvement', 0):.1%}
- Risk Score: {context.get('risk_score', 0):.1%}
- Hypothesis ID: {context.get('hypothesis_id', 'N/A')}

Weights considered:
- Success Rate Weight: {context.get('success_weight', 0.5)}
- Latency Weight: {context.get('latency_weight', 0.3)}
- Cost Weight: {context.get('cost_weight', 0.2)}

Can Rollback: {context.get('can_rollback', True)}

Write a concise (3-4 sentences) explanation of why this action is recommended.
Focus on business impact and trade-offs. Be confident but acknowledge risks.
Do not use markdown formatting."""
        
        elif agent_role == "risk_officer":
            return f"""You are the Risk Officer Agent in Vanta, a payment operations AI system.
Your role is to ensure safety, compliance, and prevent catastrophic failures.

You have assessed the following action:
- Action ID: {context.get('action_id', 'unknown')}
- Verdict: {context.get('verdict', 'N/A')}
- Overall Risk: {context.get('overall_risk', 0):.1%}
- Risk Factors: {context.get('risk_factors', [])}
- Mitigations: {context.get('mitigations', [])}
- Conditions: {context.get('conditions', [])}

Write a concise (3-4 sentences) risk assessment explanation.
Explain your verdict and highlight the most critical risk factors.
If approving with conditions, be specific about what must be monitored.
Do not use markdown formatting."""
        
        elif agent_role == "negotiator":
            return f"""You are the Negotiation Engine in Vanta, a payment operations AI system.
Your role is to mediate between the Optimizer and Risk Officer agents.

Negotiation details:
- Final Decision: {context.get('decision', 'N/A')}
- Rounds of Negotiation: {context.get('rounds', 0)}
- Optimizer Position: {context.get('optimizer_reasoning', 'N/A')}
- Risk Officer Position: {context.get('risk_officer_reasoning', 'N/A')}
- Compromise: {context.get('compromise_details', 'None')}

Write a concise (3-4 sentences) summary of how consensus was reached.
Highlight the key trade-offs and any compromises made.
Do not use markdown formatting."""
        
        return "Explain your decision briefly."
    
    def analyze_pattern(self, pattern_data: Dict[str, Any]) -> Optional[str]:
        """
        Analyze a payment pattern using Gemini.
        
        Args:
            pattern_data: Dictionary with pattern details
            
        Returns:
            LLM-generated analysis, or None on failure
        """
        try:
            self._rate_limit()
            
            prompt = f"""You are analyzing a payment pattern in Vanta, a payment operations AI system.

Pattern Details:
- Type: {pattern_data.get('pattern_type', 'unknown')}
- Entity: {pattern_data.get('entity', 'N/A')}
- Severity: {pattern_data.get('severity', 'N/A')}
- Metric Change: {pattern_data.get('metric_change', 0):.1%}
- Sample Size: {pattern_data.get('sample_size', 0)} transactions

Provide a brief (2-3 sentences) analysis of what this pattern indicates
and what might be causing it. Be specific to payments/fintech domain.
Do not use markdown formatting."""

            response = self.model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.7,
                    'max_output_tokens': 200,
                }
            )
            
            if response and response.text:
                return response.text.strip()
            return None
            
        except Exception as e:
            print(f"[LLM] Gemini API error: {e}")
            return None


def get_gemini_client() -> Optional[GeminiClient]:
    """
    Get the singleton Gemini client instance.
    
    Returns:
        GeminiClient if configured, None otherwise
    """
    global _gemini_client
    
    if _gemini_client is not None:
        return _gemini_client
    
    # Try to load API key from environment
    api_key = os.environ.get('GEMINI_API_KEY')
    
    # Try loading from .env file if not in environment
    if not api_key:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.environ.get('GEMINI_API_KEY')
        except ImportError:
            pass
    
    if not api_key:
        print("[LLM] No GEMINI_API_KEY found. Using fallback reasoning.")
        return None
    
    try:
        _gemini_client = GeminiClient(api_key)
        print("[LLM] Gemini client initialized successfully.")
        return _gemini_client
    except Exception as e:
        print(f"[LLM] Failed to initialize Gemini client: {e}")
        return None


def reset_client():
    """Reset the singleton client (for testing)."""
    global _gemini_client
    _gemini_client = None
