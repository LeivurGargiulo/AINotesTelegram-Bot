"""
Enhanced Discord command handlers for the Notes Bot.
Production-ready with security, rate limiting, caching, and performance monitoring.
"""
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import discord
from discord.ext import commands
from discord import Embed, Color

from database import db
from note_categorizer import categorize_note_with_keywords
from config import VALID_CATEGORIES, MAX_PREVIEW_LENGTH, NOTES_PER_PAGE, REMINDER_MAX_PER_USER
from logger import get_logger, log_performance
from discord_reminder_scheduler import scheduler
from rate_limiter import security_middleware

# Set up logging
logger = get_logger(__name__)


def create_error_embed(title: str, description: str, user_name: str = None) -> Embed:
    """Create a standardized error embed."""
    embed = Embed(title=f"❌ {title}", description=description, color=Color.red())
    if user_name:
        embed.set_footer(text=f"Requested by {user_name}")
    return embed


def create_success_embed(title: str, description: str, user_name: str = None) -> Embed:
    """Create a standardized success embed."""
    embed = Embed(title=f"✅ {title}", description=description, color=Color.green())
    if user_name:
        embed.set_footer(text=f"Requested by {user_name}")
    return embed


def create_info_embed(title: str, description: str, user_name: str = None) -> Embed:
    """Create a standardized info embed."""
    embed = Embed(title=f"ℹ️ {title}", description=description, color=Color.blue())
    if user_name:
        embed.set_footer(text=f"Requested by {user_name}")
    return embed


