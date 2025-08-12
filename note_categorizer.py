"""
Simple note categorization system using keyword matching.
Replaces AI-based categorization with a rule-based approach.
"""
import re
from typing import List, Tuple
from config import VALID_CATEGORIES
from logger import get_logger

logger = get_logger(__name__)


class NoteCategorizer:
    """Simple rule-based note categorizer using keyword matching."""
    
    def __init__(self):
        """Initialize the categorizer with keyword patterns."""
        # Define keyword patterns for each category
        self.category_patterns = {
            'task': [
                r'\b(buy|purchase|get|pick up|order|shop|shopping)\b',
                r'\b(call|phone|text|message|email|contact)\b',
                r'\b(meeting|appointment|schedule|book|reserve)\b',
                r'\b(clean|wash|organize|sort|arrange)\b',
                r'\b(fix|repair|maintain|check|inspect)\b',
                r'\b(pay|bill|invoice|rent|mortgage)\b',
                r'\b(study|read|learn|practice|exercise)\b',
                r'\b(cook|prepare|make|bake|grill)\b',
                r'\b(drive|travel|go to|visit|attend)\b',
                r'\b(remember|don\'t forget|remind)\b',
                r'\b(todo|to do|to-do|task|action item)\b',
                r'\b(deadline|due|by|before|until)\b',
                r'\b(tomorrow|today|next week|this week)\b',
                r'\b(urgent|important|priority|asap)\b'
            ],
            'idea': [
                r'\b(idea|concept|thought|brainstorm|innovation)\b',
                r'\b(project|plan|strategy|approach|method)\b',
                r'\b(create|build|develop|design|invent)\b',
                r'\b(startup|business|company|venture)\b',
                r'\b(improve|enhance|optimize|upgrade)\b',
                r'\b(research|explore|investigate|analyze)\b',
                r'\b(what if|imagine|suppose|consider)\b',
                r'\b(feature|functionality|tool|app|website)\b',
                r'\b(problem|solution|solve|fix|address)\b',
                r'\b(opportunity|potential|possibility)\b',
                r'\b(creative|artistic|design|art)\b',
                r'\b(technology|tech|software|hardware)\b'
            ],
            'quote': [
                r'["""].*["""]',  # Quoted text
                r'\b(said|says|quoted|according to)\b',
                r'\b(quote|quotation|saying|proverb)\b',
                r'\b(inspirational|motivational|wise)\b',
                r'\b(famous|well-known|celebrity|author)\b',
                r'\b(book|article|speech|interview)\b',
                r'\b(philosophy|wisdom|life lesson)\b',
                r'\b(remember this|keep in mind|note to self)\b'
            ]
        }
        
        # Compile regex patterns for efficiency
        self.compiled_patterns = {}
        for category, patterns in self.category_patterns.items():
            self.compiled_patterns[category] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
        
        logger.info("Note categorizer initialized with keyword patterns")
    
    def categorize_note(self, note_text: str) -> str:
        """
        Categorize a note using keyword matching.
        
        Args:
            note_text: The text of the note to categorize
            
        Returns:
            The category: 'task', 'idea', 'quote', or 'other'
        """
        try:
            logger.info(f"Categorizing note: {note_text[:50]}...")
            
            # Convert to lowercase for case-insensitive matching
            text_lower = note_text.lower()
            
            # Calculate scores for each category
            category_scores = {}
            
            for category, patterns in self.compiled_patterns.items():
                score = 0
                for pattern in patterns:
                    matches = pattern.findall(text_lower)
                    score += len(matches)
                category_scores[category] = score
            
            # Find the category with the highest score
            if category_scores:
                best_category = max(category_scores, key=category_scores.get)
                best_score = category_scores[best_category]
                
                # Only categorize if we have a meaningful score (at least 1 match)
                if best_score > 0:
                    logger.info(f"Note categorized as '{best_category}' with score {best_score}")
                    return best_category
            
            # Default to 'other' if no clear category is found
            logger.info("No clear category found, defaulting to 'other'")
            return 'other'
            
        except Exception as e:
            logger.error(f"Error categorizing note: {e}")
            return 'other'
    
    def get_category_confidence(self, note_text: str) -> Tuple[str, float]:
        """
        Categorize a note and return confidence score.
        
        Args:
            note_text: The text of the note to categorize
            
        Returns:
            Tuple of (category, confidence_score)
        """
        try:
            text_lower = note_text.lower()
            category_scores = {}
            total_matches = 0
            
            for category, patterns in self.compiled_patterns.items():
                score = 0
                for pattern in patterns:
                    matches = pattern.findall(text_lower)
                    score += len(matches)
                category_scores[category] = score
                total_matches += score
            
            if total_matches == 0:
                return 'other', 0.0
            
            best_category = max(category_scores, key=category_scores.get)
            confidence = category_scores[best_category] / total_matches
            
            return best_category, confidence
            
        except Exception as e:
            logger.error(f"Error calculating category confidence: {e}")
            return 'other', 0.0


# Global categorizer instance
categorizer = NoteCategorizer()


def categorize_note_with_keywords(note_text: str) -> str:
    """
    Convenience function to categorize a note using keyword matching.
    
    Args:
        note_text: The text of the note to categorize
        
    Returns:
        The category: 'task', 'idea', 'quote', or 'other'
    """
    return categorizer.categorize_note(note_text)


def get_note_category_confidence(note_text: str) -> Tuple[str, float]:
    """
    Convenience function to categorize a note and get confidence score.
    
    Args:
        note_text: The text of the note to categorize
        
    Returns:
        Tuple of (category, confidence_score)
    """
    return categorizer.get_category_confidence(note_text)