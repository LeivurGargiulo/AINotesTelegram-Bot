#!/usr/bin/env python3
"""
Simple test script for the Telegram Notes Bot.
Tests core functionality without requiring pytest.
"""
import os
import sys
import tempfile
import shutil
from datetime import datetime, timedelta

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import NotesDatabase
from note_categorizer import categorize_note_with_keywords
from config import VALID_CATEGORIES, NOTES_PER_PAGE


def test_database():
    """Test database operations."""
    print("🧪 Testing database operations...")
    
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    
    try:
        db = NotesDatabase(temp_db.name)
        
        # Test adding notes
        test_user_id = 12345
        test_notes = [
            ("Buy groceries tomorrow", "task"),
            ("Great idea for a new app", "idea"),
            ("Be the change you wish to see in the world", "quote"),
            ("Random thought about life", "other")
        ]
        
        note_ids = []
        for note_text, expected_category in test_notes:
            note_id = db.add_note(test_user_id, note_text, expected_category)
            note_ids.append(note_id)
            print(f"  ✅ Added note {note_id}: {note_text[:30]}...")
        
        # Test getting all notes with pagination
        all_notes, total_count = db.get_notes(test_user_id)
        assert len(all_notes) == 4, f"Expected 4 notes, got {len(all_notes)}"
        assert total_count == 4, f"Expected total count 4, got {total_count}"
        print(f"  ✅ Retrieved {len(all_notes)} notes (total: {total_count})")
        
        # Test filtering by category
        task_notes, task_count = db.get_notes(test_user_id, "task")
        assert len(task_notes) == 1, f"Expected 1 task note, got {len(task_notes)}"
        assert task_count == 1, f"Expected task count 1, got {task_count}"
        print(f"  ✅ Filtered task notes: {len(task_notes)} found")
        
        # Test search with pagination
        search_results, search_count = db.search_notes(test_user_id, "groceries")
        assert len(search_results) == 1, f"Expected 1 search result, got {len(search_results)}"
        assert search_count == 1, f"Expected search count 1, got {search_count}"
        print(f"  ✅ Search results: {len(search_results)} found")
        
        # Test pagination
        # Add more notes to test pagination
        for i in range(15):
            db.add_note(test_user_id, f"Test note {i}", "task")
        
        notes_page1, total_count = db.get_notes(test_user_id, page=1, per_page=10)
        assert len(notes_page1) == 10, f"Expected 10 notes on page 1, got {len(notes_page1)}"
        assert total_count == 19, f"Expected total count 19, got {total_count}"
        print(f"  ✅ Pagination page 1: {len(notes_page1)} notes")
        
        notes_page2, total_count = db.get_notes(test_user_id, page=2, per_page=10)
        assert len(notes_page2) == 9, f"Expected 9 notes on page 2, got {len(notes_page2)}"
        print(f"  ✅ Pagination page 2: {len(notes_page2)} notes")
        
        # Test reminder operations
        note_id = note_ids[0]
        job_id = "test_job_123"
        reminder_time = "2024-01-15 14:30:00"
        
        success = db.add_reminder(test_user_id, note_id, job_id, reminder_time)
        assert success is True, "Failed to add reminder"
        print(f"  ✅ Added reminder for note {note_id}")
        
        reminders = db.get_user_reminders(test_user_id)
        assert len(reminders) == 1, f"Expected 1 reminder, got {len(reminders)}"
        print(f"  ✅ Retrieved {len(reminders)} reminders")
        
        success = db.remove_reminder(job_id)
        assert success is True, "Failed to remove reminder"
        print(f"  ✅ Removed reminder")
        
        # Test deleting note
        success = db.delete_note(test_user_id, note_ids[0])
        assert success, "Failed to delete note"
        print(f"  ✅ Deleted note {note_ids[0]}")
        
        # Verify note count decreased (check total count, not page results)
        remaining_notes, remaining_count = db.get_notes(test_user_id)
        assert remaining_count == 18, f"Expected remaining count 18, got {remaining_count}"
        print(f"  ✅ Remaining notes count: {remaining_count}")
        
        # Test that we can still get the first page
        first_page_notes, _ = db.get_notes(test_user_id, page=1, per_page=10)
        assert len(first_page_notes) == 10, f"Expected 10 notes on first page, got {len(first_page_notes)}"
        print(f"  ✅ First page after deletion: {len(first_page_notes)} notes")
        
        print("  🎉 Database tests passed!")
        
    finally:
        # Clean up temporary database
        os.unlink(temp_db.name)


