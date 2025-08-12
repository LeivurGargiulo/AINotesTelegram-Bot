#!/usr/bin/env python3
"""
Main Discord Notes Bot application.
Handles bot initialization, command registration, and startup.
Converted from Telegram bot to Discord using discord.py.
"""
import logging
import asyncio
import os
from datetime import datetime
from discord.ext import commands
from discord import Intents, Activity, ActivityType
from discord.ext.tasks import loop

from config import BOT_TOKEN
from logger import get_logger
from discord_reminder_scheduler import scheduler
from discord_handlers import (
    setup_commands,
    setup_error_handlers,
    setup_events
)

# Set up logging
logger = get_logger(__name__)

# Bot configuration
intents = Intents.default()
intents.message_content = True
intents.members = True

# Create bot instance with command prefix
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)


@bot.event
async def on_ready():
    """Called when the bot is ready."""
    logger.info(f'Discord bot logged in as {bot.user.name} ({bot.user.id})')
    
    # Set bot status
    activity = Activity(type=ActivityType.playing, name="!help for commands")
    await bot.change_presence(activity=activity)
    
    # Set up reminder scheduler with Discord bot
    scheduler.set_discord_bot(bot)
    scheduler.start()
    logger.info("Reminder scheduler started")
    
    logger.info("Discord bot is ready!")


@bot.event
async def on_command_error(ctx, error):
    """Global error handler for commands."""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Command not found. Use `!help` to see available commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param.name}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid argument provided.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏰ Command is on cooldown. Try again in {error.retry_after:.1f} seconds.")
    else:
        logger.error(f"Unhandled command error: {error}", exc_info=True)
        await ctx.send("❌ An unexpected error occurred. Please try again later.")


@bot.event
async def on_message(message):
    """Handle incoming messages."""
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Process commands
    await bot.process_commands(message)


def setup_bot():
    """Set up the bot with all commands and handlers."""
    # Setup commands
    setup_commands(bot)
    
    # Setup error handlers
    setup_error_handlers(bot)
    
    # Setup event handlers
    setup_events(bot)
    
    logger.info("Bot setup completed")


async def main():
    """Main function to run the bot."""
    logger.info("Starting Discord Notes Bot...")
    
    # Set up the bot
    setup_bot()
    
    # Start the bot
    logger.info("Bot is starting...")
    
    try:
        await bot.start(BOT_TOKEN)
    except KeyboardInterrupt:
        logger.info("Received stop signal, shutting down...")
    finally:
        # Clean shutdown
        logger.info("Stopping reminder scheduler...")
        scheduler.stop()
        
        logger.info("Stopping bot...")
        await bot.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())