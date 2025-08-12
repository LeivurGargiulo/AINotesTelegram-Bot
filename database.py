"""
Enhanced database operations for the Discord Notes Bot.
Handles SQLite database operations with connection pooling, caching, and performance optimizations.
"""
import sqlite3
import json
import asyncio
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from contextlib import contextmanager
from functools import wraps
import time

from config import DATABASE_FILE, TIMESTAMP_FORMAT, NOTES_PER_PAGE, DATABASE_TIMEOUT, CACHE_ENABLED, CACHE_TTL
from logger import get_logger, log_performance

logger = get_logger(__name__)


class DatabaseConnectionPool:
    """Manages database connections with pooling for better performance."""
    
    def __init__(self, db_file: str, max_connections: int = 10, timeout: int = 30):
        self.db_file = db_file
        self.max_connections = max_connections
        self.timeout = timeout
        self._connections = []
        self._lock = threading.Lock()
        self._initialized = False
    
    def _initialize_pool(self):
        """Initialize the connection pool."""
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:
                return
            
            # Create initial connections
            for _ in range(min(3, self.max_connections)):
                conn = sqlite3.connect(
                    self.db_file,
                    timeout=self.timeout,
                    check_same_thread=False
                )
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=10000")
                conn.execute("PRAGMA temp_store=MEMORY")
                self._connections.append(conn)
            
            self._initialized = True
            logger.info(f"Database connection pool initialized with {len(self._connections)} connections")
    
    @contextmanager
    def get_connection(self):
        """Get a database connection from the pool."""
        self._initialize_pool()
        
        conn = None
        try:
            with self._lock:
                if self._connections:
                    conn = self._connections.pop()
                else:
                    # Create a new connection if pool is empty
                    conn = sqlite3.connect(
                        self.db_file,
                        timeout=self.timeout,
                        check_same_thread=False
                    )
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA synchronous=NORMAL")
                    conn.execute("PRAGMA cache_size=10000")
                    conn.execute("PRAGMA temp_store=MEMORY")
            
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                try:
                    conn.close()
                except:
                    pass
            raise
        finally:
            # Return connection to pool if it's still valid
            if conn:
                try:
                    conn.rollback()  # Rollback any uncommitted changes
                    with self._lock:
                        if len(self._connections) < self.max_connections:
                            self._connections.append(conn)
                        else:
                            conn.close()
                except:
                    conn.close()
    
    def close_all(self):
        """Close all connections in the pool."""
        with self._lock:
            for conn in self._connections:
                try:
                    conn.close()
                except:
                    pass
            self._connections.clear()
            self._initialized = False


class Cache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self._cache = {}
        self._timestamps = {}
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        with self._lock:
            if key not in self._cache:
                return None
            
            # Check if expired
            if time.time() - self._timestamps[key] > self.ttl:
                del self._cache[key]
                del self._timestamps[key]
                return None
            
            return self._cache[key]
    
    def set(self, key: str, value: Any):
        """Set a value in cache."""
        with self._lock:
            self._cache[key] = value
            self._timestamps[key] = time.time()
    
    def delete(self, key: str):
        """Delete a value from cache."""
        with self._lock:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)
    
    def clear(self):
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
    
    def cleanup_expired(self):
        """Remove expired entries."""
        current_time = time.time()
        with self._lock:
            expired_keys = [
                key for key, timestamp in self._timestamps.items()
                if current_time - timestamp > self.ttl
            ]
            for key in expired_keys:
                del self._cache[key]
                del self._timestamps[key]