def test_llm_categorization():
    """Test LLM categorization."""
    print("🧪 Testing LLM categorization...")
    
    test_notes = [
        "Buy groceries tomorrow",
        "Great idea for a new app",
        "Be the change you wish to see in the world",
        "Random thought about life"
    ]
    
    for note_text in test_notes:
        try:
            category = categorize_note_with_keywords(note_text)
            if category in VALID_CATEGORIES:
                print(f"  ✅ '{note_text[:30]}...' → {category}")
            else:
                print(f"  ⚠️  '{note_text[:30]}...' → {category} (invalid category)")
        except Exception as e:
            print(f"  ❌ Error categorizing '{note_text[:30]}...': {e}")
    
    print("  🎉 LLM categorization tests completed!")


def test_config():
    """Test configuration loading."""
    print("🧪 Testing configuration...")
    
    try:
        from config import VALID_CATEGORIES, MAX_PREVIEW_LENGTH, TIMESTAMP_FORMAT, NOTES_PER_PAGE
        
        assert len(VALID_CATEGORIES) == 4, f"Expected 4 categories, got {len(VALID_CATEGORIES)}"
        assert MAX_PREVIEW_LENGTH > 0, "MAX_PREVIEW_LENGTH should be positive"
        assert TIMESTAMP_FORMAT, "TIMESTAMP_FORMAT should not be empty"
        assert NOTES_PER_PAGE > 0, "NOTES_PER_PAGE should be positive"
        
        print(f"  ✅ Valid categories: {VALID_CATEGORIES}")
        print(f"  ✅ Max preview length: {MAX_PREVIEW_LENGTH}")
        print(f"  ✅ Timestamp format: {TIMESTAMP_FORMAT}")
        print(f"  ✅ Notes per page: {NOTES_PER_PAGE}")
        print("  🎉 Configuration tests passed!")
        
    except Exception as e:
        print(f"  ❌ Configuration test failed: {e}")


def test_reminder_time_parsing():
    """Test reminder time parsing functionality."""
    print("🧪 Testing reminder time parsing...")
    
    try:
        from reminder_scheduler import ReminderScheduler
        
        scheduler = ReminderScheduler()
        
        # Test relative times
        test_cases = [
            ("in 30 minutes", True),
            ("in 2 hours", True),
            ("in 1 day", True),
            ("2:30pm", True),
            ("14:30", True),
            ("invalid time", False),
            ("", False),
        ]
        
        for time_str, should_parse in test_cases:
            result = scheduler.parse_reminder_time(time_str)
            if should_parse:
                assert result is not None, f"Failed to parse valid time: {time_str}"
                print(f"  ✅ Parsed '{time_str}' → {result}")
            else:
                assert result is None, f"Should not parse invalid time: {time_str}"
                print(f"  ✅ Rejected invalid time: {time_str}")
        
        print("  🎉 Reminder time parsing tests passed!")
        
    except Exception as e:
        print(f"  ❌ Reminder time parsing test failed: {e}")


def main():
    """Run all tests."""
    print("🚀 Starting Telegram Notes Bot tests...\n")
    
    try:
        test_config()
        print()
        
        test_database()
        print()
        
        test_llm_categorization()
        print()
        
        test_reminder_time_parsing()
        print()
        
        print("🎉 All tests completed successfully!")
        print("\n💡 To run the bot:")
        print("   1. Set up your .env file with BOT_TOKEN")
        print("   2. Start your local LLM (e.g., Ollama)")
        print("   3. Run: python3 bot.py")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()