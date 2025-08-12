"""
Rate limiting and security management for the Discord Notes Bot.
Provides advanced rate limiting, user management, and security features.
"""
import time
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, deque
from datetime import datetime, timedelta
import threading

from config import (
    RATE_LIMIT_ENABLED, RATE_LIMIT_BUCKET_SIZE, RATE_LIMIT_WINDOW,
    COMMAND_COOLDOWNS, ALLOWED_GUILDS, BLOCKED_USERS
)
from logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Advanced rate limiter with sliding window and multiple bucket support."""
    
    def __init__(self, bucket_size: int = 10, window_size: int = 60):
        self.bucket_size = bucket_size
        self.window_size = window_size
        self.buckets: Dict[str, deque] = defaultdict(lambda: deque())
        self.lock = threading.Lock()
    
    def _cleanup_expired(self, bucket_key: str):
        """Remove expired timestamps from a bucket."""
        current_time = time.time()
        with self.lock:
            bucket = self.buckets[bucket_key]
            while bucket and bucket[0] < current_time - self.window_size:
                bucket.popleft()
    
    def is_allowed(self, key: str) -> Tuple[bool, float]:
        """
        Check if a request is allowed.
        
        Args:
            key: Unique identifier for the rate limit bucket
            
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        if not RATE_LIMIT_ENABLED:
            return True, 0.0
        
        self._cleanup_expired(key)
        
        with self.lock:
            bucket = self.buckets[key]
            current_time = time.time()
            
            # Check if bucket is full
            if len(bucket) >= self.bucket_size:
                oldest_request = bucket[0]
                retry_after = self.window_size - (current_time - oldest_request)
                return False, max(0, retry_after)
            
            # Add current request
            bucket.append(current_time)
            return True, 0.0
    
    def get_bucket_info(self, key: str) -> Dict[str, Any]:
        """Get information about a rate limit bucket."""
        self._cleanup_expired(key)
        
        with self.lock:
            bucket = self.buckets[key]
            current_time = time.time()
            
            return {
                'current_requests': len(bucket),
                'max_requests': self.bucket_size,
                'window_size': self.window_size,
                'remaining_requests': max(0, self.bucket_size - len(bucket)),
                'reset_time': current_time + self.window_size if bucket else current_time
            }


