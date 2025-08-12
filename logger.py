"""
Structured logging configuration for the Telegram Notes Bot.
"""
import logging
import logging.handlers
import os
from config import LOG_LEVEL, LOG_FORMAT, LOG_FILE


def setup_logger(name: str = __name__) -> logging.Logger:
    """
    Set up a structured logger with file and console handlers.
    
    Args:
        name: The logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Set log level
    log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    if LOG_FILE:
        # Ensure log directory exists
        log_dir = os.path.dirname(LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = __name__) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: The logger name
        
    Returns:
        Logger instance
    """
    return setup_logger(name)