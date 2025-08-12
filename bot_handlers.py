"""
Bot command handlers for the Telegram Notes Bot.
Contains all the command handlers and utility functions.
"""
import logging
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from database import NotesDatabase
from llm_client import categorize_note_with_llm
from config import VALID_CATEGORIES, MAX_PREVIEW_LENGTH, NOTES_PER_PAGE
from logger import get_logger
from reminder_scheduler import scheduler

# Set up logging
logger = get_logger(__name__)

# Initialize database
db = NotesDatabase()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} started the bot")
    
    welcome_message = (
        "🎉 Welcome to the Notes Bot!\n\n"
        "I can help you organize your thoughts with smart categorization.\n\n"
        "Use /help to see all available commands."
    )
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /help command."""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} requested help")
    
    help_text = (
        "📝 **Notes Bot Commands**\n\n"
        "**Add a note:**\n"
        "`/add <note text>` - Add a new note with automatic categorization\n\n"
        "**List notes:**\n"
        "`/list` - Show all your notes (paginated)\n"
        "`/list <category>` - Show notes from a specific category\n"
        "Categories: task, idea, quote, other\n\n"
        "**Delete a note:**\n"
        "`/delete <note_id>` - Delete a note by its ID\n\n"
        "**Search notes:**\n"
        "`/search <keyword>` - Find notes containing a keyword\n\n"
        "**Reminders:**\n"
        "`/remind <note_id> <time>` - Set a reminder for a note\n"
        "`/reminders` - List your scheduled reminders\n"
        "Time formats: 'in 30 minutes', '2:30pm', '14:30', '2024-01-15'\n\n"
        "**Other commands:**\n"
        "`/help` - Show this help message\n"
        "`/start` - Welcome message\n\n"
        "**Examples:**\n"
        "• `/add Buy groceries tomorrow`\n"
        "• `/list task`\n"
        "• `/delete 5`\n"
        "• `/search meeting`\n"
        "• `/remind 5 in 2 hours`"
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
        logger.info(f"User {user_id} adding note: {note_text[:50]}...")
        
        # Send typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        # Categorize the note using LLM
        category = categorize_note_with_llm(note_text)
        logger.info(f"Note categorized as: {category}")
        
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
        logger.info(f"Note {note_id} added successfully for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error adding note for user {user_id}: {e}")
        await update.message.reply_text(
            "❌ Sorry, there was an error adding your note. Please try again."
        )


def create_pagination_keyboard(page: int, total_pages: int, category: Optional[str] = None, 
                             search_keyword: Optional[str] = None) -> InlineKeyboardMarkup:
    """Create pagination keyboard for navigation."""
    keyboard = []
    
    # Navigation buttons
    nav_buttons = []
    
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", 
                                               callback_data=f"page_{page-1}_{category or 'all'}_{search_keyword or ''}"))
    
    nav_buttons.append(InlineKeyboardButton(f"📄 {page}/{total_pages}", 
                                           callback_data="current_page"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", 
                                               callback_data=f"page_{page+1}_{category or 'all'}_{search_keyword or ''}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    return InlineKeyboardMarkup(keyboard)


async def list_notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /list command with pagination support."""
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
        logger.info(f"User {user_id} listing notes (category: {category_filter or 'all'})")
        
        # Get notes from database with pagination
        notes, total_count = db.get_notes(user_id, category_filter, page=1, per_page=NOTES_PER_PAGE)
        total_pages = (total_count + NOTES_PER_PAGE - 1) // NOTES_PER_PAGE
        
        if not notes:
            if category_filter:
                message = f"📝 No notes found in category '{category_filter}'."
            else:
                message = "📝 You don't have any notes yet.\n\nUse `/add <note text>` to create your first note!"
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            return
        
        # Build the notes list message
        if category_filter:
            header = f"📝 **Your notes in category '{category_filter}' (Page 1/{total_pages}):**\n\n"
        else:
            header = f"📝 **Your notes (Page 1/{total_pages}, {total_count} total):**\n\n"
        
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
        
        # Create pagination keyboard if needed
        keyboard = None
        if total_pages > 1:
            keyboard = create_pagination_keyboard(1, total_pages, category_filter)
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        logger.info(f"Listed {len(notes)} notes for user {user_id} (page 1/{total_pages})")
            
    except Exception as e:
        logger.error(f"Error listing notes for user {user_id}: {e}")
        await update.message.reply_text(
            "❌ Sorry, there was an error retrieving your notes. Please try again."
        )


