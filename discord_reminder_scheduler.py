"""
Reminder scheduling functionality for the Discord Notes Bot.
Adapted from Telegram version to work with Discord channels.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone
# Import discord components only if available
try:
    from discord import Embed, Color
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    # Mock classes for testing
    class Embed:
        def __init__(self, **kwargs):
            self.title = kwargs.get('title', '')
            self.description = kwargs.get('description', '')
            self.color = kwargs.get('color', None)
            self.fields = []
        
        def add_field(self, **kwargs):
            self.fields.append(kwargs)
        
        def set_footer(self, **kwargs):
            self.footer = kwargs
    
    class Color:
        orange = None
        blue = None
        green = None
        red = None
        gold = None

from logger import get_logger
from config import REMINDER_TIMEZONE
from database import NotesDatabase

logger = get_logger(__name__)


class DiscordReminderScheduler:
    """Handles scheduling and managing reminders for notes in Discord."""
    
    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = AsyncIOScheduler(timezone=REMINDER_TIMEZONE)
        self.discord_bot = None
        self.db = NotesDatabase()
        self.reminder_callbacks = {}
        
    def set_discord_bot(self, bot):
        """Set the Discord bot instance for sending reminder messages."""
        self.discord_bot = bot
        
    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Discord reminder scheduler started")
            
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Discord reminder scheduler stopped")
            
    def schedule_reminder(self, user_id: int, note_id: int, reminder_time: datetime, 
                         channel_id: int, job_id: Optional[str] = None) -> str:
        """
        Schedule a reminder for a note.
        
        Args:
            user_id: Discord user ID
            note_id: Note ID to remind about
            reminder_time: When to send the reminder
            channel_id: Discord channel ID where to send the reminder
            job_id: Optional custom job ID
            
        Returns:
            Job ID for the scheduled reminder
        """
        if not job_id:
            job_id = f"reminder_{user_id}_{note_id}_{int(reminder_time.timestamp())}"
            
        # Get note text from database
        note = self.db.get_note_by_id(note_id)
        if not note:
            logger.error(f"Note {note_id} not found for reminder scheduling")
            return None
            
        # Store channel ID for this reminder
        self.reminder_callbacks[job_id] = {
            'user_id': user_id,
            'note_id': note_id,
            'channel_id': channel_id,
            'note_text': note['note_text']
        }
            
        # Schedule the reminder
        self.scheduler.add_job(
            func=self._send_reminder,
            trigger=DateTrigger(run_date=reminder_time),
            args=[job_id],
            id=job_id,
            replace_existing=True
        )
        
        # Store reminder in database
        self.db.add_reminder(user_id, note_id, job_id, reminder_time.strftime('%Y-%m-%d %H:%M:%S'))
        
        logger.info(f"Scheduled Discord reminder for user {user_id}, note {note_id} at {reminder_time}")
        return job_id
        
    def remove_reminder(self, job_id: str) -> bool:
        """
        Remove a scheduled reminder.
        
        Args:
            job_id: The job ID to remove
            
        Returns:
            True if removed, False if not found
        """
        try:
            self.scheduler.remove_job(job_id)
            if job_id in self.reminder_callbacks:
                del self.reminder_callbacks[job_id]
            logger.info(f"Removed Discord reminder job {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to remove Discord reminder job {job_id}: {e}")
            return False
            
    def get_user_reminders(self, user_id: int) -> list:
        """
        Get all scheduled reminders for a user.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            List of reminder jobs for the user
        """
        user_jobs = []
        for job in self.scheduler.get_jobs():
            if job.id.startswith(f"reminder_{user_id}_"):
                job_info = {
                    'job_id': job.id,
                    'next_run': job.next_run_time,
                    'note_id': None,
                    'reminder_time': None
                }
                
                # Get additional info from callback storage
                if job.id in self.reminder_callbacks:
                    callback_info = self.reminder_callbacks[job.id]
                    job_info['note_id'] = callback_info['note_id']
                    job_info['reminder_time'] = callback_info.get('reminder_time')
                
                user_jobs.append(job_info)
        return user_jobs
        
    async def _send_reminder(self, job_id: str):
        """
        Send a reminder message to the Discord channel.
        
        Args:
            job_id: The job ID for the reminder
        """
        if not self.discord_bot:
            logger.error("Discord bot instance not set, cannot send reminder")
            return
            
        if job_id not in self.reminder_callbacks:
            logger.error(f"Reminder callback info not found for job {job_id}")
            return
            
        callback_info = self.reminder_callbacks[job_id]
        user_id = callback_info['user_id']
        note_id = callback_info['note_id']
        channel_id = callback_info['channel_id']
        note_text = callback_info['note_text']
        
        try:
            # Get the channel
            channel = self.discord_bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Channel {channel_id} not found for reminder")
                return
                
            # Truncate note text if too long
            preview = note_text[:100] + "..." if len(note_text) > 100 else note_text
            
            # Create reminder embed
            embed = Embed(
                title=f"⏰ Reminder for Note #{note_id}",
                description=f"**Note:** {preview}",
                color=Color.orange()
            )
            embed.add_field(
                name="📝 Actions",
                value="Use `!list` to view all your notes or `!search <keyword>` to find specific notes.",
                inline=False
            )
            embed.set_footer(text=f"Reminder for user {user_id}")
            
            await channel.send(embed=embed)
            
            # Clean up callback info
            if job_id in self.reminder_callbacks:
                del self.reminder_callbacks[job_id]
            
            logger.info(f"Sent Discord reminder to channel {channel_id} for note {note_id}")
            
        except Exception as e:
            logger.error(f"Failed to send Discord reminder for job {job_id}: {e}")
            
    def parse_time_string(self, time_str: str) -> Optional[datetime]:
        """
        Parse reminder time from various formats.
        
        Args:
            time_str: Time string in various formats
            
        Returns:
            Parsed datetime or None if invalid
        """
        time_str = time_str.lower().strip()
        now = datetime.now(timezone(REMINDER_TIMEZONE))
        
        try:
            # Handle relative times
            if time_str.startswith('in '):
                # "in 30 minutes", "in 2 hours", "in 1 day"
                parts = time_str[3:].split()
                if len(parts) >= 2:
                    amount = int(parts[0])
                    unit = parts[1]
                    
                    if unit in ['minute', 'minutes']:
                        return now + timedelta(minutes=amount)
                    elif unit in ['hour', 'hours']:
                        return now + timedelta(hours=amount)
                    elif unit in ['day', 'days']:
                        return now + timedelta(days=amount)
                    elif unit in ['week', 'weeks']:
                        return now + timedelta(weeks=amount)
                        
            # Handle specific times
            elif ':' in time_str:
                # "14:30", "2:30pm"
                if 'am' in time_str or 'pm' in time_str:
                    # 12-hour format
                    time_part = time_str.replace('am', '').replace('pm', '').strip()
                    hour, minute = map(int, time_part.split(':'))
                    
                    if 'pm' in time_str and hour != 12:
                        hour += 12
                    elif 'am' in time_str and hour == 12:
                        hour = 0
                        
                    reminder_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    # If time has passed today, schedule for tomorrow
                    if reminder_time <= now:
                        reminder_time += timedelta(days=1)
                        
                    return reminder_time
                else:
                    # 24-hour format
                    hour, minute = map(int, time_str.split(':'))
                    reminder_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    # If time has passed today, schedule for tomorrow
                    if reminder_time <= now:
                        reminder_time += timedelta(days=1)
                        
                    return reminder_time
                    
            # Handle specific dates
            elif '/' in time_str or '-' in time_str:
                # Try to parse as date
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']:
                    try:
                        date_part = time_str.split()[0]  # Take first part if time included
                        parsed_date = datetime.strptime(date_part, fmt).date()
                        reminder_time = datetime.combine(parsed_date, now.time())
                        return timezone(REMINDER_TIMEZONE).localize(reminder_time)
                    except ValueError:
                        continue
                        
        except Exception as e:
            logger.warning(f"Failed to parse reminder time '{time_str}': {e}")
            
        return None


# Global Discord scheduler instance
scheduler = DiscordReminderScheduler()