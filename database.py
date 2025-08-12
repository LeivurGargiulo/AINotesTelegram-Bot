"""
Database operations for the Telegram Notes Bot.
Handles SQLite database operations for storing and retrieving notes.
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from config import DATABASE_FILE, TIMESTAMP_FORMAT


class NotesDatabase:
    """Handles all database operations for notes."""
    
    def __init__(self, db_file: str = DATABASE_FILE):
        """Initialize database connection and create tables if they don't exist."""
        self.db_file = db_file
        self._create_tables()
    
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
            conn.commit()
    
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
            return cursor.lastrowid
    
    def get_notes(self, user_id: int, category: Optional[str] = None) -> List[Dict]:
        """Get all notes for a user, optionally filtered by category."""
        with sqlite3.connect(self.db_file) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if category:
                cursor.execute('''
                    SELECT id, note_text, category, timestamp, created_at
                    FROM notes
                    WHERE user_id = ? AND category = ?
                    ORDER BY created_at DESC
                ''', (user_id, category))
            else:
                cursor.execute('''
                    SELECT id, note_text, category, timestamp, created_at
                    FROM notes
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                ''', (user_id,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def delete_note(self, user_id: int, note_id: int) -> bool:
        """Delete a note by ID. Returns True if successful, False if note not found."""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM notes
                WHERE id = ? AND user_id = ?
            ''', (note_id, user_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def search_notes(self, user_id: int, keyword: str) -> List[Dict]:
        """Search notes by keyword in the note text."""
        with sqlite3.connect(self.db_file) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, note_text, category, timestamp, created_at
                FROM notes
                WHERE user_id = ? AND note_text LIKE ?
                ORDER BY created_at DESC
            ''', (user_id, f'%{keyword}%'))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_note_by_id(self, user_id: int, note_id: int) -> Optional[Dict]:
        """Get a specific note by ID."""
        with sqlite3.connect(self.db_file) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, note_text, category, timestamp, created_at
                FROM notes
                WHERE id = ? AND user_id = ?
            ''', (note_id, user_id))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_note_count(self, user_id: int) -> int:
        """Get the total number of notes for a user."""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM notes WHERE user_id = ?
            ''', (user_id,))
            return cursor.fetchone()[0]