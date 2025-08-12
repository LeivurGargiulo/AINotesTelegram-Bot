"""
Enhanced structured logging configuration for the Discord Notes Bot.
Includes error tracking, performance monitoring, and production-ready features.
"""
import logging
import logging.handlers
import os
import time
import traceback
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from config import LOG_LEVEL, LOG_FORMAT, LOG_FILE, LOG_MAX_SIZE, LOG_BACKUP_COUNT


class PerformanceLogger:
    """Tracks performance metrics and timing information."""
    
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.error_counts: Dict[str, int] = {}
        self.start_times: Dict[str, float] = {}
    
    def start_timer(self, operation: str):
        """Start timing an operation."""
        self.start_times[operation] = time.time()
    
    def end_timer(self, operation: str) -> float:
        """End timing an operation and return duration."""
        if operation not in self.start_times:
            return 0.0
        
        duration = time.time() - self.start_times[operation]
        if operation not in self.metrics:
            self.metrics[operation] = []
        self.metrics[operation].append(duration)
        
        # Keep only last 100 measurements
        if len(self.metrics[operation]) > 100:
            self.metrics[operation] = self.metrics[operation][-100:]
        
        del self.start_times[operation]
        return duration
    
    def record_error(self, error_type: str):
        """Record an error occurrence."""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        stats = {}
        for operation, times in self.metrics.items():
            if times:
                stats[operation] = {
                    'count': len(times),
                    'avg_time': sum(times) / len(times),
                    'min_time': min(times),
                    'max_time': max(times),
                    'recent_avg': sum(times[-10:]) / min(len(times), 10)
                }
        return stats
    
    def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics."""
        return self.error_counts.copy()


class StructuredFormatter(logging.Formatter):
    """Enhanced formatter with structured logging support."""
    
    def format(self, record):
        # Add structured fields
        if not hasattr(record, 'structured_data'):
            record.structured_data = {}
        
        # Add performance context if available
        if hasattr(record, 'operation'):
            record.structured_data['operation'] = record.operation
        if hasattr(record, 'duration'):
            record.structured_data['duration'] = record.duration
        if hasattr(record, 'user_id'):
            record.structured_data['user_id'] = record.user_id
        
        # Format the message
        formatted = super().format(record)
        
        # Add structured data if present
        if record.structured_data:
            import json
            structured_str = json.dumps(record.structured_data)
            formatted += f" | {structured_str}"
        
        return formatted


class ErrorTracker:
    """Tracks and manages error information."""
    
    def __init__(self, max_errors: int = 100):
        self.errors: List[Dict[str, Any]] = []
        self.max_errors = max_errors
    
    def add_error(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Add an error to the tracker."""
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
            'context': context or {}
        }
        
        self.errors.append(error_info)
        
        # Keep only the most recent errors
        if len(self.errors) > self.max_errors:
            self.errors = self.errors[-self.max_errors:]
    
    def get_recent_errors(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get the most recent errors."""
        return self.errors[-count:] if self.errors else []
    
    def get_error_summary(self) -> Dict[str, int]:
        """Get a summary of error types."""
        summary = {}
        for error in self.errors:
            error_type = error['error_type']
            summary[error_type] = summary.get(error_type, 0) + 1
        return summary


# Global instances
performance_logger = PerformanceLogger()
error_tracker = ErrorTracker()


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
    formatter = StructuredFormatter(LOG_FORMAT)
    
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
            maxBytes=LOG_MAX_SIZE,
            backupCount=LOG_BACKUP_COUNT
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


def log_performance(operation: str, user_id: Optional[int] = None):
    """Decorator to log performance metrics."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            performance_logger.start_timer(operation)
            try:
                result = await func(*args, **kwargs)
                duration = performance_logger.end_timer(operation)
                
                logger = get_logger(__name__)
                logger.info(
                    f"Operation '{operation}' completed successfully",
                    extra={
                        'operation': operation,
                        'duration': duration,
                        'user_id': user_id,
                        'structured_data': {
                            'operation': operation,
                            'duration': duration,
                            'user_id': user_id,
                            'status': 'success'
                        }
                    }
                )
                return result
            except Exception as e:
                duration = performance_logger.end_timer(operation)
                performance_logger.record_error(type(e).__name__)
                error_tracker.add_error(e, {
                    'operation': operation,
                    'user_id': user_id,
                    'duration': duration
                })
                
                logger = get_logger(__name__)
                logger.error(
                    f"Operation '{operation}' failed: {str(e)}",
                    extra={
                        'operation': operation,
                        'duration': duration,
                        'user_id': user_id,
                        'structured_data': {
                            'operation': operation,
                            'duration': duration,
                            'user_id': user_id,
                            'status': 'error',
                            'error': str(e)
                        }
                    }
                )
                raise
        
        def sync_wrapper(*args, **kwargs):
            performance_logger.start_timer(operation)
            try:
                result = func(*args, **kwargs)
                duration = performance_logger.end_timer(operation)
                
                logger = get_logger(__name__)
                logger.info(
                    f"Operation '{operation}' completed successfully",
                    extra={
                        'operation': operation,
                        'duration': duration,
                        'user_id': user_id,
                        'structured_data': {
                            'operation': operation,
                            'duration': duration,
                            'user_id': user_id,
                            'status': 'success'
                        }
                    }
                )
                return result
            except Exception as e:
                duration = performance_logger.end_timer(operation)
                performance_logger.record_error(type(e).__name__)
                error_tracker.add_error(e, {
                    'operation': operation,
                    'user_id': user_id,
                    'duration': duration
                })
                
                logger = get_logger(__name__)
                logger.error(
                    f"Operation '{operation}' failed: {str(e)}",
                    extra={
                        'operation': operation,
                        'duration': duration,
                        'user_id': user_id,
                        'structured_data': {
                            'operation': operation,
                            'duration': duration,
                            'user_id': user_id,
                            'status': 'error',
                            'error': str(e)
                        }
                    }
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def get_performance_stats() -> Dict[str, Any]:
    """Get current performance statistics."""
    return performance_logger.get_performance_stats()


def get_error_stats() -> Dict[str, Any]:
    """Get current error statistics."""
    return {
        'error_counts': error_tracker.get_error_summary(),
        'recent_errors': error_tracker.get_recent_errors(5)
    }


# Import asyncio for the decorator
import asyncio