class CommandRateLimiter:
    """Rate limiter specifically for Discord commands with cooldowns."""
    
    def __init__(self):
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.user_cooldowns: Dict[str, float] = {}
        self.lock = threading.Lock()
    
    def _get_user_command_key(self, user_id: int, command: str) -> str:
        """Generate a key for user-command rate limiting."""
        return f"user:{user_id}:command:{command}"
    
    def _get_user_key(self, user_id: int) -> str:
        """Generate a key for general user rate limiting."""
        return f"user:{user_id}:general"
    
    def is_command_allowed(self, user_id: int, command: str) -> Tuple[bool, float]:
        """
        Check if a user can execute a specific command.
        
        Args:
            user_id: Discord user ID
            command: Command name
            
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        # Check command-specific cooldown
        cooldown = COMMAND_COOLDOWNS.get(command, 3)
        user_command_key = self._get_user_command_key(user_id, command)
        
        # Get or create rate limiter for this command
        if command not in self.rate_limiters:
            with self.lock:
                if command not in self.rate_limiters:
                    self.rate_limiters[command] = RateLimiter(
                        bucket_size=1,  # One request per cooldown period
                        window_size=cooldown
                    )
        
        return self.rate_limiters[command].is_allowed(user_command_key)
    
    def is_user_allowed(self, user_id: int) -> Tuple[bool, float]:
        """
        Check if a user is allowed to make any request (general rate limiting).
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        user_key = self._get_user_key(user_id)
        
        # Get or create general rate limiter
        if 'general' not in self.rate_limiters:
            with self.lock:
                if 'general' not in self.rate_limiters:
                    self.rate_limiters['general'] = RateLimiter(
                        bucket_size=RATE_LIMIT_BUCKET_SIZE,
                        window_size=RATE_LIMIT_WINDOW
                    )
        
        return self.rate_limiters['general'].is_allowed(user_key)
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get rate limiting statistics for a user."""
        stats = {}
        
        # General user stats
        user_key = self._get_user_key(user_id)
        if 'general' in self.rate_limiters:
            stats['general'] = self.rate_limiters['general'].get_bucket_info(user_key)
        
        # Command-specific stats
        stats['commands'] = {}
        for command in COMMAND_COOLDOWNS:
            user_command_key = self._get_user_command_key(user_id, command)
            if command in self.rate_limiters:
                stats['commands'][command] = self.rate_limiters[command].get_bucket_info(user_command_key)
        
        return stats


class SecurityManager:
    """Manages security features including guild and user restrictions."""
    
    def __init__(self):
        self.allowed_guilds = set(int(guild_id) for guild_id in ALLOWED_GUILDS if guild_id.strip())
        self.blocked_users = set(int(user_id) for user_id in BLOCKED_USERS if user_id.strip())
        self.suspicious_activity: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        self.lock = threading.Lock()
    
    def is_guild_allowed(self, guild_id: int) -> bool:
        """Check if a guild is allowed to use the bot."""
        if not self.allowed_guilds:  # Empty set means all guilds allowed
            return True
        return guild_id in self.allowed_guilds
    
    def is_user_blocked(self, user_id: int) -> bool:
        """Check if a user is blocked from using the bot."""
        return user_id in self.blocked_users
    
    def record_suspicious_activity(self, user_id: int, activity_type: str, details: Dict[str, Any]):
        """Record suspicious activity for monitoring."""
        with self.lock:
            activity = {
                'timestamp': datetime.now().isoformat(),
                'type': activity_type,
                'details': details
            }
            self.suspicious_activity[user_id].append(activity)
            
            # Keep only last 10 activities per user
            if len(self.suspicious_activity[user_id]) > 10:
                self.suspicious_activity[user_id] = self.suspicious_activity[user_id][-10:]
    
    def get_suspicious_activity(self, user_id: int) -> List[Dict[str, Any]]:
        """Get suspicious activity for a user."""
        with self.lock:
            return self.suspicious_activity.get(user_id, []).copy()
    
    def block_user(self, user_id: int, reason: str = "Manual block"):
        """Manually block a user."""
        with self.lock:
            self.blocked_users.add(user_id)
            logger.warning(f"User {user_id} manually blocked: {reason}")
    
    def unblock_user(self, user_id: int):
        """Unblock a user."""
        with self.lock:
            self.blocked_users.discard(user_id)
            logger.info(f"User {user_id} unblocked")
    
    def add_allowed_guild(self, guild_id: int):
        """Add a guild to the allowed list."""
        with self.lock:
            self.allowed_guilds.add(guild_id)
            logger.info(f"Guild {guild_id} added to allowed list")
    
    def remove_allowed_guild(self, guild_id: int):
        """Remove a guild from the allowed list."""
        with self.lock:
            self.allowed_guilds.discard(guild_id)
            logger.info(f"Guild {guild_id} removed from allowed list")


class SecurityMiddleware:
    """Middleware for applying security and rate limiting to Discord commands."""
    
    def __init__(self):
        self.rate_limiter = CommandRateLimiter()
        self.security_manager = SecurityManager()
    
    async def check_permissions(self, ctx) -> Tuple[bool, str]:
        """
        Check if a user has permission to use the bot.
        
        Args:
            ctx: Discord command context
            
        Returns:
            Tuple of (has_permission, error_message)
        """
        user_id = ctx.author.id
        guild_id = ctx.guild.id if ctx.guild else None
        
        # Check if user is blocked
        if self.security_manager.is_user_blocked(user_id):
            return False, "You are blocked from using this bot."
        
        # Check if guild is allowed (only for guild messages)
        if guild_id and not self.security_manager.is_guild_allowed(guild_id):
            return False, "This bot is not available in this server."
        
        return True, ""
    
    async def check_rate_limits(self, ctx, command: str) -> Tuple[bool, float]:
        """
        Check rate limits for a command.
        
        Args:
            ctx: Discord command context
            command: Command name
            
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        user_id = ctx.author.id
        
        # Check general user rate limit
        general_allowed, general_retry = self.rate_limiter.is_user_allowed(user_id)
        if not general_allowed:
            return False, general_retry
        
        # Check command-specific rate limit
        command_allowed, command_retry = self.rate_limiter.is_command_allowed(user_id, command)
        if not command_allowed:
            return False, command_retry
        
        return True, 0.0
    
    def record_command_usage(self, ctx, command: str, success: bool):
        """Record command usage for monitoring."""
        user_id = ctx.author.id
        
        if not success:
            self.security_manager.record_suspicious_activity(
                user_id,
                'command_failure',
                {
                    'command': command,
                    'guild_id': ctx.guild.id if ctx.guild else None,
                    'channel_id': ctx.channel.id
                }
            )
    
    def get_user_security_info(self, user_id: int) -> Dict[str, Any]:
        """Get security information for a user."""
        return {
            'blocked': self.security_manager.is_user_blocked(user_id),
            'rate_limit_stats': self.rate_limiter.get_user_stats(user_id),
            'suspicious_activity': self.security_manager.get_suspicious_activity(user_id)
        }


# Global instances
security_middleware = SecurityMiddleware()