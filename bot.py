#!/usr/bin/env python3
"""
Main Telegram Notes Bot application.
Handles bot initialization, command registration, and startup.
"""
import logging
import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from config import BOT_TOKEN
from logger import get_logger
from reminder_scheduler import scheduler
from bot_handlers import (
    start_command,
    help_command,
    add_note_command,
    list_notes_command,
    delete_note_command,
    search_notes_command,
    remind_command,
    reminders_command,
    handle_pagination_callback,
    error_handler
)

# Set up logging
logger = get_logger(__name__)


def setup_bot():
    """Set up the bot application with all handlers."""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("add", add_note_command))
    application.add_handler(CommandHandler("list", list_notes_command))
    application.add_handler(CommandHandler("delete", delete_note_command))
    application.add_handler(CommandHandler("search", search_notes_command))
    application.add_handler(CommandHandler("remind", remind_command))
    application.add_handler(CommandHandler("reminders", reminders_command))
    
    # Add callback query handler for pagination
    application.add_handler(CallbackQueryHandler(handle_pagination_callback))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    return application


async def main():
    """Main function to run the bot."""
    logger.info("Starting Telegram Notes Bot...")
    
    # Set up the bot
    application = setup_bot()
    
    # Set up reminder scheduler
    scheduler.set_bot(application.bot)
    scheduler.start()
    logger.info("Reminder scheduler started")
    
    # Start the bot
    logger.info("Bot is starting...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    logger.info("Bot is running! Press Ctrl+C to stop.")
    
    try:
        # Keep the bot running
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Received stop signal, shutting down...")
    finally:
        # Clean shutdown
        logger.info("Stopping reminder scheduler...")
        scheduler.stop()
        
        logger.info("Stopping bot...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())