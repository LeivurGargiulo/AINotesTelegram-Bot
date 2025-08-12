"""
Enhanced reminder scheduling functionality for the Discord Notes Bot.
Production-ready with error handling, performance monitoring, and security features.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from pytz import timezone
import re

from logger import get_logger, log_performance
from config import REMINDER_TIMEZONE, REMINDER_MAX_PER_USER
from database import db

logger = get_logger(__name__)


class EnhancedDiscordReminderScheduler:
    """Enhanced reminder scheduler with better error handling and performance monitoring."""
    
    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = AsyncIOScheduler(
            timezone=REMINDER_TIMEZONE,
            job_defaults={
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 60  # 1 minute grace time for missed executions
            }
        )
        self.discord_bot = None
        self.reminder_callbacks = {}
        self.user_reminder_counts = {}
        self._setup_event_listeners()
        
    def _setup_event_listeners(self):
        """Set up scheduler event listeners for monitoring."""
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
    
    def _job_executed(self, event):
        """Handle successful job execution."""
        logger.info(f"Reminder job executed successfully: {event.job_id}")
    
    def _job_error(self, event):
        """Handle job execution errors."""
        logger.error(f"Reminder job failed: {event.job_id}, Exception: {event.exception}")
        
        # Try to send error notification to user if possible
        if hasattr(event, 'job_id') and event.job_id in self.reminder_callbacks:
            callback_info = self.reminder_callbacks[event.job_id]
            user_id = callback_info.get('user_id')
            note_id = callback_info.get('note_id')
            
            logger.error(f"Failed to send reminder for user {user_id}, note {note_id}")
    
    def set_discord_bot(self, bot):
        """Set the Discord bot instance for sending reminder messages."""
        self.discord_bot = bot
        
    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Enhanced Discord reminder scheduler started")
            
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Enhanced Discord reminder scheduler stopped")
    
    @log_performance("schedule_reminder")
    def schedule_reminder(self, user_id: int, note_id: int, reminder_time: datetime, 
                         channel_id: int, job_id: Optional[str] = None) -> Optional[str]:
        """
        Schedule a reminder for a note with enhanced validation.
        
        Args:
            user_id: Discord user ID
            note_id: Note ID to remind about
            reminder_time: When to send the reminder
            channel_id: Discord channel ID where to send the reminder
            job_id: Optional custom job ID
            
        Returns:
            Job ID for the scheduled reminder, or None if failed
        """
        try:
            # Check user reminder limit
            if not self._check_user_reminder_limit(user_id):
                logger.warning(f"User {user_id} exceeded reminder limit")
                return None
            
            if not job_id:
                job_id = f"reminder_{user_id}_{note_id}_{int(reminder_time.timestamp())}"
            
            # Get note text from database
            note = db.get_note_by_id(note_id)
            if not note:
                logger.error(f"Note {note_id} not found for reminder scheduling")
                return None
            
            # Store callback information
            self.reminder_callbacks[job_id] = {
                'user_id': user_id,
                'note_id': note_id,
                'channel_id': channel_id,
                'reminder_time': reminder_time.isoformat(),
                'note_text': note['note_text'][:100]  # Store truncated note text
            }
            
            # Schedule the job
            self.scheduler.add_job(
                func=self._send_reminder,
                trigger=DateTrigger(run_date=reminder_time),
                args=[job_id],
                id=job_id,
                replace_existing=True
            )
            
            # Update user reminder count
            self._increment_user_reminder_count(user_id)
            
            logger.info(f"Reminder scheduled: {job_id} for user {user_id}, note {note_id} at {reminder_time}")
            return job_id
            
        except Exception as e:
            logger.error(f"Error scheduling reminder for user {user_id}, note {note_id}: {e}")
            return None
    
    def _check_user_reminder_limit(self, user_id: int) -> bool:
        """Check if user has exceeded reminder limit."""
        current_count = self.user_reminder_counts.get(user_id, 0)
        return current_count < REMINDER_MAX_PER_USER
    
    def _increment_user_reminder_count(self, user_id: int):
        """Increment user's reminder count."""
        self.user_reminder_counts[user_id] = self.user_reminder_counts.get(user_id, 0) + 1
    
    def _decrement_user_reminder_count(self, user_id: int):
        """Decrement user's reminder count."""
        current_count = self.user_reminder_counts.get(user_id, 0)
        if current_count > 0:
            self.user_reminder_counts[user_id] = current_count - 1
    
    async def _send_reminder(self, job_id: str):
        """Send a reminder message to Discord."""
        try:
            if job_id not in self.reminder_callbacks:
                logger.error(f"Reminder callback not found for job {job_id}")
                return
            
            callback_info = self.reminder_callbacks[job_id]
            user_id = callback_info['user_id']
            note_id = callback_info['note_id']
            channel_id = callback_info['channel_id']
            note_text = callback_info['note_text']
            
            if not self.discord_bot:
                logger.error("Discord bot not available for sending reminder")
                return
            
            # Get the channel
            channel = self.discord_bot.get_channel(channel_id)
            if not channel:
                logger.error(f"Channel {channel_id} not found for reminder")
                return
            
            # Create reminder embed
            embed = discord.Embed(
                title="⏰ Reminder",
                description=f"Here's your reminder for note ID {note_id}:",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="Note Text",
                value=note_text + ("..." if len(note_text) == 100 else ""),
                inline=False
            )
            embed.add_field(
                name="Note ID",
                value=str(note_id),
                inline=True
            )
            embed.add_field(
                name="Time",
                value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                inline=True
            )
            
            # Try to mention the user
            try:
                user = await self.discord_bot.fetch_user(user_id)
                await channel.send(f"{user.mention}", embed=embed)
            except:
                # Fallback if user mention fails
                await channel.send(embed=embed)
            
            logger.info(f"Reminder sent successfully: {job_id}")
            
            # Clean up
            self._cleanup_reminder(job_id, user_id)
            
        except Exception as e:
            logger.error(f"Error sending reminder {job_id}: {e}")
            # Clean up even on error
            if job_id in self.reminder_callbacks:
                user_id = self.reminder_callbacks[job_id]['user_id']
                self._cleanup_reminder(job_id, user_id)
    
    def _cleanup_reminder(self, job_id: str, user_id: int):
        """Clean up reminder data after execution."""
        if job_id in self.reminder_callbacks:
            del self.reminder_callbacks[job_id]
        self._decrement_user_reminder_count(user_id)
    
    def cancel_reminder(self, job_id: str) -> bool:
        """Cancel a scheduled reminder."""
        try:
            if job_id in self.reminder_callbacks:
                user_id = self.reminder_callbacks[job_id]['user_id']
                self.scheduler.remove_job(job_id)
                self._cleanup_reminder(job_id, user_id)
                logger.info(f"Reminder cancelled: {job_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error cancelling reminder {job_id}: {e}")
            return False
    
    def get_user_reminders(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all scheduled reminders for a user."""
        try:
            user_reminders = []
            for job_id, callback_info in self.reminder_callbacks.items():
                if callback_info['user_id'] == user_id:
                    user_reminders.append({
                        'job_id': job_id,
                        'note_id': callback_info['note_id'],
                        'reminder_time': callback_info['reminder_time'],
                        'note_text': callback_info['note_text']
                    })
            
            # Sort by reminder time
            user_reminders.sort(key=lambda x: x['reminder_time'])
            return user_reminders
            
        except Exception as e:
            logger.error(f"Error getting reminders for user {user_id}: {e}")
            return []
    
    def cancel_user_reminders(self, user_id: int) -> int:
        """Cancel all reminders for a user."""
        try:
            cancelled_count = 0
            job_ids_to_cancel = []
            
            for job_id, callback_info in self.reminder_callbacks.items():
                if callback_info['user_id'] == user_id:
                    job_ids_to_cancel.append(job_id)
            
            for job_id in job_ids_to_cancel:
                if self.cancel_reminder(job_id):
                    cancelled_count += 1
            
            logger.info(f"Cancelled {cancelled_count} reminders for user {user_id}")
            return cancelled_count
            
        except Exception as e:
            logger.error(f"Error cancelling reminders for user {user_id}: {e}")
            return 0
    
    @log_performance("parse_time_string")
    def parse_time_string(self, time_string: str) -> Optional[datetime]:
        """
        Parse various time string formats into a datetime object.
        
        Args:
            time_string: Time string in various formats
            
        Returns:
            Parsed datetime object or None if parsing failed
        """
        try:
            time_string = time_string.strip().lower()
            now = datetime.now(timezone(REMINDER_TIMEZONE))
            
            # Handle "in X minutes/hours/days" format
            if time_string.startswith('in '):
                return self._parse_relative_time(time_string[3:], now)
            
            # Handle specific time formats
            if ':' in time_string:
                return self._parse_time_format(time_string, now)
            
            # Handle date formats
            if '-' in time_string or '/' in time_string:
                return self._parse_date_format(time_string, now)
            
            # Handle natural language
            return self._parse_natural_language(time_string, now)
            
        except Exception as e:
            logger.error(f"Error parsing time string '{time_string}': {e}")
            return None
    
    def _parse_relative_time(self, time_str: str, base_time: datetime) -> Optional[datetime]:
        """Parse relative time expressions like '30 minutes', '2 hours', '1 day'."""
        try:
            # Match patterns like "30 minutes", "2 hours", "1 day"
            pattern = r'(\d+)\s*(minute|hour|day|week)s?'
            match = re.match(pattern, time_str)
            
            if not match:
                return None
            
            amount = int(match.group(1))
            unit = match.group(2)
            
            if unit == 'minute':
                return base_time + timedelta(minutes=amount)
            elif unit == 'hour':
                return base_time + timedelta(hours=amount)
            elif unit == 'day':
                return base_time + timedelta(days=amount)
            elif unit == 'week':
                return base_time + timedelta(weeks=amount)
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing relative time '{time_str}': {e}")
            return None
    
    def _parse_time_format(self, time_str: str, base_time: datetime) -> Optional[datetime]:
        """Parse time formats like '14:30', '2:30pm'."""
        try:
            # Handle 24-hour format
            if re.match(r'^\d{1,2}:\d{2}$', time_str):
                hour, minute = map(int, time_str.split(':'))
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return base_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # Handle 12-hour format with am/pm
            pattern = r'(\d{1,2}):(\d{2})\s*(am|pm)'
            match = re.match(pattern, time_str)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2))
                period = match.group(3)
                
                if period == 'pm' and hour != 12:
                    hour += 12
                elif period == 'am' and hour == 12:
                    hour = 0
                
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return base_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing time format '{time_str}': {e}")
            return None
    
    def _parse_date_format(self, date_str: str, base_time: datetime) -> Optional[datetime]:
        """Parse date formats like '2024-01-15', '01/15/2024'."""
        try:
            # Handle YYYY-MM-DD format
            if re.match(r'^\d{4}-\d{1,2}-\d{1,2}$', date_str):
                return datetime.strptime(date_str, '%Y-%m-%d').replace(
                    hour=base_time.hour, minute=base_time.minute, second=0, microsecond=0
                )
            
            # Handle MM/DD/YYYY format
            if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', date_str):
                return datetime.strptime(date_str, '%m/%d/%Y').replace(
                    hour=base_time.hour, minute=base_time.minute, second=0, microsecond=0
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing date format '{date_str}': {e}")
            return None
    
    def _parse_natural_language(self, time_str: str, base_time: datetime) -> Optional[datetime]:
        """Parse natural language time expressions."""
        try:
            # Handle "tomorrow", "next week", etc.
            if time_str == 'tomorrow':
                return base_time + timedelta(days=1)
            elif time_str == 'next week':
                return base_time + timedelta(weeks=1)
            elif time_str == 'next month':
                # Simple implementation - add 30 days
                return base_time + timedelta(days=30)
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing natural language '{time_str}': {e}")
            return None
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get scheduler status and statistics."""
        try:
            return {
                'running': self.scheduler.running,
                'job_count': len(self.scheduler.get_jobs()),
                'user_reminder_counts': self.user_reminder_counts.copy(),
                'active_callbacks': len(self.reminder_callbacks)
            }
        except Exception as e:
            logger.error(f"Error getting scheduler status: {e}")
            return {}


# Global scheduler instance
scheduler = EnhancedDiscordReminderScheduler()