#!/usr/bin/env python3
"""
Comprehensive test suite for the Telegram Notes Bot.
Tests database operations, LLM integration, pagination, and reminder functionality.
"""
import os
import sys
import tempfile
import shutil
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import NotesDatabase
from note_categorizer import categorize_note_with_keywords
from reminder_scheduler import ReminderScheduler, scheduler
from config import VALID_CATEGORIES, NOTES_PER_PAGE


class TestDatabase:
    """Test database operations."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        yield temp_db.name
        os.unlink(temp_db.name)
    
    def test_database_initialization(self, temp_db):
        """Test database initialization and table creation."""
        db = NotesDatabase(temp_db)
        assert os.path.exists(temp_db)
        
        # Test that tables exist by trying to add a note
        note_id = db.add_note(12345, "Test note", "task")
        assert note_id > 0
    
    def test_add_and_get_notes(self, temp_db):
        """Test adding and retrieving notes."""
        db = NotesDatabase(temp_db)
        user_id = 12345
        
        # Add test notes
        test_notes = [
            ("Buy groceries tomorrow", "task"),
            ("Great idea for a new app", "idea"),
            ("Be the change you wish to see in the world", "quote"),
            ("Random thought about life", "other")
        ]
        
        note_ids = []
        for note_text, expected_category in test_notes:
            note_id = db.add_note(user_id, note_text, expected_category)
            note_ids.append(note_id)
            assert note_id > 0
        
        # Test getting all notes
        all_notes, total_count = db.get_notes(user_id)
        assert len(all_notes) == 4
        assert total_count == 4
        
        # Test filtering by category
        task_notes, task_count = db.get_notes(user_id, "task")
        assert len(task_notes) == 1
        assert task_count == 1
        assert task_notes[0]['category'] == 'task'
    
    def test_pagination(self, temp_db):
        """Test pagination functionality."""
        db = NotesDatabase(temp_db)
        user_id = 12345
        
        # Add more notes than fit on one page
        for i in range(25):
            db.add_note(user_id, f"Test note {i}", "task")
        
        # Test first page
        notes, total_count = db.get_notes(user_id, page=1, per_page=10)
        assert len(notes) == 10
        assert total_count == 25
        
        # Test second page
        notes, total_count = db.get_notes(user_id, page=2, per_page=10)
        assert len(notes) == 10
        assert total_count == 25
        
        # Test third page
        notes, total_count = db.get_notes(user_id, page=3, per_page=10)
        assert len(notes) == 5
        assert total_count == 25
    
    def test_search_notes(self, temp_db):
        """Test note search functionality."""
        db = NotesDatabase(temp_db)
        user_id = 12345
        
        # Add test notes
        db.add_note(user_id, "Meeting with John tomorrow", "task")
        db.add_note(user_id, "Buy groceries", "task")
        db.add_note(user_id, "Great idea for a new app", "idea")
        
        # Test search
        results, count = db.search_notes(user_id, "meeting")
        assert len(results) == 1
        assert count == 1
        assert "meeting" in results[0]['note_text'].lower()
        
        # Test search with pagination
        results, count = db.search_notes(user_id, "task", page=1, per_page=2)
        assert len(results) == 2
        assert count == 2
    
    def test_delete_note(self, temp_db):
        """Test note deletion."""
        db = NotesDatabase(temp_db)
        user_id = 12345
        
        # Add a note
        note_id = db.add_note(user_id, "Test note to delete", "task")
        
        # Verify note exists
        note = db.get_note_by_id(user_id, note_id)
        assert note is not None
        
        # Delete the note
        success = db.delete_note(user_id, note_id)
        assert success is True
        
        # Verify note is deleted
        note = db.get_note_by_id(user_id, note_id)
        assert note is None
        
        # Test deleting non-existent note
        success = db.delete_note(user_id, 99999)
        assert success is False
    
    def test_reminder_operations(self, temp_db):
        """Test reminder database operations."""
        db = NotesDatabase(temp_db)
        user_id = 12345
        
        # Add a note first
        note_id = db.add_note(user_id, "Test note for reminder", "task")
        
        # Add reminder
        job_id = "test_job_123"
        reminder_time = "2024-01-15 14:30:00"
        success = db.add_reminder(user_id, note_id, job_id, reminder_time)
        assert success is True
        
        # Get user reminders
        reminders = db.get_user_reminders(user_id)
        assert len(reminders) == 1
        assert reminders[0]['note_id'] == note_id
        assert reminders[0]['job_id'] == job_id
        
        # Remove reminder
        success = db.remove_reminder(job_id)
        assert success is True
        
        # Verify reminder is removed
        reminders = db.get_user_reminders(user_id)
        assert len(reminders) == 0


class TestNoteCategorizer:
    """Test note categorization functionality."""
    
    def test_categorize_note_with_keywords_success(self):
        """Test successful note categorization with keywords."""
        # Test task categorization
        category = categorize_note_with_keywords("Buy groceries tomorrow")
        assert category == "task"
        
        # Test idea categorization
        category = categorize_note_with_keywords("Great idea for a new app")
        assert category == "idea"
        
        # Test quote categorization
        category = categorize_note_with_keywords('"Be the change you wish to see in the world"')
        assert category == "quote"
    
    def test_categorize_note_with_keywords_fallback(self):
        """Test keyword categorization fallback to 'other' category."""
        # Test random text that doesn't match any patterns
        category = categorize_note_with_keywords("Random thought about life")
        assert category == "other"


class TestReminderScheduler:
    """Test reminder scheduler functionality."""
    
    @pytest.fixture
    def test_scheduler(self):
        """Create a test scheduler."""
        return ReminderScheduler()
    
    def test_parse_reminder_time_relative(self, test_scheduler):
        """Test parsing relative time formats."""
        # Test relative times
        test_cases = [
            ("in 30 minutes", timedelta(minutes=30)),
            ("in 2 hours", timedelta(hours=2)),
            ("in 1 day", timedelta(days=1)),
            ("in 1 week", timedelta(weeks=1)),
        ]
        
        for time_str, expected_delta in test_cases:
            result = test_scheduler.parse_reminder_time(time_str)
            assert result is not None
            # Check that the result is approximately the expected time
            now = datetime.now()
            expected_time = now + expected_delta
            time_diff = abs((result - expected_time).total_seconds())
            assert time_diff < 60  # Within 1 minute
    
    def test_parse_reminder_time_absolute(self, test_scheduler):
        """Test parsing absolute time formats."""
        # Test 24-hour format
        result = test_scheduler.parse_reminder_time("14:30")
        assert result is not None
        assert result.hour == 14
        assert result.minute == 30
        
        # Test 12-hour format
        result = test_scheduler.parse_reminder_time("2:30pm")
        assert result is not None
        assert result.hour == 14
        assert result.minute == 30
    
    def test_parse_reminder_time_invalid(self, test_scheduler):
        """Test parsing invalid time formats."""
        invalid_times = [
            "invalid time",
            "25:70",
            "in 30 invalid",
            "",
        ]
        
        for time_str in invalid_times:
            result = test_scheduler.parse_reminder_time(time_str)
            assert result is None
    
    @pytest.mark.asyncio
    async def test_scheduler_operations(self, test_scheduler):
        """Test scheduler operations."""
        # Mock bot
        mock_bot = Mock()
        test_scheduler.set_bot(mock_bot)
        
        # Test adding reminder
        user_id = 12345
        note_id = 1
        reminder_time = datetime.now() + timedelta(minutes=1)
        note_text = "Test note"
        
        job_id = test_scheduler.add_reminder(user_id, note_id, reminder_time, note_text)
        assert job_id is not None
        
        # Test getting user reminders
        reminders = test_scheduler.get_user_reminders(user_id)
        assert len(reminders) == 1
        
        # Test removing reminder
        success = test_scheduler.remove_reminder(job_id)
        assert success is True
        
        # Verify reminder is removed
        reminders = test_scheduler.get_user_reminders(user_id)
        assert len(reminders) == 0


class TestIntegration:
    """Integration tests for the complete system."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for integration testing."""
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        yield temp_db.name
        os.unlink(temp_db.name)
    
    def test_full_workflow(self, temp_db):
        """Test a complete workflow: add note, search, paginate, set reminder."""
        db = NotesDatabase(temp_db)
        user_id = 12345
        
        # 1. Add multiple notes
        note_ids = []
        for i in range(15):
            note_id = db.add_note(user_id, f"Test note {i} for workflow", "task")
            note_ids.append(note_id)
        
        # 2. Test pagination
        notes, total_count = db.get_notes(user_id, page=1, per_page=10)
        assert len(notes) == 10
        assert total_count == 15
        
        notes, total_count = db.get_notes(user_id, page=2, per_page=10)
        assert len(notes) == 5
        assert total_count == 15
        
        # 3. Test search with pagination
        results, count = db.search_notes(user_id, "workflow", page=1, per_page=5)
        assert len(results) == 5
        assert count == 15
        
        # 4. Test reminder functionality
        note_id = note_ids[0]
        job_id = "test_job_workflow"
        reminder_time = "2024-01-15 14:30:00"
        
        success = db.add_reminder(user_id, note_id, job_id, reminder_time)
        assert success is True
        
        reminders = db.get_user_reminders(user_id)
        assert len(reminders) == 1
        
        # 5. Test note deletion (should also remove reminders)
        success = db.delete_note(user_id, note_id)
        assert success is True
        
        # Verify note is deleted
        note = db.get_note_by_id(user_id, note_id)
        assert note is None
    
    def test_keyword_categorization_integration_with_database(self, temp_db):
        """Test keyword categorization integration with database operations."""
        db = NotesDatabase(temp_db)
        user_id = 12345
        
        # Add note with keyword categorization
        note_text = "Great idea for a new mobile app"
        category = categorize_note_with_keywords(note_text)
        note_id = db.add_note(user_id, note_text, category)
        
        # Verify categorization
        assert category == "idea"
        
        # Verify note is stored correctly
        note = db.get_note_by_id(user_id, note_id)
        assert note is not None
        assert note['category'] == "idea"
        assert note['note_text'] == note_text


