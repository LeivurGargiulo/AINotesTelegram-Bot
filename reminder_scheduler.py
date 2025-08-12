"""
Reminder scheduling functionality for the Telegram Notes Bot.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

from logger import get_logger
from config import REMINDER_TIMEZONE

logger = get_logger(__name__)


class ReminderScheduler:
    """Handles scheduling and managing reminders for notes."""
    
    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = AsyncIOScheduler(timezone=REMINDER_TIMEZONE)
        self.bot = None
        self.reminder_callbacks = {}
        
    def set_bot(self, bot):
        """Set the bot instance for sending reminder messages."""
        self.bot = bot
        
    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Reminder scheduler started")
            
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Reminder scheduler stopped")
            
    def add_reminder(self, user_id: int, note_id: int, reminder_time: datetime, 
                    note_text: str, job_id: Optional[str] = None) -> str:
        """
        Add a reminder for a note.
        
        Args:
            user_id: Telegram user ID
            note_id: Note ID to remind about
            reminder_time: When to send the reminder
            note_text: The note text to include in reminder
            job_id: Optional custom job ID
            
        Returns:
            Job ID for the scheduled reminder
        """
        if not job_id:
            job_id = f"reminder_{user_id}_{note_id}_{int(reminder_time.timestamp())}"
            
        # Schedule the reminder
        self.scheduler.add_job(
            func=self._send_reminder,
            trigger=DateTrigger(run_date=reminder_time),
            args=[user_id, note_id, note_text],
            id=job_id,
            replace_existing=True
        )
        
        logger.info(f"Scheduled reminder for user {user_id}, note {note_id} at {reminder_time}")
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
            logger.info(f"Removed reminder job {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to remove reminder job {job_id}: {e}")
            return False
            
    def get_user_reminders(self, user_id: int) -> list:
        """
        Get all scheduled reminders for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            List of reminder jobs for the user
        """
        user_jobs = []
        for job in self.scheduler.get_jobs():
            if job.id.startswith(f"reminder_{user_id}_"):
                user_jobs.append({
                    'job_id': job.id,
                    'next_run': job.next_run_time,
                    'args': job.args
                })
        return user_jobs
        
    async def _send_reminder(self, user_id: int, note_id: int, note_text: str):
        """
        Send a reminder message to the user.
        
        Args:
            user_id: Telegram user ID
            note_id: Note ID
            note_text: Note text to include in reminder
        """
        if not self.bot:
            logger.error("Bot instance not set, cannot send reminder")
            return
            
        try:
            # Truncate note text if too long
            preview = note_text[:100] + "..." if len(note_text) > 100 else note_text
            
            reminder_message = (
                f"⏰ **Reminder for Note #{note_id}**\n\n"
                f"**Note:** {preview}\n\n"
                f"Use `/list` to view all your notes or `/search <keyword>` to find specific notes."
            )
            
            await self.bot.send_message(
                chat_id=user_id,
                text=reminder_message,
                parse_mode='Markdown'
            )
            
            logger.info(f"Sent reminder to user {user_id} for note {note_id}")
            
        except Exception as e:
            logger.error(f"Failed to send reminder to user {user_id} for note {note_id}: {e}")
            
    def parse_reminder_time(self, time_str: str) -> Optional[datetime]:
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


# Global scheduler instance
scheduler = ReminderScheduler()