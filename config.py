"""
Configuration settings for the Discord Notes Bot.
Enhanced with better environment variable handling and production settings.
"""
import os
import logging
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN') or os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN or BOT_TOKEN environment variable is required")

# Database configuration
DATABASE_FILE = os.getenv('DATABASE_FILE', 'notes_bot.db')

# Note categorization settings
VALID_CATEGORIES = ['task', 'idea', 'quote', 'other']

# Display settings
MAX_PREVIEW_LENGTH = int(os.getenv('MAX_PREVIEW_LENGTH', '50'))
TIMESTAMP_FORMAT = os.getenv('TIMESTAMP_FORMAT', '%Y-%m-%d %H:%M:%S')

# Pagination settings
NOTES_PER_PAGE = int(os.getenv('NOTES_PER_PAGE', '10'))

# Rate limiting settings
RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
RATE_LIMIT_BUCKET_SIZE = int(os.getenv('RATE_LIMIT_BUCKET_SIZE', '10'))
RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', '60'))  # seconds

# Command cooldowns (in seconds)
COMMAND_COOLDOWNS = {
    'add': int(os.getenv('ADD_COOLDOWN', '5')),
    'list': int(os.getenv('LIST_COOLDOWN', '3')),
    'delete': int(os.getenv('DELETE_COOLDOWN', '3')),
    'search': int(os.getenv('SEARCH_COOLDOWN', '3')),
    'remind': int(os.getenv('REMIND_COOLDOWN', '5')),
    'reminders': int(os.getenv('REMINDERS_COOLDOWN', '3')),
    'debug': int(os.getenv('DEBUG_COOLDOWN', '10')),
}

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
LOG_FILE = os.getenv('LOG_FILE', 'discord_bot.log')
LOG_MAX_SIZE = int(os.getenv('LOG_MAX_SIZE', '10')) * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))

# Reminder settings
REMINDER_TIMEZONE = os.getenv('REMINDER_TIMEZONE', 'UTC')
REMINDER_MAX_PER_USER = int(os.getenv('REMINDER_MAX_PER_USER', '10'))

# Cache settings
CACHE_ENABLED = os.getenv('CACHE_ENABLED', 'true').lower() == 'true'
CACHE_TTL = int(os.getenv('CACHE_TTL', '300'))  # 5 minutes

# Performance settings
MAX_CONCURRENT_OPERATIONS = int(os.getenv('MAX_CONCURRENT_OPERATIONS', '10'))
DATABASE_TIMEOUT = int(os.getenv('DATABASE_TIMEOUT', '30'))

# Security settings
ALLOWED_GUILDS = os.getenv('ALLOWED_GUILDS', '').split(',') if os.getenv('ALLOWED_GUILDS') else []
BLOCKED_USERS = os.getenv('BLOCKED_USERS', '').split(',') if os.getenv('BLOCKED_USERS') else []

# Development settings
DEBUG_MODE = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
TESTING_MODE = os.getenv('TESTING_MODE', 'false').lower() == 'true'

def get_config() -> Dict[str, Any]:
    """Get all configuration as a dictionary."""
    return {
        'bot_token': BOT_TOKEN,
        'database_file': DATABASE_FILE,
        'valid_categories': VALID_CATEGORIES,
        'max_preview_length': MAX_PREVIEW_LENGTH,
        'timestamp_format': TIMESTAMP_FORMAT,
        'notes_per_page': NOTES_PER_PAGE,
        'rate_limit_enabled': RATE_LIMIT_ENABLED,
        'rate_limit_bucket_size': RATE_LIMIT_BUCKET_SIZE,
        'rate_limit_window': RATE_LIMIT_WINDOW,
        'command_cooldowns': COMMAND_COOLDOWNS,
        'log_level': LOG_LEVEL,
        'log_format': LOG_FORMAT,
        'log_file': LOG_FILE,
        'log_max_size': LOG_MAX_SIZE,
        'log_backup_count': LOG_BACKUP_COUNT,
        'reminder_timezone': REMINDER_TIMEZONE,
        'reminder_max_per_user': REMINDER_MAX_PER_USER,
        'cache_enabled': CACHE_ENABLED,
        'cache_ttl': CACHE_TTL,
        'max_concurrent_operations': MAX_CONCURRENT_OPERATIONS,
        'database_timeout': DATABASE_TIMEOUT,
        'allowed_guilds': ALLOWED_GUILDS,
        'blocked_users': BLOCKED_USERS,
        'debug_mode': DEBUG_MODE,
        'testing_mode': TESTING_MODE,
    }