def setup_commands(bot):
    """Set up all bot commands with enhanced error handling and performance monitoring."""
    
    @bot.command(name='start')
    @log_performance("start_command")
    async def start_command(ctx):
        """Handle the !start command."""
        user_id = ctx.author.id
        logger.info(f"User {user_id} started the bot")
        
        embed = create_success_embed(
            "Welcome to the Notes Bot!",
            "I can help you organize your thoughts with automatic categorization.\n\n"
            "**Key Features:**\n"
            "• 📝 Automatic note categorization\n"
            "• 🔍 Smart search functionality\n"
            "• ⏰ Reminder system\n"
            "• 📊 User statistics\n\n"
            "Use `!help` to see all available commands.",
            ctx.author.display_name
        )
        
        await ctx.send(embed=embed)

    @bot.command(name='help')
    @log_performance("help_command")
    async def help_command(ctx):
        """Handle the !help command."""
        user_id = ctx.author.id
        logger.info(f"User {user_id} requested help")
        
        embed = Embed(
            title="📝 Notes Bot Commands",
            description="Here are all available commands:",
            color=Color.blue()
        )
        
        # Add command fields
        embed.add_field(
            name="📝 Add a note",
            value="`!add <note text>` - Add a new note with keyword-based categorization",
            inline=False
        )
        
        embed.add_field(
            name="📋 List notes",
            value="`!list` - Show all your notes (paginated)\n`!list <category>` - Show notes from a specific category\nCategories: task, idea, quote, other",
            inline=False
        )
        
        embed.add_field(
            name="🗑️ Delete a note",
            value="`!delete <note_id>` - Delete a note by its ID",
            inline=False
        )
        
        embed.add_field(
            name="🔍 Search notes",
            value="`!search <keyword>` - Find notes containing a keyword",
            inline=False
        )
        
        embed.add_field(
            name="⏰ Reminders",
            value="`!remind <note_id> <time>` - Set a reminder for a note\n`!reminders` - List your scheduled reminders\nTime formats: 'in 30 minutes', '2:30pm', '14:30', '2024-01-15'",
            inline=False
        )
        
        embed.add_field(
            name="📊 Statistics",
            value="`!stats` - View your note statistics\n`!status` - Bot health and performance info",
            inline=False
        )
        
        embed.add_field(
            name="🔧 Other commands",
            value="`!help` - Show this help message\n`!start` - Welcome message",
            inline=False
        )
        
        embed.add_field(
            name="📖 Examples",
            value="• `!add Buy groceries tomorrow`\n• `!list task`\n• `!delete 5`\n• `!search meeting`\n• `!remind 5 in 2 hours`",
            inline=False
        )
        
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @bot.command(name='add')
    @log_performance("add_note_command")
    async def add_note_command(ctx, *, note_text: str):
        """Handle the !add command with enhanced validation."""
        user_id = ctx.author.id
        
        # Validate note text
        if len(note_text.strip()) == 0:
            embed = create_error_embed(
                "Invalid Note",
                "Note text cannot be empty.",
                ctx.author.display_name
            )
            await ctx.send(embed=embed)
            return
        
        if len(note_text) > 1000:
            embed = create_error_embed(
                "Note Too Long",
                "Note text is too long. Please keep it under 1000 characters.",
                ctx.author.display_name
            )
            await ctx.send(embed=embed)
            return
        
        try:
            logger.info(f"User {user_id} adding note: {note_text[:50]}...")
            
            # Show typing indicator
            async with ctx.typing():
                # Categorize the note using keyword matching
                category = categorize_note_with_keywords(note_text)
                logger.info(f"Note categorized as: {category}")
                
                # Add note to database
                note_id = db.add_note(user_id, note_text, category)
                
                # Create success embed
                embed = create_success_embed(
                    "Note Added Successfully!",
                    f"Your note has been saved and categorized as **{category}**.",
                    ctx.author.display_name
                )
                embed.add_field(name="ID", value=str(note_id), inline=True)
                embed.add_field(name="Category", value=category, inline=True)
                embed.add_field(
                    name="Text", 
                    value=note_text[:100] + ('...' if len(note_text) > 100 else ''),
                    inline=False
                )
                
                await ctx.send(embed=embed)
                logger.info(f"Note {note_id} added successfully for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error adding note for user {user_id}: {e}")
            embed = create_error_embed(
                "Database Error",
                "Sorry, there was an error adding your note. Please try again.",
                ctx.author.display_name
            )
            await ctx.send(embed=embed)

    @bot.command(name='list')
    @log_performance("list_notes_command")
    async def list_notes_command(ctx, category_filter: Optional[str] = None, page: int = 1):
        """Handle the !list command with enhanced pagination."""
        user_id = ctx.author.id
        
        # Validate page number
        if page < 1:
            page = 1
        
        # Validate category if provided
        if category_filter:
            category_filter = category_filter.lower()
            if category_filter not in VALID_CATEGORIES:
                valid_categories = ', '.join(VALID_CATEGORIES)
                embed = create_error_embed(
                    "Invalid Category",
                    f"Valid categories are: {valid_categories}",
                    ctx.author.display_name
                )
                await ctx.send(embed=embed)
                return
        
        try:
            logger.info(f"User {user_id} listing notes (category: {category_filter or 'all'}, page: {page})")
            
            # Get notes from database with pagination
            notes, total_count = db.get_notes(user_id, category_filter, page=page, per_page=NOTES_PER_PAGE)
            total_pages = (total_count + NOTES_PER_PAGE - 1) // NOTES_PER_PAGE
            
            if not notes:
                if category_filter:
                    description = f"📝 No notes found in category '{category_filter}'."
                else:
                    description = "📝 You don't have any notes yet.\n\nUse `!add <note text>` to create your first note!"
                
                embed = create_info_embed("Notes", description, ctx.author.display_name)
                await ctx.send(embed=embed)
                return
            
            # Build the notes list embed
            if category_filter:
                title = f"📝 Your notes in category '{category_filter}' (Page {page}/{total_pages})"
            else:
                title = f"📝 Your notes (Page {page}/{total_pages}, {total_count} total)"
            
            embed = Embed(title=title, color=Color.blue())
            
            for note in notes:
                # Truncate note text for preview
                preview = note['note_text']
                if len(preview) > MAX_PREVIEW_LENGTH:
                    preview = preview[:MAX_PREVIEW_LENGTH] + "..."
                
                embed.add_field(
                    name=f"ID: {note['id']} | {note['category'].upper()}",
                    value=f"**Time:** {note['timestamp']}\n**Text:** {preview}",
                    inline=False
                )
            
            # Add pagination info if needed
            if total_pages > 1:
                pagination_text = f"Page {page} of {total_pages}"
                if page > 1:
                    pagination_text += f" | Use `!list {category_filter or ''} {page-1}` for previous page"
                if page < total_pages:
                    pagination_text += f" | Use `!list {category_filter or ''} {page+1}` for next page"
                
                embed.add_field(
                    name="📄 Navigation",
                    value=pagination_text,
                    inline=False
                )
            
            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing notes for user {user_id}: {e}")
            embed = create_error_embed(
                "Database Error",
                "Sorry, there was an error listing your notes. Please try again.",
                ctx.author.display_name
            )
            await ctx.send(embed=embed)

    @bot.command(name='delete')
    @log_performance("delete_note_command")
    async def delete_note_command(ctx, note_id: int):
        """Handle the !delete command with enhanced validation."""
        user_id = ctx.author.id
        
        try:
            logger.info(f"User {user_id} attempting to delete note {note_id}")
            
            # Check if note exists and belongs to user
            note = db.get_note_by_id(note_id, user_id)
            if not note:
                embed = create_error_embed(
                    "Note Not Found",
                    "Note not found or you don't have permission to delete it.",
                    ctx.author.display_name
                )
                await ctx.send(embed=embed)
                return
            
            # Delete the note
            success = db.delete_note(note_id, user_id)
            
            if success:
                embed = create_success_embed(
                    "Note Deleted",
                    f"Note ID {note_id} has been deleted successfully.",
                    ctx.author.display_name
                )
                await ctx.send(embed=embed)
                logger.info(f"Note {note_id} deleted successfully for user {user_id}")
            else:
                embed = create_error_embed(
                    "Delete Failed",
                    "Failed to delete the note. Please try again.",
                    ctx.author.display_name
                )
                await ctx.send(embed=embed)
            
        except ValueError:
            embed = create_error_embed(
                "Invalid Note ID",
                "Please provide a valid note ID (number).",
                ctx.author.display_name
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error deleting note {note_id} for user {user_id}: {e}")
            embed = create_error_embed(
                "Database Error",
                "Sorry, there was an error deleting your note. Please try again.",
                ctx.author.display_name
            )
            await ctx.send(embed=embed)

    @bot.command(name='search')
    @log_performance("search_notes_command")
    async def search_notes_command(ctx, *, keyword: str):
        """Handle the !search command with enhanced search."""
        user_id = ctx.author.id
        
        if len(keyword.strip()) == 0:
            embed = create_error_embed(
                "Invalid Search",
                "Please provide a search keyword.",
                ctx.author.display_name
            )
            await ctx.send(embed=embed)
            return
        
        try:
            logger.info(f"User {user_id} searching for keyword: {keyword}")
            
            # Search notes in database
            notes, total_count = db.search_notes(user_id, keyword)
            
            if not notes:
                embed = create_info_embed(
                    "Search Results",
                    f"No notes found containing '{keyword}'.",
                    ctx.author.display_name
                )
                await ctx.send(embed=embed)
                return
            
            # Build search results embed
            embed = Embed(
                title=f"🔍 Search Results for '{keyword}'",
                description=f"Found {len(notes)} matching notes:",
                color=Color.blue()
            )
            
            for note in notes:
                # Truncate note text for preview
                preview = note['note_text']
                if len(preview) > MAX_PREVIEW_LENGTH:
                    preview = preview[:MAX_PREVIEW_LENGTH] + "..."
                
                embed.add_field(
                    name=f"ID: {note['id']} | {note['category'].upper()}",
                    value=f"**Time:** {note['timestamp']}\n**Text:** {preview}",
                    inline=False
                )
            
            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error searching notes for user {user_id}: {e}")
            embed = create_error_embed(
                "Search Error",
                "Sorry, there was an error searching your notes. Please try again.",
                ctx.author.display_name
            )
            await ctx.send(embed=embed)

    @bot.command(name='remind')
    @log_performance("remind_command")
    async def remind_command(ctx, note_id: int, *, time_string: str):
        """Handle the !remind command with enhanced validation."""
        user_id = ctx.author.id
        
        try:
            logger.info(f"User {user_id} setting reminder for note {note_id} at {time_string}")
            
            # Check if note exists and belongs to user
            note = db.get_note_by_id(note_id, user_id)
            if not note:
                embed = create_error_embed(
                    "Note Not Found",
                    "Note not found or you don't have permission to set a reminder for it.",
                    ctx.author.display_name
                )
                await ctx.send(embed=embed)
                return
            
            # Check reminder limit
            user_reminders = scheduler.get_user_reminders(user_id)
            if len(user_reminders) >= REMINDER_MAX_PER_USER:
                embed = create_error_embed(
                    "Reminder Limit Reached",
                    f"You can only have {REMINDER_MAX_PER_USER} active reminders. Please delete some before adding new ones.",
                    ctx.author.display_name
                )
                await ctx.send(embed=embed)
                return
            
            # Parse time string and schedule reminder
            reminder_time = scheduler.parse_time_string(time_string)
            if not reminder_time:
                embed = create_error_embed(
                    "Invalid Time Format",
                    "Please use formats like: 'in 30 minutes', '2:30pm', '14:30', '2024-01-15'",
                    ctx.author.display_name
                )
                await ctx.send(embed=embed)
                return
            
            # Schedule the reminder
            job_id = scheduler.schedule_reminder(user_id, note_id, reminder_time, ctx.channel.id)
            
            if job_id:
                embed = create_success_embed(
                    "Reminder Set",
                    f"Reminder set for note ID {note_id} at {reminder_time.strftime('%Y-%m-%d %H:%M:%S')}",
                    ctx.author.display_name
                )
                await ctx.send(embed=embed)
                logger.info(f"Reminder scheduled for note {note_id} at {reminder_time}")
            else:
                embed = create_error_embed(
                    "Reminder Failed",
                    "Failed to schedule the reminder. Please try again.",
                    ctx.author.display_name
                )
                await ctx.send(embed=embed)
            
        except ValueError:
            embed = create_error_embed(
                "Invalid Note ID",
                "Please provide a valid note ID (number).",
                ctx.author.display_name
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error setting reminder for user {user_id}: {e}")
            embed = create_error_embed(
                "Reminder Error",
                "Sorry, there was an error setting your reminder. Please try again.",
                ctx.author.display_name
            )
            await ctx.send(embed=embed)

    @bot.command(name='reminders')
    @log_performance("reminders_command")
    async def reminders_command(ctx):
        """Handle the !reminders command."""
        user_id = ctx.author.id
        
        try:
            logger.info(f"User {user_id} listing reminders")
            
            # Get user's reminders
            reminders = scheduler.get_user_reminders(user_id)
            
            if not reminders:
                embed = create_info_embed(
                    "Your Reminders",
                    "You don't have any scheduled reminders.",
                    ctx.author.display_name
                )
                await ctx.send(embed=embed)
                return
            
            # Build reminders list embed
            embed = Embed(
                title="⏰ Your Reminders",
                description=f"You have {len(reminders)} scheduled reminders:",
                color=Color.blue()
            )
            
            for reminder in reminders:
                embed.add_field(
                    name=f"Note ID: {reminder['note_id']}",
                    value=f"**Time:** {reminder['reminder_time']}\n**Job ID:** {reminder['job_id']}",
                    inline=True
                )
            
            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing reminders for user {user_id}: {e}")
            embed = create_error_embed(
                "Reminder Error",
                "Sorry, there was an error listing your reminders. Please try again.",
                ctx.author.display_name
            )
            await ctx.send(embed=embed)

    @bot.command(name='stats')
    @log_performance("stats_command")
    async def stats_command(ctx):
        """Handle the !stats command to show user statistics."""
        user_id = ctx.author.id
        
        try:
            logger.info(f"User {user_id} requesting statistics")
            
            # Get user statistics
            stats = db.get_user_stats(user_id)
            
            embed = Embed(
                title="📊 Your Note Statistics",
                color=Color.blue()
            )
            
            embed.add_field(
                name="📝 Total Notes",
                value=str(stats['total_notes']),
                inline=True
            )
            
            embed.add_field(
                name="📈 Recent Activity",
                value=f"{stats['recent_notes']} notes in last 7 days",
                inline=True
            )
            
            # Add category breakdown
            if stats['category_counts']:
                category_text = "\n".join([
                    f"**{category.title()}:** {count}"
                    for category, count in stats['category_counts'].items()
                ])
                embed.add_field(
                    name="📂 By Category",
                    value=category_text,
                    inline=False
                )
            
            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error getting stats for user {user_id}: {e}")
            embed = create_error_embed(
                "Statistics Error",
                "Sorry, there was an error retrieving your statistics. Please try again.",
                ctx.author.display_name
            )
            await ctx.send(embed=embed)


def setup_error_handlers(bot):
    """Set up additional error handlers."""
    pass  # Global error handler is already set up in main bot file


def setup_events(bot):
    """Set up additional event handlers."""
    
    @bot.event
    async def on_guild_join(guild):
        """Log when bot joins a new server."""
        logger.info(f"Bot joined guild: {guild.name} (ID: {guild.id})")
        
        # Check if guild is allowed
        if not security_middleware.security_manager.is_guild_allowed(guild.id):
            logger.warning(f"Bot joined unauthorized guild: {guild.name} (ID: {guild.id})")
            # You could leave the guild here if needed
            # await guild.leave()
    
    @bot.event
    async def on_guild_remove(guild):
        """Log when bot leaves a server."""
        logger.info(f"Bot left guild: {guild.name} (ID: {guild.id})")
    
    @bot.event
    async def on_command_completion(ctx):
        """Log successful command completion."""
        user_id = ctx.author.id
        command_name = ctx.command.name if ctx.command else 'unknown'
        logger.info(f"Command '{command_name}' completed successfully for user {user_id}")
        
        # Record successful command usage
        security_middleware.record_command_usage(ctx, command_name, True)