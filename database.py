"""
Database operations for the Telegram Notes Bot.
Handles SQLite database operations for storing and retrieving notes.
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from config import DATABASE_FILE, TIMESTAMP_FORMAT, NOTES_PER_PAGE
from logger import get_logger

logger = get_logger(__name__)


class NotesDatabase:
    """Handles all database operations for notes."""
    
    def __init__(self, db_file: str = DATABASE_FILE):
        """Initialize database connection and create tables if they don't exist."""
        self.db_file = db_file
        self._create_tables()
        logger.info(f"Database initialized with file: {db_file}")
    
    def _create_tables(self):
        """Create the notes table if it doesn't exist."""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    note_text TEXT NOT NULL,
                    category TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            ''')
            
            # Create reminders table for tracking scheduled reminders
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    note_id INTEGER NOT NULL,
                    job_id TEXT NOT NULL,
                    reminder_time TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (note_id) REFERENCES notes (id) ON DELETE CASCADE
                )
            ''')
            
            conn.commit()
            logger.info("Database tables created/verified")
    
    def add_note(self, user_id: int, note_text: str, category: str) -> int:
        """Add a new note to the database and return its ID."""
        timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
        
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notes (user_id, note_text, category, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, note_text, category, timestamp, timestamp))
            conn.commit()
            note_id = cursor.lastrowid
            logger.info(f"Added note {note_id} for user {user_id} in category {category}")
            return note_id
    
    def get_notes(self, user_id: int, category: Optional[str] = None, 
                  page: int = 1, per_page: int = NOTES_PER_PAGE) -> Tuple[List[Dict], int]:
        """
        Get notes for a user with pagination support.
        
        Args:
            user_id: User ID
            category: Optional category filter
            page: Page number (1-based)
            per_page: Notes per page
            
        Returns:
            Tuple of (notes_list, total_count)
        """
        offset = (page - 1) * per_page
        
        with sqlite3.connect(self.db_file) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Build query based on whether category filter is applied
            if category:
                # Get total count
                cursor.execute('''
                    SELECT COUNT(*) FROM notes
                    WHERE user_id = ? AND category = ?
                ''', (user_id, category))
                total_count = cursor.fetchone()[0]
                
                # Get paginated results
                cursor.execute('''
                    SELECT id, note_text, category, timestamp, created_at
                    FROM notes
                    WHERE user_id = ? AND category = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                ''', (user_id, category, per_page, offset))
            else:
                # Get total count
                cursor.execute('''
                    SELECT COUNT(*) FROM notes WHERE user_id = ?
                ''', (user_id,))
                total_count = cursor.fetchone()[0]
                
                # Get paginated results
                cursor.execute('''
                    SELECT id, note_text, category, timestamp, created_at
                    FROM notes
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                ''', (user_id, per_page, offset))
            
            rows = cursor.fetchall()
            notes = [dict(row) for row in rows]
            
            logger.info(f"Retrieved {len(notes)} notes for user {user_id} (page {page}, total: {total_count})")
            return notes, total_count
    
    def delete_note(self, user_id: int, note_id: int) -> bool:
        """Delete a note by ID. Returns True if successful, False if note not found."""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM notes
                WHERE id = ? AND user_id = ?
            ''', (note_id, user_id))
            conn.commit()
            success = cursor.rowcount > 0
            
            if success:
                logger.info(f"Deleted note {note_id} for user {user_id}")
            else:
                logger.warning(f"Failed to delete note {note_id} for user {user_id} (not found or no permission)")
                
            return success
    
    def search_notes(self, user_id: int, keyword: str, 
                    page: int = 1, per_page: int = NOTES_PER_PAGE) -> Tuple[List[Dict], int]:
        """
        Search notes by keyword with pagination support.
        
        Args:
            user_id: User ID
            keyword: Search keyword
            page: Page number (1-based)
            per_page: Notes per page
            
        Returns:
            Tuple of (notes_list, total_count)
        """
        offset = (page - 1) * per_page
        
        with sqlite3.connect(self.db_file) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get total count
            cursor.execute('''
                SELECT COUNT(*) FROM notes
                WHERE user_id = ? AND note_text LIKE ?
            ''', (user_id, f'%{keyword}%'))
            total_count = cursor.fetchone()[0]
            
            # Get paginated results
            cursor.execute('''
                SELECT id, note_text, category, timestamp, created_at
                FROM notes
                WHERE user_id = ? AND note_text LIKE ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (user_id, f'%{keyword}%', per_page, offset))
            
            rows = cursor.fetchall()
            notes = [dict(row) for row in rows]
            
            logger.info(f"Search for '{keyword}' returned {len(notes)} notes for user {user_id} (page {page}, total: {total_count})")
            return notes, total_count
    
    def get_note_by_id(self, note_id: int, user_id: Optional[int] = None) -> Optional[Dict]:
        """Get a specific note by ID, optionally filtered by user."""
        with sqlite3.connect(self.db_file) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute('''
                    SELECT id, user_id, note_text, category, timestamp, created_at
                    FROM notes
                    WHERE id = ? AND user_id = ?
                ''', (note_id, user_id))
            else:
                cursor.execute('''
                    SELECT id, user_id, note_text, category, timestamp, created_at
                    FROM notes
                    WHERE id = ?
                ''', (note_id,))
            
            row = cursor.fetchone()
            if row:
                logger.info(f"Retrieved note {note_id}" + (f" for user {user_id}" if user_id else ""))
                return dict(row)
            else:
                logger.warning(f"Note {note_id} not found" + (f" for user {user_id}" if user_id else ""))
                return None
    
    def get_note_count(self, user_id: int, category: Optional[str] = None) -> int:
        """Get the total number of notes for a user, optionally filtered by category."""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            if category:
                cursor.execute('''
                    SELECT COUNT(*) FROM notes WHERE user_id = ? AND category = ?
                ''', (user_id, category))
            else:
                cursor.execute('''
                    SELECT COUNT(*) FROM notes WHERE user_id = ?
                ''', (user_id,))
            return cursor.fetchone()[0]
    
    def add_reminder(self, user_id: int, note_id: int, job_id: str, reminder_time: str) -> bool:
        """Add a reminder record to the database."""
        timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
        
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO reminders (user_id, note_id, job_id, reminder_time, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, note_id, job_id, reminder_time, timestamp))
            conn.commit()
            logger.info(f"Added reminder record for user {user_id}, note {note_id}, job {job_id}")
            return True
    
    def remove_reminder(self, job_id: str) -> bool:
        """Remove a reminder record from the database."""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM reminders WHERE job_id = ?
            ''', (job_id,))
            conn.commit()
            success = cursor.rowcount > 0
            
            if success:
                logger.info(f"Removed reminder record for job {job_id}")
            else:
                logger.warning(f"Reminder record for job {job_id} not found")
                
            return success
    
    def get_user_reminders(self, user_id: int) -> List[Dict]:
        """Get all reminder records for a user."""
        with sqlite3.connect(self.db_file) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.id, r.note_id, r.job_id, r.reminder_time, r.created_at,
                       n.note_text, n.category
                FROM reminders r
                JOIN notes n ON r.note_id = n.id
                WHERE r.user_id = ?
                ORDER BY r.reminder_time ASC
            ''', (user_id,))
            
            rows = cursor.fetchall()
            reminders = [dict(row) for row in rows]
            logger.info(f"Retrieved {len(reminders)} reminders for user {user_id}")
            return reminders