async def handle_pagination_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pagination callback queries."""
    query = update.callback_query
    user_id = query.from_user.id
    
    if not query.data.startswith("page_"):
        await query.answer()
        return
    
    try:
        # Parse callback data: page_<page>_<category>_<search>
        parts = query.data.split("_")
        if len(parts) < 3:
            await query.answer("Invalid pagination data")
            return
        
        page = int(parts[1])
        category = parts[2] if parts[2] != 'all' else None
        search_keyword = parts[3] if len(parts) > 3 and parts[3] else None
        
        logger.info(f"User {user_id} navigating to page {page} (category: {category}, search: {search_keyword})")
        
        # Get notes for the requested page
        if search_keyword:
            notes, total_count = db.search_notes(user_id, search_keyword, page=page, per_page=NOTES_PER_PAGE)
            header = f"🔍 **Search results for '{search_keyword}' (Page {page}/{total_count // NOTES_PER_PAGE + 1}):**\n\n"
        else:
            notes, total_count = db.get_notes(user_id, category, page=page, per_page=NOTES_PER_PAGE)
            if category:
                header = f"📝 **Your notes in category '{category}' (Page {page}/{total_count // NOTES_PER_PAGE + 1}):**\n\n"
            else:
                header = f"📝 **Your notes (Page {page}/{total_count // NOTES_PER_PAGE + 1}, {total_count} total):**\n\n"
        
        total_pages = (total_count + NOTES_PER_PAGE - 1) // NOTES_PER_PAGE
        
        # Build notes list
        notes_list = []
        for note in notes:
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
        
        # Create pagination keyboard
        keyboard = create_pagination_keyboard(page, total_pages, category, search_keyword)
        
        # Update the message
        await query.edit_message_text(message, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        await query.answer()
        
    except Exception as e:
        logger.error(f"Error handling pagination for user {user_id}: {e}")
        await query.answer("Error loading page")


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
        logger.info(f"User {user_id} attempting to delete note {note_id}")
        
        # Try to delete the note
        success = db.delete_note(user_id, note_id)
        
        if success:
            await update.message.reply_text(f"✅ Note with ID {note_id} has been deleted.")
            logger.info(f"Note {note_id} deleted successfully for user {user_id}")
        else:
            await update.message.reply_text(
                f"❌ Note with ID {note_id} not found or you don't have permission to delete it."
            )
            logger.warning(f"Failed to delete note {note_id} for user {user_id}")
            
    except Exception as e:
        logger.error(f"Error deleting note {note_id} for user {user_id}: {e}")
        await update.message.reply_text(
            "❌ Sorry, there was an error deleting the note. Please try again."
        )


async def search_notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /search command with pagination support."""
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
        logger.info(f"User {user_id} searching for: {keyword}")
        
        # Search notes in database with pagination
        notes, total_count = db.search_notes(user_id, keyword, page=1, per_page=NOTES_PER_PAGE)
        total_pages = (total_count + NOTES_PER_PAGE - 1) // NOTES_PER_PAGE
        
        if not notes:
            await update.message.reply_text(
                f"🔍 No notes found containing '{keyword}'."
            )
            return
        
        # Build the search results message
        header = f"🔍 **Search results for '{keyword}' (Page 1/{total_pages}, {total_count} found):**\n\n"
        
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
        
        # Create pagination keyboard if needed
        keyboard = None
        if total_pages > 1:
            keyboard = create_pagination_keyboard(1, total_pages, search_keyword=keyword)
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        logger.info(f"Search returned {len(notes)} results for user {user_id} (page 1/{total_pages})")
            
    except Exception as e:
        logger.error(f"Error searching notes for user {user_id}: {e}")
        await update.message.reply_text(
            "❌ Sorry, there was an error searching your notes. Please try again."
        )


