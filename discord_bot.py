#!/usr/bin/env python3
"""
Enhanced Discord Notes Bot application.
Production-ready with security, rate limiting, caching, and performance monitoring.
"""
import asyncio
import os
import signal
import sys
from datetime import datetime
from typing import Optional

import discord
from discord.ext import commands, tasks
from discord import Intents, Activity, ActivityType

from config import BOT_TOKEN, get_config
from logger import get_logger, get_performance_stats, get_error_stats
from database import db
from rate_limiter import security_middleware
from discord_reminder_scheduler import scheduler
from discord_handlers import setup_commands, setup_error_handlers, setup_events

# Set up logging
logger = get_logger(__name__)

# Bot configuration
intents = Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

# Create bot instance with command prefix
bot = commands.Bot(
    command_prefix='!',
    intents=intents,
    help_command=None,
    case_insensitive=True
)

# Bot state tracking
bot.start_time = None
bot.config = get_config()


class BotHealthMonitor:
    """Monitors bot health and performance."""
    
    def __init__(self, bot):
        self.bot = bot
        self.last_heartbeat = None
        self.heartbeat_latency_history = []
        self.command_usage = {}
        self.error_counts = {}
    
    def record_heartbeat(self, latency: float):
        """Record heartbeat latency."""
        self.last_heartbeat = datetime.now()
        self.heartbeat_latency_history.append(latency)
        
        # Keep only last 100 measurements
        if len(self.heartbeat_latency_history) > 100:
            self.heartbeat_latency_history = self.heartbeat_latency_history[-100:]
    
    def record_command(self, command_name: str):
        """Record command usage."""
        self.command_usage[command_name] = self.command_usage.get(command_name, 0) + 1
    
    def record_error(self, error_type: str):
        """Record error occurrence."""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
    
    def get_health_status(self) -> dict:
        """Get current bot health status."""
        return {
            'uptime': str(datetime.now() - self.bot.start_time) if self.bot.start_time else 'Unknown',
            'latency': self.bot.latency * 1000 if self.bot.latency else 0,
            'guild_count': len(self.bot.guilds),
            'user_count': len(self.bot.users),
            'command_usage': self.command_usage.copy(),
            'error_counts': self.error_counts.copy(),
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'avg_latency': sum(self.heartbeat_latency_history) / len(self.heartbeat_latency_history) if self.heartbeat_latency_history else 0
        }


# Initialize health monitor
health_monitor = BotHealthMonitor(bot)


@bot.event
async def on_ready():
    """Called when the bot is ready."""
    bot.start_time = datetime.now()
    
    logger.info(f'Discord bot logged in as {bot.user.name} ({bot.user.id})')
    logger.info(f'Connected to {len(bot.guilds)} guilds')
    logger.info(f'Serving {len(bot.users)} users')
    
    # Set bot status
    activity = Activity(type=ActivityType.playing, name="!help for commands")
    await bot.change_presence(activity=activity)
    
    # Set up reminder scheduler with Discord bot
    scheduler.set_discord_bot(bot)
    scheduler.start()
    logger.info("Reminder scheduler started")
    
    # Start health monitoring tasks
    health_check.start()
    cache_cleanup.start()
    
    logger.info("Discord bot is ready and monitoring!")


@bot.event
async def on_command(ctx):
    """Log all command usage and apply security checks."""
    user_id = ctx.author.id
    command_name = ctx.command.name if ctx.command else 'unknown'
    
    # Record command usage
    health_monitor.record_command(command_name)
    
    # Check permissions
    has_permission, error_msg = await security_middleware.check_permissions(ctx)
    if not has_permission:
        await ctx.send(f"❌ {error_msg}")
        security_middleware.record_command_usage(ctx, command_name, False)
        return
    
    # Check rate limits
    rate_allowed, retry_after = await security_middleware.check_rate_limits(ctx, command_name)
    if not rate_allowed:
        await ctx.send(f"⏰ Rate limit exceeded. Try again in {retry_after:.1f} seconds.")
        security_middleware.record_command_usage(ctx, command_name, False)
        return
    
    logger.info(f"Command '{command_name}' used by {user_id} in {ctx.guild.id if ctx.guild else 'DM'}")


@bot.event
async def on_command_error(ctx, error):
    """Enhanced global error handler for commands."""
    user_id = ctx.author.id
    command_name = ctx.command.name if ctx.command else 'unknown'
    
    # Record error
    error_type = type(error).__name__
    health_monitor.record_error(error_type)
    security_middleware.record_command_usage(ctx, command_name, False)
    
    # Handle specific error types
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Command not found. Use `!help` to see available commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param.name}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid argument provided.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏰ Command is on cooldown. Try again in {error.retry_after:.1f} seconds.")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("❌ This command cannot be used in private messages.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    else:
        logger.error(f"Unhandled command error: {error}", exc_info=True)
        await ctx.send("❌ An unexpected error occurred. Please try again later.")