class NotesDatabase:
    """Enhanced database operations for notes with caching and connection pooling."""
    
    def __init__(self, db_file: str = DATABASE_FILE):
        """Initialize database connection and create tables if they don't exist."""
        self.db_file = db_file
        self.pool = DatabaseConnectionPool(db_file, timeout=DATABASE_TIMEOUT)
        self.cache = Cache(CACHE_TTL) if CACHE_ENABLED else None
        self._create_tables()
        logger.info(f"Enhanced database initialized with file: {db_file}")
    
    def _create_tables(self):
        """Create the notes table if it doesn't exist."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create notes table with indexes for better performance
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
            
            # Create indexes for better query performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_notes_user_id ON notes(user_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_notes_category ON notes(category)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_notes_user_category ON notes(user_id, category)
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
            
            # Create indexes for reminders
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_reminders_user_id ON reminders(user_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_reminders_note_id ON reminders(note_id)
            ''')
            
            conn.commit()
            logger.info("Database tables and indexes created/verified")
    
    def _get_cache_key(self, operation: str, *args) -> str:
        """Generate a cache key for an operation."""
        return f"{operation}:{':'.join(str(arg) for arg in args)}"
    
    def _invalidate_user_cache(self, user_id: int):
        """Invalidate all cache entries for a user."""
        if not self.cache:
            return
        
        # This is a simplified invalidation - in production, you might want
        # a more sophisticated cache invalidation strategy
        keys_to_delete = []
        for key in self.cache._cache.keys():
            if f"user_id:{user_id}" in key:
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            self.cache.delete(key)
    
    @log_performance("add_note")
    def add_note(self, user_id: int, note_text: str, category: str) -> int:
        """Add a new note to the database and return its ID."""
        timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
        
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notes (user_id, note_text, category, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, note_text, category, timestamp, timestamp))
            conn.commit()
            note_id = cursor.lastrowid
            
            # Invalidate user cache
            self._invalidate_user_cache(user_id)
            
            logger.info(f"Added note {note_id} for user {user_id} in category {category}")
            return note_id
    
    @log_performance("get_notes")
    def get_notes(self, user_id: int, category: Optional[str] = None, 
                  page: int = 1, per_page: int = NOTES_PER_PAGE) -> Tuple[List[Dict], int]:
        """
        Get notes for a user with pagination support and caching.
        
        Args:
            user_id: User ID
            category: Optional category filter
            page: Page number (1-based)
            per_page: Notes per page
            
        Returns:
            Tuple of (notes_list, total_count)
        """
        # Try cache first
        cache_key = self._get_cache_key("get_notes", user_id, category, page, per_page)
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for notes query: {cache_key}")
                return cached_result
        
        offset = (page - 1) * per_page
        
        with self.pool.get_connection() as conn:
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
            
            result = (notes, total_count)
            
            # Cache the result
            if self.cache:
                self.cache.set(cache_key, result)
            
            logger.info(f"Retrieved {len(notes)} notes for user {user_id} (page {page}, total: {total_count})")
            return result
    
    @log_performance("delete_note")
    def delete_note(self, note_id: int, user_id: int) -> bool:
        """Delete a note by ID. Returns True if successful, False if note not found."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM notes
                WHERE id = ? AND user_id = ?
            ''', (note_id, user_id))
            conn.commit()
            success = cursor.rowcount > 0
            
            if success:
                # Invalidate user cache
                self._invalidate_user_cache(user_id)
                logger.info(f"Deleted note {note_id} for user {user_id}")
            else:
                logger.warning(f"Failed to delete note {note_id} for user {user_id} (not found or no permission)")
                
            return success
    
    @log_performance("search_notes")
    def search_notes(self, user_id: int, keyword: str, 
                    page: int = 1, per_page: int = NOTES_PER_PAGE) -> Tuple[List[Dict], int]:
        """
        Search notes by keyword with pagination support and caching.
        
        Args:
            user_id: User ID
            keyword: Search keyword
            page: Page number (1-based)
            per_page: Notes per page
            
        Returns:
            Tuple of (notes_list, total_count)
        """
        # Try cache first
        cache_key = self._get_cache_key("search_notes", user_id, keyword, page, per_page)
        if self.cache:
            cached_result = self.cache.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for search query: {cache_key}")
                return cached_result
        
        offset = (page - 1) * per_page
        
        with self.pool.get_connection() as conn:
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
            
            result = (notes, total_count)
            
            # Cache the result
            if self.cache:
                self.cache.set(cache_key, result)
            
            logger.info(f"Search for '{keyword}' returned {len(notes)} notes for user {user_id} (page {page}, total: {total_count})")
            return result
    
    @log_performance("get_note_by_id")
    def get_note_by_id(self, note_id: int, user_id: Optional[int] = None) -> Optional[Dict]:
        """Get a specific note by ID, optionally filtered by user."""
        with self.pool.get_connection() as conn:
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
                return dict(row)
            return None
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get statistics for a user."""
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get total notes count
            cursor.execute('''
                SELECT COUNT(*) FROM notes WHERE user_id = ?
            ''', (user_id,))
            total_notes = cursor.fetchone()[0]
            
            # Get notes by category
            cursor.execute('''
                SELECT category, COUNT(*) as count
                FROM notes
                WHERE user_id = ?
                GROUP BY category
            ''', (user_id,))
            category_counts = dict(cursor.fetchall())
            
            # Get recent activity
            cursor.execute('''
                SELECT COUNT(*) FROM notes
                WHERE user_id = ? AND created_at >= datetime('now', '-7 days')
            ''', (user_id,))
            recent_notes = cursor.fetchone()[0]
            
            return {
                'total_notes': total_notes,
                'category_counts': category_counts,
                'recent_notes': recent_notes
            }
    
    def cleanup_old_reminders(self, days: int = 30):
        """Clean up old reminders that are no longer needed."""
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.strftime(TIMESTAMP_FORMAT)
        
        with self.pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM reminders
                WHERE reminder_time < ?
            ''', (cutoff_str,))
            deleted_count = cursor.rowcount
            conn.commit()
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old reminders")
    
    def close(self):
        """Close all database connections."""
        self.pool.close_all()
        if self.cache:
            self.cache.clear()
        logger.info("Database connections closed")


# Global database instance
db = NotesDatabase()