def run_tests():
    """Run all tests and display results."""
    print("🧪 Running comprehensive test suite for Telegram Notes Bot...")
    print("=" * 60)
    
    # Test database operations
    print("\n📊 Testing database operations...")
    test_db = TestDatabase()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_db:
        temp_db.close()
        try:
            test_db.test_database_initialization(temp_db.name)
            test_db.test_add_and_get_notes(temp_db.name)
            test_db.test_pagination(temp_db.name)
            test_db.test_search_notes(temp_db.name)
            test_db.test_delete_note(temp_db.name)
            test_db.test_reminder_operations(temp_db.name)
            print("  ✅ Database tests passed!")
        finally:
            os.unlink(temp_db.name)
    
    # Test keyword categorization
    print("\n🔍 Testing keyword categorization...")
    test_categorizer = TestNoteCategorizer()
    test_categorizer.test_categorize_note_with_keywords_success()
    test_categorizer.test_categorize_note_with_keywords_fallback()
    print("  ✅ Keyword categorization tests passed!")
    
    # Test reminder scheduler
    print("\n⏰ Testing reminder scheduler...")
    test_scheduler = TestReminderScheduler()
    test_scheduler.test_parse_reminder_time_relative(test_scheduler.test_scheduler())
    test_scheduler.test_parse_reminder_time_absolute(test_scheduler.test_scheduler())
    test_scheduler.test_parse_reminder_time_invalid(test_scheduler.test_scheduler())
    print("  ✅ Reminder scheduler tests passed!")
    
    # Test integration
    print("\n🔗 Testing integration...")
    test_integration = TestIntegration()
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_db:
        temp_db.close()
        try:
            test_integration.test_full_workflow(temp_db.name)
            print("  ✅ Integration tests passed!")
        finally:
            os.unlink(temp_db.name)
    
    print("\n🎉 All tests completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()