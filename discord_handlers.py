"""
Discord command handlers for the Notes Bot.
Contains all the command handlers converted from Telegram to Discord.
"""
import logging
import asyncio
from typing import Optional
from datetime import datetime, timedelta
from discord.ext import commands
from discord import Embed, Color
from discord.ext.commands import cooldown, BucketType

from database import NotesDatabase
from note_categorizer import categorize_note_with_keywords
from config import VALID_CATEGORIES, MAX_PREVIEW_LENGTH, NOTES_PER_PAGE
from logger import get_logger
from discord_reminder_scheduler import scheduler

# Set up logging
logger = get_logger(__name__)

# Initialize database
db = NotesDatabase()


def setup_commands(bot):
    """Set up all bot commands."""
    
    @bot.command(name='start')
    async def start_command(ctx):
        """Handle the !start command."""
        user_id = ctx.author.id
        logger.info(f"User {user_id} started the bot")
        
        embed = Embed(
            title="🎉 Welcome to the Notes Bot!",
            description="I can help you organize your thoughts with automatic categorization.\n\nUse `!help` to see all available commands.",
            color=Color.green()
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        
        await ctx.send(embed=embed)

    @bot.command(name='help')
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
            name="🔧 Other commands",
            value="`!help` - Show this help message\n`!start` - Welcome message\n`!debug` - Bot status and debug info",
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
    @cooldown(1, 5, BucketType.user)  # 1 use per 5 seconds per user
    async def add_note_command(ctx, *, note_text: str):
        """Handle the !add command."""
        user_id = ctx.author.id
        
        # Validate note text
        if len(note_text.strip()) == 0:
            embed = Embed(
                title="❌ Error",
                description="Note text cannot be empty.",
                color=Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        if len(note_text) > 1000:
            embed = Embed(
                title="❌ Error",
                description="Note text is too long. Please keep it under 1000 characters.",
                color=Color.red()
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
                embed = Embed(
                    title="✅ Note Added Successfully!",
                    color=Color.green()
                )
                embed.add_field(name="ID", value=str(note_id), inline=True)
                embed.add_field(name="Category", value=category, inline=True)
                embed.add_field(
                    name="Text", 
                    value=note_text[:100] + ('...' if len(note_text) > 100 else ''),
                    inline=False
                )
                embed.set_footer(text=f"Added by {ctx.author.display_name}")
                
                await ctx.send(embed=embed)
                logger.info(f"Note {note_id} added successfully for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error adding note for user {user_id}: {e}")
            embed = Embed(
                title="❌ Error",
                description="Sorry, there was an error adding your note. Please try again.",
                color=Color.red()
            )
            await ctx.send(embed=embed)

    @bot.command(name='list')
    @cooldown(1, 3, BucketType.user)  # 1 use per 3 seconds per user
    async def list_notes_command(ctx, category_filter: Optional[str] = None):
        """Handle the !list command with pagination support."""
        user_id = ctx.author.id
        
        # Validate category if provided
        if category_filter:
            category_filter = category_filter.lower()
            if category_filter not in VALID_CATEGORIES:
                valid_categories = ', '.join(VALID_CATEGORIES)
                embed = Embed(
                    title="❌ Invalid Category",
                    description=f"Valid categories are: {valid_categories}",
                    color=Color.red()
                )
                await ctx.send(embed=embed)
                return
        
        try:
            logger.info(f"User {user_id} listing notes (category: {category_filter or 'all'})")
            
            # Get notes from database with pagination
            notes, total_count = db.get_notes(user_id, category_filter, page=1, per_page=NOTES_PER_PAGE)
            total_pages = (total_count + NOTES_PER_PAGE - 1) // NOTES_PER_PAGE
            
            if not notes:
                if category_filter:
                    description = f"📝 No notes found in category '{category_filter}'."
                else:
                    description = "📝 You don't have any notes yet.\n\nUse `!add <note text>` to create your first note!"
                
                embed = Embed(
                    title="📝 Notes",
                    description=description,
                    color=Color.blue()
                )
                await ctx.send(embed=embed)
                return
            
            # Build the notes list embed
            if category_filter:
                title = f"📝 Your notes in category '{category_filter}' (Page 1/{total_pages})"
            else:
                title = f"📝 Your notes (Page 1/{total_pages}, {total_count} total)"
            
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
                embed.add_field(
                    name="📄 Navigation",
                    value=f"Page 1 of {total_pages}\nUse `!list <category> <page>` for pagination",
                    inline=False
                )
            
            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing notes for user {user_id}: {e}")
            embed = Embed(
                title="❌ Error",
                description="Sorry, there was an error listing your notes. Please try again.",
                color=Color.red()
            )
            await ctx.send(embed=embed)

    @bot.command(name='delete')
    @cooldown(1, 3, BucketType.user)  # 1 use per 3 seconds per user
    async def delete_note_command(ctx, note_id: int):
        """Handle the !delete command."""
        user_id = ctx.author.id
        
        try:
            logger.info(f"User {user_id} attempting to delete note {note_id}")
            
            # Check if note exists and belongs to user
            note = db.get_note_by_id(note_id, user_id)
            if not note:
                embed = Embed(
                    title="❌ Note Not Found",
                    description="Note not found or you don't have permission to delete it.",
                    color=Color.red()
                )
                await ctx.send(embed=embed)
                return
            
            # Delete the note
            db.delete_note(note_id)
            
            embed = Embed(
                title="✅ Note Deleted",
                description=f"Note ID {note_id} has been deleted successfully.",
                color=Color.green()
            )
            embed.set_footer(text=f"Deleted by {ctx.author.display_name}")
            
            await ctx.send(embed=embed)
            logger.info(f"Note {note_id} deleted successfully for user {user_id}")
            
        except ValueError:
            embed = Embed(
                title="❌ Invalid Note ID",
                description="Please provide a valid note ID (number).",
                color=Color.red()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error deleting note {note_id} for user {user_id}: {e}")
            embed = Embed(
                title="❌ Error",
                description="Sorry, there was an error deleting your note. Please try again.",
                color=Color.red()
            )
            await ctx.send(embed=embed)

    @bot.command(name='search')
    @cooldown(1, 3, BucketType.user)  # 1 use per 3 seconds per user
    async def search_notes_command(ctx, *, keyword: str):
        """Handle the !search command."""
        user_id = ctx.author.id
        
        if len(keyword.strip()) == 0:
            embed = Embed(
                title="❌ Error",
                description="Please provide a search keyword.",
                color=Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        try:
            logger.info(f"User {user_id} searching for keyword: {keyword}")
            
            # Search notes in database
            notes = db.search_notes(user_id, keyword)
            
            if not notes:
                embed = Embed(
                    title="🔍 Search Results",
                    description=f"No notes found containing '{keyword}'.",
                    color=Color.blue()
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
            embed = Embed(
                title="❌ Error",
                description="Sorry, there was an error searching your notes. Please try again.",
                color=Color.red()
            )
            await ctx.send(embed=embed)

    @bot.command(name='remind')
    @cooldown(1, 5, BucketType.user)  # 1 use per 5 seconds per user
    async def remind_command(ctx, note_id: int, *, time_string: str):
        """Handle the !remind command."""
        user_id = ctx.author.id
        
        try:
            logger.info(f"User {user_id} setting reminder for note {note_id} at {time_string}")
            
            # Check if note exists and belongs to user
            note = db.get_note_by_id(note_id, user_id)
            if not note:
                embed = Embed(
                    title="❌ Note Not Found",
                    description="Note not found or you don't have permission to set a reminder for it.",
                    color=Color.red()
                )
                await ctx.send(embed=embed)
                return
            
            # Parse time string and schedule reminder
            reminder_time = scheduler.parse_time_string(time_string)
            if not reminder_time:
                embed = Embed(
                    title="❌ Invalid Time Format",
                    description="Please use formats like: 'in 30 minutes', '2:30pm', '14:30', '2024-01-15'",
                    color=Color.red()
                )
                await ctx.send(embed=embed)
                return
            
            # Schedule the reminder
            job_id = scheduler.schedule_reminder(user_id, note_id, reminder_time, ctx.channel.id)
            
            embed = Embed(
                title="⏰ Reminder Set",
                description=f"Reminder set for note ID {note_id} at {reminder_time.strftime('%Y-%m-%d %H:%M:%S')}",
                color=Color.green()
            )
            embed.set_footer(text=f"Set by {ctx.author.display_name}")
            
            await ctx.send(embed=embed)
            logger.info(f"Reminder scheduled for note {note_id} at {reminder_time}")
            
        except ValueError:
            embed = Embed(
                title="❌ Invalid Note ID",
                description="Please provide a valid note ID (number).",
                color=Color.red()
            )
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error setting reminder for user {user_id}: {e}")
            embed = Embed(
                title="❌ Error",
                description="Sorry, there was an error setting your reminder. Please try again.",
                color=Color.red()
            )
            await ctx.send(embed=embed)

    @bot.command(name='reminders')
    @cooldown(1, 3, BucketType.user)  # 1 use per 3 seconds per user
    async def reminders_command(ctx):
        """Handle the !reminders command."""
        user_id = ctx.author.id
        
        try:
            logger.info(f"User {user_id} listing reminders")
            
            # Get user's reminders
            reminders = scheduler.get_user_reminders(user_id)
            
            if not reminders:
                embed = Embed(
                    title="⏰ Your Reminders",
                    description="You don't have any scheduled reminders.",
                    color=Color.blue()
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
            embed = Embed(
                title="❌ Error",
                description="Sorry, there was an error listing your reminders. Please try again.",
                color=Color.red()
            )
            await ctx.send(embed=embed)

    @bot.command(name='debug')
    @cooldown(1, 10, BucketType.user)  # 1 use per 10 seconds per user
    async def debug_command(ctx):
        """Handle the !debug command."""
        user_id = ctx.author.id
        logger.info(f"User {user_id} requested debug info")
        
        try:
            # Get bot uptime
            uptime = datetime.now() - bot.start_time if hasattr(bot, 'start_time') else timedelta(0)
            
            # Get recent error logs (last 5 errors)
            recent_errors = logger.get_recent_errors(5) if hasattr(logger, 'get_recent_errors') else []
            
            embed = Embed(
                title="🔧 Bot Debug Information",
                color=Color.gold()
            )
            
            embed.add_field(
                name="🤖 Bot Status",
                value=f"**Name:** {bot.user.name}\n**ID:** {bot.user.id}\n**Uptime:** {str(uptime).split('.')[0]}",
                inline=True
            )
            
            embed.add_field(
                name="📊 Statistics",
                value=f"**Servers:** {len(bot.guilds)}\n**Users:** {len(bot.users)}\n**Latency:** {round(bot.latency * 1000)}ms",
                inline=True
            )
            
            embed.add_field(
                name="📝 Database",
                value=f"**File:** {db.db_file}\n**Status:** Connected",
                inline=True
            )
            
            if recent_errors:
                error_text = "\n".join([f"• {error}" for error in recent_errors[:3]])
                embed.add_field(
                    name="⚠️ Recent Errors",
                    value=error_text,
                    inline=False
                )
            
            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in debug command: {e}")
            embed = Embed(
                title="❌ Debug Error",
                description="An error occurred while gathering debug information.",
                color=Color.red()
            )
            await ctx.send(embed=embed)


def setup_error_handlers(bot):
    """Set up additional error handlers."""
    pass  # Global error handler is already set up in main bot file


def setup_events(bot):
    """Set up additional event handlers."""
    
    @bot.event
    async def on_command(ctx):
        """Log all command usage."""
        logger.info(f"Command '{ctx.command}' used by {ctx.author.id} in {ctx.guild.id if ctx.guild else 'DM'}")
    
    @bot.event
    async def on_guild_join(guild):
        """Log when bot joins a new server."""
        logger.info(f"Bot joined guild: {guild.name} (ID: {guild.id})")
    
    @bot.event
    async def on_guild_remove(guild):
        """Log when bot leaves a server."""
        logger.info(f"Bot left guild: {guild.name} (ID: {guild.id})")