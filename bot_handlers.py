"""
Bot command handlers for the Telegram Notes Bot.
Contains all the command handlers and utility functions.
"""
import logging
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import NotesDatabase
from llm_client import categorize_note_with_llm
from config import VALID_CATEGORIES, MAX_PREVIEW_LENGTH

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
db = NotesDatabase()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    welcome_message = (
        "🎉 Welcome to the Notes Bot!\n\n"
        "I can help you organize your thoughts with smart categorization.\n\n"
        "Use /help to see all available commands."
    )
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command."""
    help_text = (
        "📝 **Notes Bot Commands**\n\n"
        "**Add a note:**\n"
        "`/add <note text>` - Add a new note with automatic categorization\n\n"
        "**List notes:**\n"
        "`/list` - Show all your notes\n"
        "`/list <category>` - Show notes from a specific category\n"
        "Categories: task, idea, quote, other\n\n"
        "**Delete a note:**\n"
        "`/delete <note_id>` - Delete a note by its ID\n\n"
        "**Search notes:**\n"
        "`/search <keyword>` - Find notes containing a keyword\n\n"
        "**Other commands:**\n"
        "`/help` - Show this help message\n"
        "`/start` - Welcome message\n\n"
        "**Examples:**\n"
        "• `/add Buy groceries tomorrow`\n"
        "• `/list task`\n"
        "• `/delete 5`\n"
        "• `/search meeting`"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def add_note_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /add command."""
    user_id = update.effective_user.id
    
    # Check if note text is provided
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a note text.\n"
            "Usage: `/add <note text>`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Get the note text (join all arguments)
    note_text = ' '.join(context.args)
    
    # Validate note text
    if len(note_text.strip()) == 0:
        await update.message.reply_text("❌ Note text cannot be empty.")
        return
    
    if len(note_text) > 1000:
        await update.message.reply_text("❌ Note text is too long. Please keep it under 1000 characters.")
        return
    
    try:
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        # Categorize the note using LLM
        category = categorize_note_with_llm(note_text)
        
        # Add note to database
        note_id = db.add_note(user_id, note_text, category)
        
        # Send success message
        success_message = (
            f"✅ **Note added successfully!**\n\n"
            f"**ID:** {note_id}\n"
            f"**Category:** {category}\n"
            f"**Text:** {note_text[:100]}{'...' if len(note_text) > 100 else ''}"
        )
        
        await update.message.reply_text(success_message, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Error adding note: {e}")
        await update.message.reply_text(
            "❌ Sorry, there was an error adding your note. Please try again."
        )


async def list_notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /list command."""
    user_id = update.effective_user.id
    
    # Get category filter if provided
    category_filter = context.args[0].lower() if context.args else None
    
    # Validate category if provided
    if category_filter and category_filter not in VALID_CATEGORIES:
        valid_categories = ', '.join(VALID_CATEGORIES)
        await update.message.reply_text(
            f"❌ Invalid category. Valid categories are: {valid_categories}"
        )
        return
    
    try:
        # Get notes from database
        notes = db.get_notes(user_id, category_filter)
        
        if not notes:
            if category_filter:
                message = f"📝 No notes found in category '{category_filter}'."
            else:
                message = "📝 You don't have any notes yet.\n\nUse `/add <note text>` to create your first note!"
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            return
        
        # Build the notes list message
        if category_filter:
            header = f"📝 **Your notes in category '{category_filter}':**\n\n"
        else:
            header = f"📝 **Your notes ({len(notes)} total):**\n\n"
        
        notes_list = []
        for note in notes:
            # Truncate note text for preview
            preview = note['note_text']
            if len(preview) > MAX_PREVIEW_LENGTH:
                preview = preview[:MAX_PREVIEW_LENGTH] + "..."
            
            note_entry = (
                f"**ID:** {note['id']} | **{note['category'].upper()}**\n"
                f"**Time:** {note['timestamp']}\n"
                f"**Text:** {preview}\n"
            )
            notes_list.append(note_entry)
        
        message = header + "\n".join(notes_list)
        
        # Split message if too long
        if len(message) > 4096:
            # Send in chunks
            chunks = [message[i:i+4096] for i in range(0, len(message), 4096)]
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
                else:
                    await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            
    except Exception as e:
        logger.error(f"Error listing notes: {e}")
        await update.message.reply_text(
            "❌ Sorry, there was an error retrieving your notes. Please try again."
        )


async def delete_note_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /delete command."""
    user_id = update.effective_user.id
    
    # Check if note ID is provided
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a note ID.\n"
            "Usage: `/delete <note_id>`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Validate note ID
    try:
        note_id = int(context.args[0])
        if note_id <= 0:
            raise ValueError("Note ID must be positive")
    except ValueError:
        await update.message.reply_text("❌ Invalid note ID. Please provide a valid number.")
        return
    
    try:
        # Try to delete the note
        success = db.delete_note(user_id, note_id)
        
        if success:
            await update.message.reply_text(f"✅ Note with ID {note_id} has been deleted.")
        else:
            await update.message.reply_text(
                f"❌ Note with ID {note_id} not found or you don't have permission to delete it."
            )
            
    except Exception as e:
        logger.error(f"Error deleting note: {e}")
        await update.message.reply_text(
            "❌ Sorry, there was an error deleting the note. Please try again."
        )


async def search_notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /search command."""
    user_id = update.effective_user.id
    
    # Check if keyword is provided
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a search keyword.\n"
            "Usage: `/search <keyword>`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Get the search keyword
    keyword = ' '.join(context.args)
    
    if len(keyword.strip()) == 0:
        await update.message.reply_text("❌ Search keyword cannot be empty.")
        return
    
    try:
        # Search notes in database
        notes = db.search_notes(user_id, keyword)
        
        if not notes:
            await update.message.reply_text(
                f"🔍 No notes found containing '{keyword}'."
            )
            return
        
        # Build the search results message
        header = f"🔍 **Search results for '{keyword}' ({len(notes)} found):**\n\n"
        
        notes_list = []
        for note in notes:
            # Truncate note text for preview
            preview = note['note_text']
            if len(preview) > MAX_PREVIEW_LENGTH:
                preview = preview[:MAX_PREVIEW_LENGTH] + "..."
            
            note_entry = (
                f"**ID:** {note['id']} | **{note['category'].upper()}**\n"
                f"**Time:** {note['timestamp']}\n"
                f"**Text:** {preview}\n"
            )
            notes_list.append(note_entry)
        
        message = header + "\n".join(notes_list)
        
        # Split message if too long
        if len(message) > 4096:
            # Send in chunks
            chunks = [message[i:i+4096] for i in range(0, len(message), 4096)]
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
                else:
                    await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            
    except Exception as e:
        logger.error(f"Error searching notes: {e}")
        await update.message.reply_text(
            "❌ Sorry, there was an error searching your notes. Please try again."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in the bot."""
    logger.error(f"Exception while handling an update: {context.error}")
    
    # Send a friendly error message to the user
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Sorry, something went wrong. Please try again later."
        )