"""
LLM client for categorizing notes using a local LLM.
Supports various local LLM APIs like Ollama, local OpenAI-compatible APIs, etc.
"""
import requests
import json
import logging
from typing import Optional
from config import LLM_API_URL, LLM_MODEL, VALID_CATEGORIES

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with local LLM for note categorization."""
    
    def __init__(self, api_url: str = LLM_API_URL, model: str = LLM_MODEL):
        """Initialize the LLM client."""
        self.api_url = api_url
        self.model = model
        self.categorization_prompt = "Categorize this note as 'task', 'idea', 'quote', or 'other'. Return only the category."
    
    def categorize_note_with_llm(self, note_text: str) -> str:
        """
        Categorize a note using the local LLM.
        Returns one of: 'task', 'idea', 'quote', 'other'
        Falls back to 'other' if LLM is unavailable or returns invalid category.
        """
        try:
            # Try Ollama API first (most common local LLM)
            category = self._try_ollama_api(note_text)
            if category and category in VALID_CATEGORIES:
                return category
            
            # Try OpenAI-compatible API
            category = self._try_openai_compatible_api(note_text)
            if category and category in VALID_CATEGORIES:
                return category
            
            # Fallback to 'other' if LLM fails
            logger.warning(f"LLM categorization failed for note: {note_text[:50]}...")
            return 'other'
            
        except Exception as e:
            logger.error(f"Error categorizing note with LLM: {e}")
            return 'other'
    
    def _try_ollama_api(self, note_text: str) -> Optional[str]:
        """Try to categorize using Ollama API."""
        try:
            prompt = f"{self.categorization_prompt}\n\nNote: {note_text}"
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "max_tokens": 10
                }
            }
            
            response = requests.post(self.api_url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            category = result.get('response', '').strip().lower()
            
            # Clean up the response to extract just the category
            category = self._clean_category_response(category)
            
            logger.info(f"Ollama API categorized note as: {category}")
            return category
            
        except Exception as e:
            logger.debug(f"Ollama API failed: {e}")
            return None
    
    def _try_openai_compatible_api(self, note_text: str) -> Optional[str]:
        """Try to categorize using OpenAI-compatible API."""
        try:
            # Try OpenAI-compatible endpoint
            openai_url = self.api_url.replace('/api/generate', '/v1/chat/completions')
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": self.categorization_prompt
                    },
                    {
                        "role": "user",
                        "content": f"Note: {note_text}"
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 10
            }
            
            response = requests.post(openai_url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            category = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip().lower()
            
            # Clean up the response to extract just the category
            category = self._clean_category_response(category)
            
            logger.info(f"OpenAI-compatible API categorized note as: {category}")
            return category
            
        except Exception as e:
            logger.debug(f"OpenAI-compatible API failed: {e}")
            return None
    
    def _clean_category_response(self, response: str) -> str:
        """Clean up LLM response to extract valid category."""
        # Remove common prefixes/suffixes and quotes
        response = response.strip().lower()
        response = response.replace('"', '').replace("'", '')
        response = response.replace('category:', '').replace('category', '')
        response = response.replace('answer:', '').replace('answer', '')
        response = response.strip()
        
        # Check if it's a valid category
        if response in VALID_CATEGORIES:
            return response
        
        # Try to extract category from longer responses
        for category in VALID_CATEGORIES:
            if category in response:
                return category
        
        return 'other'


# Global LLM client instance
llm_client = LLMClient()


def categorize_note_with_llm(note_text: str) -> str:
    """
    Convenience function to categorize a note using the LLM.
    This is the function that should be used by the bot.
    """
    return llm_client.categorize_note_with_llm(note_text)