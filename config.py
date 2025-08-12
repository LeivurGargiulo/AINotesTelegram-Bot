"""
Configuration settings for the Telegram Notes Bot.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

# Database configuration
DATABASE_FILE = os.getenv('DATABASE_FILE', 'notes_bot.db')

# LLM configuration
LLM_API_URL = os.getenv('LLM_API_URL', 'http://localhost:11434/api/generate')
LLM_MODEL = os.getenv('LLM_MODEL', 'llama2')

# Note categories
VALID_CATEGORIES = ['task', 'idea', 'quote', 'other']

# Display settings
MAX_PREVIEW_LENGTH = 50
TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'