@bot.event
async def on_message(message):
    """Handle incoming messages with security checks."""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Check if user is blocked
    if security_middleware.security_manager.is_user_blocked(message.author.id):
        return  # Silently ignore blocked users
    
    # Process commands
    await bot.process_commands(message)


@tasks.loop(minutes=5)
async def health_check():
    """Periodic health check and monitoring."""
    try:
        # Record heartbeat latency
        if bot.latency:
            health_monitor.record_heartbeat(bot.latency)
        
        # Log health status
        health_status = health_monitor.get_health_status()
        logger.info(f"Bot health check - Latency: {health_status['latency']:.2f}ms, "
                   f"Guilds: {health_status['guild_count']}, Users: {health_status['user_count']}")
        
        # Check for high error rates
        if health_status['error_counts']:
            total_errors = sum(health_status['error_counts'].values())
            if total_errors > 10:  # Threshold for error alerting
                logger.warning(f"High error rate detected: {total_errors} errors in last 5 minutes")
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")


@tasks.loop(hours=1)
async def cache_cleanup():
    """Periodic cache cleanup and maintenance."""
    try:
        # Clean up database cache
        if db.cache:
            db.cache.cleanup_expired()
        
        # Clean up old reminders
        db.cleanup_old_reminders(days=30)
        
        logger.debug("Cache cleanup completed")
        
    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")


async def graceful_shutdown(signal_received=None):
    """Gracefully shutdown the bot."""
    logger.info("Shutdown signal received, starting graceful shutdown...")
    
    # Stop background tasks
    health_check.cancel()
    cache_cleanup.cancel()
    
    # Stop reminder scheduler
    logger.info("Stopping reminder scheduler...")
    scheduler.stop()
    
    # Close database connections
    logger.info("Closing database connections...")
    db.close()
    
    # Close bot
    logger.info("Closing bot connection...")
    await bot.close()
    
    logger.info("Bot shutdown completed.")


def setup_signal_handlers():
    """Set up signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        asyncio.create_task(graceful_shutdown(signum))
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def setup_bot():
    """Set up the bot with all commands and handlers."""
    # Setup commands
    setup_commands(bot)
    
    # Setup error handlers
    setup_error_handlers(bot)
    
    # Setup event handlers
    setup_events(bot)
    
    # Add custom commands for monitoring
    @bot.command(name='status')
    async def status_command(ctx):
        """Show bot status and health information."""
        user_id = ctx.author.id
        
        # Check if user has permission to view status
        has_permission, error_msg = await security_middleware.check_permissions(ctx)
        if not has_permission:
            await ctx.send(f"❌ {error_msg}")
            return
        
        try:
            health_status = health_monitor.get_health_status()
            performance_stats = get_performance_stats()
            error_stats = get_error_stats()
            
            embed = discord.Embed(
                title="🤖 Bot Status",
                color=discord.Color.green()
            )
            
            # Bot information
            embed.add_field(
                name="📊 General Info",
                value=f"**Uptime:** {health_status['uptime']}\n"
                      f"**Latency:** {health_status['latency']:.2f}ms\n"
                      f"**Guilds:** {health_status['guild_count']}\n"
                      f"**Users:** {health_status['user_count']}",
                inline=True
            )
            
            # Performance information
            if performance_stats:
                recent_ops = list(performance_stats.items())[:3]
                perf_text = "\n".join([
                    f"**{op}:** {stats['recent_avg']:.3f}s avg"
                    for op, stats in recent_ops
                ])
                embed.add_field(
                    name="⚡ Performance",
                    value=perf_text or "No data",
                    inline=True
                )
            
            # Error information
            if error_stats['error_counts']:
                error_text = "\n".join([
                    f"**{error_type}:** {count}"
                    for error_type, count in list(error_stats['error_counts'].items())[:3]
                ])
                embed.add_field(
                    name="⚠️ Recent Errors",
                    value=error_text,
                    inline=True
                )
            
            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await ctx.send("❌ Error retrieving bot status.")


async def main():
    """Main function to run the bot."""
    logger.info("Starting Enhanced Discord Notes Bot...")
    
    # Set up signal handlers
    setup_signal_handlers()
    
    # Set up the bot
    setup_bot()
    
    # Start the bot
    logger.info("Bot is starting...")
    
    try:
        await bot.start(BOT_TOKEN)
    except KeyboardInterrupt:
        logger.info("Received stop signal, shutting down...")
    except Exception as e:
        logger.error(f"Bot startup failed: {e}")
        sys.exit(1)
    finally:
        await graceful_shutdown()


if __name__ == "__main__":
    asyncio.run(main())