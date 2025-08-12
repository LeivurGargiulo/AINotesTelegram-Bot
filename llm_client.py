"""
LLM client for categorizing notes using a local LLM.
Supports various local LLM APIs like Ollama, local OpenAI-compatible APIs, etc.
"""
import requests
import json
import logging
from typing import Optional
from config import LLM_API_URL, LLM_MODEL, VALID_CATEGORIES, OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL, USE_OPENROUTER
from logger import get_logger

# Set up logging
logger = get_logger(__name__)


class LLMClient:
    """Client for interacting with local LLM for note categorization."""
    
    def __init__(self, api_url: str = LLM_API_URL, model: str = LLM_MODEL):
        """Initialize the LLM client."""
        self.api_url = api_url
        self.model = model
        self.categorization_prompt = "Categorize this note as 'task', 'idea', 'quote', or 'other'. Return only the category."
        
        # OpenRouter configuration
        self.use_openrouter = USE_OPENROUTER
        self.openrouter_api_key = OPENROUTER_API_KEY
        self.openrouter_base_url = OPENROUTER_BASE_URL
        self.openrouter_model = OPENROUTER_MODEL
        
        logger.info(f"LLM client initialized with API: {api_url}, model: {model}")
        if self.use_openrouter:
            logger.info(f"OpenRouter enabled with model: {self.openrouter_model}")
        else:
            logger.info("OpenRouter disabled, using local LLM")
    
    def categorize_note_with_llm(self, note_text: str) -> str:
        """
        Categorize a note using the LLM.
        Returns one of: 'task', 'idea', 'quote', 'other'
        Falls back to 'other' if LLM is unavailable or returns invalid category.
        """
        try:
            logger.info(f"Attempting to categorize note: {note_text[:50]}...")
            
            # Try OpenRouter API first if enabled
            if self.use_openrouter and self.openrouter_api_key:
                category = self._try_openrouter_api(note_text)
                if category and category in VALID_CATEGORIES:
                    logger.info(f"Successfully categorized note as '{category}' using OpenRouter API")
                    return category
            
            # Try Ollama API (most common local LLM)
            category = self._try_ollama_api(note_text)
            if category and category in VALID_CATEGORIES:
                logger.info(f"Successfully categorized note as '{category}' using Ollama API")
                return category
            
            # Try OpenAI-compatible API
            category = self._try_openai_compatible_api(note_text)
            if category and category in VALID_CATEGORIES:
                logger.info(f"Successfully categorized note as '{category}' using OpenAI-compatible API")
                return category
            
            # Fallback to 'other' if LLM fails
            logger.warning(f"LLM categorization failed for note: {note_text[:50]}..., falling back to 'other'")
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
            
            logger.debug(f"Sending request to Ollama API: {self.api_url}")
            response = requests.post(self.api_url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            category = result.get('response', '').strip().lower()
            
            # Clean up the response to extract just the category
            category = self._clean_category_response(category)
            
            logger.debug(f"Ollama API raw response: {result.get('response', '')}")
            logger.debug(f"Ollama API categorized note as: {category}")
            return category
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"Ollama API request failed: {e}")
            return None
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
            
            logger.debug(f"Sending request to OpenAI-compatible API: {openai_url}")
            response = requests.post(openai_url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            category = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip().lower()
            
            # Clean up the response to extract just the category
            category = self._clean_category_response(category)
            
            logger.debug(f"OpenAI-compatible API raw response: {result}")
            logger.debug(f"OpenAI-compatible API categorized note as: {category}")
            return category
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"OpenAI-compatible API request failed: {e}")
            return None
        except Exception as e:
            logger.debug(f"OpenAI-compatible API failed: {e}")
            return None
    
    def _try_openrouter_api(self, note_text: str) -> Optional[str]:
        """Try to categorize using OpenRouter API."""
        try:
            if not self.openrouter_api_key:
                logger.debug("OpenRouter API key not configured")
                return None
            
            url = f"{self.openrouter_base_url}/chat/completions"
            
            payload = {
                "model": self.openrouter_model,
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
            
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/your-repo/telegram-notes-bot",  # Optional but recommended
                "X-Title": "Telegram Notes Bot"  # Optional but recommended
            }
            
            logger.debug(f"Sending request to OpenRouter API: {url}")
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            
            result = response.json()
            category = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip().lower()
            
            # Clean up the response to extract just the category
            category = self._clean_category_response(category)
            
            logger.debug(f"OpenRouter API raw response: {result}")
            logger.debug(f"OpenRouter API categorized note as: {category}")
            return category
            
        except requests.exceptions.RequestException as e:
            logger.debug(f"OpenRouter API request failed: {e}")
            return None
        except Exception as e:
            logger.debug(f"OpenRouter API failed: {e}")
            return None
    
    def _clean_category_response(self, response: str) -> str:
        """Clean up the LLM response to extract just the category."""
        # Remove common prefixes/suffixes
        response = response.strip().lower()
        
        # Remove quotes
        response = response.strip('"\'')
        
        # Remove common prefixes
        prefixes_to_remove = ['category:', 'category is:', 'the category is:', 'answer:', 'response:']
        for prefix in prefixes_to_remove:
            if response.startswith(prefix):
                response = response[len(prefix):].strip()
        
        # Remove common suffixes
        suffixes_to_remove = ['.', '!', '?', ';', ',']
        for suffix in suffixes_to_remove:
            if response.endswith(suffix):
                response = response[:-1].strip()
        
        logger.debug(f"Cleaned category response: '{response}'")
        return response


# Global LLM client instance
llm_client = LLMClient()


def categorize_note_with_llm(note_text: str) -> str:
    """
    Convenience function to categorize a note using the global LLM client.
    
    Args:
        note_text: The text of the note to categorize
        
    Returns:
        The category: 'task', 'idea', 'quote', or 'other'
    """
    return llm_client.categorize_note_with_llm(note_text)