async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /remind command."""
    user_id = update.effective_user.id
    
    # Check if note ID and time are provided
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Please provide a note ID and reminder time.\n"
            "Usage: `/remind <note_id> <time>`\n\n"
            "**Time formats:**\n"
            "• `in 30 minutes`\n"
            "• `in 2 hours`\n"
            "• `2:30pm`\n"
            "• `14:30`\n"
            "• `2024-01-15`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Parse note ID
    try:
        note_id = int(context.args[0])
        if note_id <= 0:
            raise ValueError("Note ID must be positive")
    except ValueError:
        await update.message.reply_text("❌ Invalid note ID. Please provide a valid number.")
        return
    
    # Get the reminder time string
    time_str = ' '.join(context.args[1:])
    
    try:
        logger.info(f"User {user_id} setting reminder for note {note_id} at {time_str}")
        
        # Get the note to verify it exists and belongs to the user
        note = db.get_note_by_id(user_id, note_id)
        if not note:
            await update.message.reply_text(
                f"❌ Note with ID {note_id} not found or you don't have permission to access it."
            )
            return
        
        # Parse the reminder time
        reminder_time = scheduler.parse_reminder_time(time_str)
        if not reminder_time:
            await update.message.reply_text(
                "❌ Invalid time format. Please use formats like:\n"
                "• `in 30 minutes`\n"
                "• `in 2 hours`\n"
                "• `2:30pm`\n"
                "• `14:30`\n"
                "• `2024-01-15`"
            )
            return
        
        # Schedule the reminder
        job_id = scheduler.add_reminder(user_id, note_id, reminder_time, note['note_text'])
        
        # Add reminder record to database
        db.add_reminder(user_id, note_id, job_id, reminder_time.strftime('%Y-%m-%d %H:%M:%S'))
        
        # Send confirmation message
        time_str_formatted = reminder_time.strftime('%Y-%m-%d %H:%M:%S')
        success_message = (
            f"⏰ **Reminder set successfully!**\n\n"
            f"**Note ID:** {note_id}\n"
            f"**Reminder time:** {time_str_formatted}\n"
            f"**Note preview:** {note['note_text'][:50]}{'...' if len(note['note_text']) > 50 else ''}"
        )
        
        await update.message.reply_text(success_message, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Reminder scheduled for user {user_id}, note {note_id} at {time_str_formatted}")
        
    except Exception as e:
        logger.error(f"Error setting reminder for user {user_id}, note {note_id}: {e}")
        await update.message.reply_text(
            "❌ Sorry, there was an error setting the reminder. Please try again."
        )


async def reminders_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /reminders command."""
    user_id = update.effective_user.id
    
    try:
        logger.info(f"User {user_id} listing reminders")
        
        # Get user's reminders from database
        reminders = db.get_user_reminders(user_id)
        
        if not reminders:
            await update.message.reply_text(
                "⏰ You don't have any scheduled reminders.\n\n"
                "Use `/remind <note_id> <time>` to set a reminder."
            )
            return
        
        # Build reminders list
        header = f"⏰ **Your scheduled reminders ({len(reminders)} total):**\n\n"
        
        reminders_list = []
        for reminder in reminders:
            note_preview = reminder['note_text']
            if len(note_preview) > 50:
                note_preview = note_preview[:50] + "..."
            
            reminder_entry = (
                f"**Note ID:** {reminder['note_id']} | **{reminder['category'].upper()}**\n"
                f"**Reminder time:** {reminder['reminder_time']}\n"
                f"**Note:** {note_preview}\n"
            )
            reminders_list.append(reminder_entry)
        
        message = header + "\n".join(reminders_list)
        
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Listed {len(reminders)} reminders for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error listing reminders for user {user_id}: {e}")
        await update.message.reply_text(
            "❌ Sorry, there was an error retrieving your reminders. Please try again."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in the bot."""
    user_id = update.effective_user.id if update and update.effective_user else "unknown"
    logger.error(f"Exception while handling an update for user {user_id}: {context.error}")
    
    # Send a friendly error message to the user
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Sorry, something went wrong. Please try again later."
        )