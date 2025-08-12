"""
Configuration settings for the Telegram Notes Bot.
"""
import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

# Database configuration
DATABASE_FILE = os.getenv('DATABASE_FILE', 'notes_bot.db')

# Note categorization settings
# The bot now uses keyword-based categorization instead of AI

# Note categories
VALID_CATEGORIES = ['task', 'idea', 'quote', 'other']

# Display settings
MAX_PREVIEW_LENGTH = 50
TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'

# Pagination settings
NOTES_PER_PAGE = 10

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = os.getenv('LOG_FILE', 'bot.log')

# Reminder settings
REMINDER_TIMEZONE = os.getenv('REMINDER_TIMEZONE', 'UTC')