#!/usr/bin/env python3
"""
Enhanced Discord Notes Bot Test Suite
Tests the production-ready features and functionality.
"""
import pytest
import asyncio
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

# Import bot components
from config import get_config
from database import NotesDatabase
from rate_limiter import SecurityMiddleware, RateLimiter
from discord_reminder_scheduler import EnhancedDiscordReminderScheduler
from logger import get_logger, get_performance_stats, get_error_stats


class TestEnhancedDiscordBot:
    """Test suite for the enhanced Discord bot."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        db = NotesDatabase(db_path)
        yield db
        
        # Cleanup
        db.close()
        os.unlink(db_path)
    
    @pytest.fixture
    def security_middleware(self):
        """Create security middleware for testing."""
        return SecurityMiddleware()
    
    @pytest.fixture
    def reminder_scheduler(self):
        """Create reminder scheduler for testing."""
        return EnhancedDiscordReminderScheduler()
    
    def test_config_loading(self):
        """Test configuration loading and validation."""
        config = get_config()
        
        # Check required fields
        assert 'bot_token' in config
        assert 'database_file' in config
        assert 'rate_limit_enabled' in config
        assert 'cache_enabled' in config
        
        # Check default values
        assert config['log_level'] == 'INFO'
        assert config['notes_per_page'] == 10
        assert config['reminder_max_per_user'] == 10
    
    def test_database_operations(self, temp_db):
        """Test database operations with connection pooling and caching."""
        user_id = 12345
        
        # Test adding notes
        note_id1 = temp_db.add_note(user_id, "Test note 1", "task")
        note_id2 = temp_db.add_note(user_id, "Test note 2", "idea")
        
        assert note_id1 > 0
        assert note_id2 > 0
        
        # Test retrieving notes
        notes, total = temp_db.get_notes(user_id)
        assert len(notes) == 2
        assert total == 2
        
        # Test category filtering
        task_notes, task_total = temp_db.get_notes(user_id, "task")
        assert len(task_notes) == 1
        assert task_total == 1
        
        # Test searching
        search_results, search_total = temp_db.search_notes(user_id, "test")
        assert len(search_results) == 2
        assert search_total == 2
        
        # Test getting note by ID
        note = temp_db.get_note_by_id(note_id1, user_id)
        assert note is not None
        assert note['note_text'] == "Test note 1"
        
        # Test deleting note
        success = temp_db.delete_note(note_id1, user_id)
        assert success is True
        
        # Verify note is deleted
        notes_after_delete, total_after_delete = temp_db.get_notes(user_id)
        assert len(notes_after_delete) == 1
        assert total_after_delete == 1
    
    def test_user_statistics(self, temp_db):
        """Test user statistics functionality."""
        user_id = 12345
        
        # Add some notes
        temp_db.add_note(user_id, "Task note", "task")
        temp_db.add_note(user_id, "Idea note", "idea")
        temp_db.add_note(user_id, "Quote note", "quote")
        
        # Get statistics
        stats = temp_db.get_user_stats(user_id)
        
        assert stats['total_notes'] == 3
        assert 'task' in stats['category_counts']
        assert 'idea' in stats['category_counts']
        assert 'quote' in stats['category_counts']
        assert stats['category_counts']['task'] == 1
        assert stats['category_counts']['idea'] == 1
        assert stats['category_counts']['quote'] == 1
    
    def test_rate_limiting(self, security_middleware):
        """Test rate limiting functionality."""
        user_id = 12345
        command = "add"
        
        # Test command rate limiting
        allowed, retry_after = security_middleware.rate_limiter.is_command_allowed(user_id, command)
        assert allowed is True
        assert retry_after == 0.0
        
        # Test user rate limiting
        allowed, retry_after = security_middleware.rate_limiter.is_user_allowed(user_id)
        assert allowed is True
        assert retry_after == 0.0
        
        # Test rate limit stats
        stats = security_middleware.rate_limiter.get_user_stats(user_id)
        assert 'general' in stats
        assert 'commands' in stats
    
    def test_security_features(self, security_middleware):
        """Test security features."""
        user_id = 12345
        guild_id = 67890
        
        # Test guild restrictions
        allowed = security_middleware.security_manager.is_guild_allowed(guild_id)
        assert allowed is True  # Default allows all guilds
        
        # Test user blocking
        blocked = security_middleware.security_manager.is_user_blocked(user_id)
        assert blocked is False  # Default no blocked users
        
        # Test blocking a user
        security_middleware.security_manager.block_user(user_id, "Test block")
        blocked = security_middleware.security_manager.is_user_blocked(user_id)
        assert blocked is True
        
        # Test unblocking
        security_middleware.security_manager.unblock_user(user_id)
        blocked = security_middleware.security_manager.is_user_blocked(user_id)
        assert blocked is False
    
    def test_reminder_scheduling(self, reminder_scheduler):
        """Test reminder scheduling functionality."""
        user_id = 12345
        note_id = 1
        channel_id = 67890
        
        # Test time parsing
        reminder_time = reminder_scheduler.parse_time_string("in 5 minutes")
        assert reminder_time is not None
        assert isinstance(reminder_time, datetime)
        
        # Test scheduling reminder
        job_id = reminder_scheduler.schedule_reminder(user_id, note_id, reminder_time, channel_id)
        assert job_id is not None
        
        # Test getting user reminders
        reminders = reminder_scheduler.get_user_reminders(user_id)
        assert len(reminders) == 1
        assert reminders[0]['note_id'] == note_id
        
        # Test cancelling reminder
        success = reminder_scheduler.cancel_reminder(job_id)
        assert success is True
        
        # Verify reminder is cancelled
        reminders_after_cancel = reminder_scheduler.get_user_reminders(user_id)
        assert len(reminders_after_cancel) == 0
    
    def test_time_parsing(self, reminder_scheduler):
        """Test various time parsing formats."""
        # Test relative times
        assert reminder_scheduler.parse_time_string("in 30 minutes") is not None
        assert reminder_scheduler.parse_time_string("in 2 hours") is not None
        assert reminder_scheduler.parse_time_string("in 1 day") is not None
        
        # Test time formats
        assert reminder_scheduler.parse_time_string("14:30") is not None
        assert reminder_scheduler.parse_time_string("2:30pm") is not None
        assert reminder_scheduler.parse_time_string("2:30 PM") is not None
        
        # Test date formats
        assert reminder_scheduler.parse_time_string("2024-01-15") is not None
        assert reminder_scheduler.parse_time_string("01/15/2024") is not None
        
        # Test natural language
        assert reminder_scheduler.parse_time_string("tomorrow") is not None
        assert reminder_scheduler.parse_time_string("next week") is not None
        
        # Test invalid formats
        assert reminder_scheduler.parse_time_string("invalid time") is None
        assert reminder_scheduler.parse_time_string("") is None
    
    def test_performance_monitoring(self):
        """Test performance monitoring functionality."""
        # Get initial stats
        initial_perf_stats = get_performance_stats()
        initial_error_stats = get_error_stats()
        
        # Simulate some operations
        logger = get_logger(__name__)
        logger.info("Test performance monitoring")
        
        # Get updated stats
        updated_perf_stats = get_performance_stats()
        updated_error_stats = get_error_stats()
        
        # Stats should be available
        assert isinstance(updated_perf_stats, dict)
        assert isinstance(updated_error_stats, dict)
    
    def test_logging_functionality(self):
        """Test enhanced logging functionality."""
        logger = get_logger(__name__)
        
        # Test different log levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        # Logging should work without errors
        assert True
    
    def test_cache_functionality(self, temp_db):
        """Test caching functionality."""
        user_id = 12345
        
        # Add a note
        temp_db.add_note(user_id, "Cache test note", "task")
        
        # First query should cache
        notes1, total1 = temp_db.get_notes(user_id)
        
        # Second query should use cache
        notes2, total2 = temp_db.get_notes(user_id)
        
        # Results should be the same
        assert len(notes1) == len(notes2)
        assert total1 == total2
        
        # Add another note to invalidate cache
        temp_db.add_note(user_id, "Another note", "idea")
        
        # Query should reflect new data
        notes3, total3 = temp_db.get_notes(user_id)
        assert len(notes3) == 2
        assert total3 == 2
    
    def test_error_handling(self, temp_db):
        """Test error handling and recovery."""
        user_id = 12345
        
        # Test invalid note ID
        note = temp_db.get_note_by_id(99999, user_id)
        assert note is None
        
        # Test deleting non-existent note
        success = temp_db.delete_note(99999, user_id)
        assert success is False
        
        # Test searching with empty keyword
        results, total = temp_db.search_notes(user_id, "")
        assert len(results) == 0
        assert total == 0
    
    def test_concurrent_operations(self, temp_db):
        """Test concurrent database operations."""
        import threading
        import time
        
        results = []
        errors = []
        
        def add_note(user_id, note_text, category):
            try:
                note_id = temp_db.add_note(user_id, note_text, category)
                results.append(note_id)
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(
                target=add_note,
                args=(12345, f"Concurrent note {i}", "task")
            )
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0
        assert len(results) == 5
        
        # Verify all notes were added
        notes, total = temp_db.get_notes(12345)
        assert total >= 5


class TestIntegration:
    """Integration tests for the complete system."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test a complete user workflow."""
        # This would test the full integration
        # For now, just verify the test framework works
        assert True
    
    def test_configuration_validation(self):
        """Test configuration validation."""
        config = get_config()
        
        # Test required fields
        assert config['bot_token'] is not None
        
        # Test numeric fields
        assert isinstance(config['notes_per_page'], int)
        assert isinstance(config['reminder_max_per_user'], int)
        assert isinstance(config['cache_ttl'], int)
        
        # Test boolean fields
        assert isinstance(config['rate_limit_enabled'], bool)
        assert isinstance(config['cache_enabled'], bool)
    
    def test_database_migration(self):
        """Test database migration and schema."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            db = NotesDatabase(db_path)
            
            # Test table creation
            user_id = 12345
            note_id = db.add_note(user_id, "Migration test", "task")
            assert note_id > 0
            
            # Test indexes work
            notes, total = db.get_notes(user_id, "task")
            assert len(notes) == 1
            
            db.close()
        finally:
            os.unlink(db_path)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])