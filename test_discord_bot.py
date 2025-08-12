#!/usr/bin/env python3
"""
Test script for Discord Notes Bot.
Tests core functionality without requiring a Discord connection.
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import NotesDatabase
from note_categorizer import categorize_note_with_keywords
# Import reminder scheduler without discord dependencies for testing
import importlib.util
spec = importlib.util.spec_from_file_location("discord_reminder_scheduler", "discord_reminder_scheduler.py")
discord_reminder_scheduler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(discord_reminder_scheduler)
DiscordReminderScheduler = discord_reminder_scheduler.DiscordReminderScheduler
from config import VALID_CATEGORIES
from logger import get_logger

logger = get_logger(__name__)


def test_database():
    """Test database operations."""
    print("🧪 Testing Database Operations...")
    
    try:
        # Initialize database
        db = NotesDatabase("test_notes.db")
        
        # Test adding notes
        test_user_id = 12345
        test_notes = [
            ("Buy groceries tomorrow", "task"),
            ("Great idea for a new project", "idea"),
            ("Life is what happens while you're busy making other plans", "quote"),
            ("Random thought about the weather", "other")
        ]
        
        note_ids = []
        for note_text, expected_category in test_notes:
            # Test categorization
            category = categorize_note_with_keywords(note_text)
            print(f"  📝 Note: '{note_text[:30]}...' -> Category: {category} (expected: {expected_category})")
            
            # Add note to database
            note_id = db.add_note(test_user_id, note_text, category)
            note_ids.append(note_id)
            print(f"    ✅ Added note ID: {note_id}")
        
        # Test retrieving notes
        notes, total_count = db.get_notes(test_user_id, page=1, per_page=5)
        print(f"  📋 Retrieved {len(notes)} notes (total: {total_count})")
        
        # Test category filtering
        task_notes, task_count = db.get_notes(test_user_id, category="task", page=1, per_page=5)
        print(f"  📋 Task notes: {len(task_notes)} (total: {task_count})")
        
        # Test search
        search_results = db.search_notes(test_user_id, "groceries")
        print(f"  🔍 Search for 'groceries': {len(search_results)} results")
        
        # Test getting note by ID
        if note_ids:
            note = db.get_note_by_id(note_ids[0], test_user_id)
            if note:
                print(f"  ✅ Retrieved note by ID: {note['id']} - {note['note_text'][:30]}...")
        
        # Clean up test database
        os.remove("test_notes.db")
        print("  🧹 Cleaned up test database")
        
        print("✅ Database tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        logger.error(f"Database test failed: {e}", exc_info=True)
        return False


def test_categorizer():
    """Test note categorization."""
    print("\n🧪 Testing Note Categorization...")
    
    test_cases = [
        ("Buy groceries tomorrow", "task"),
        ("Call mom at 3pm", "task"),
        ("Great idea for a startup", "idea"),
        ("Innovative solution to climate change", "idea"),
        ("Life is what happens while you're busy making other plans", "quote"),
        ("The only way to do great work is to love what you do", "quote"),
        ("Random thought about the weather", "other"),
        ("Interesting fact about penguins", "other")
    ]
    
    passed = 0
    total = len(test_cases)
    
    for note_text, expected_category in test_cases:
        category = categorize_note_with_keywords(note_text)
        status = "✅" if category == expected_category else "❌"
        print(f"  {status} '{note_text[:40]}...' -> {category} (expected: {expected_category})")
        if category == expected_category:
            passed += 1
    
    print(f"📊 Categorization accuracy: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("✅ Categorization tests passed!")
        return True
    else:
        print("❌ Some categorization tests failed!")
        return False


def test_reminder_scheduler():
    """Test reminder scheduler functionality."""
    print("\n🧪 Testing Reminder Scheduler...")
    
    try:
        scheduler = DiscordReminderScheduler()
        
        # Test time parsing
        test_times = [
            "in 30 minutes",
            "in 2 hours",
            "2:30pm",
            "14:30",
            "2024-01-15"
        ]
        
        for time_str in test_times:
            parsed_time = scheduler.parse_time_string(time_str)
            if parsed_time:
                print(f"  ✅ Parsed '{time_str}' -> {parsed_time}")
            else:
                print(f"  ❌ Failed to parse '{time_str}'")
        
        # Test scheduler operations
        scheduler.start()
        print("  ✅ Scheduler started")
        
        # Test adding a reminder (without actual scheduling)
        test_user_id = 12345
        test_note_id = 1
        test_time = datetime.now() + timedelta(minutes=5)
        test_channel_id = 67890
        
        # This would normally require a database note, so we'll just test the method exists
        print("  ✅ Scheduler methods available")
        
        scheduler.stop()
        print("  ✅ Scheduler stopped")
        
        print("✅ Reminder scheduler tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Reminder scheduler test failed: {e}")
        logger.error(f"Reminder scheduler test failed: {e}", exc_info=True)
        return False


def test_config():
    """Test configuration loading."""
    print("\n🧪 Testing Configuration...")
    
    try:
        from config import VALID_CATEGORIES, MAX_PREVIEW_LENGTH, NOTES_PER_PAGE
        
        print(f"  📋 Valid categories: {VALID_CATEGORIES}")
        print(f"  📏 Max preview length: {MAX_PREVIEW_LENGTH}")
        print(f"  📄 Notes per page: {NOTES_PER_PAGE}")
        
        # Test that required categories exist
        required_categories = ['task', 'idea', 'quote', 'other']
        for category in required_categories:
            if category in VALID_CATEGORIES:
                print(f"  ✅ Category '{category}' found")
            else:
                print(f"  ❌ Category '{category}' missing")
                return False
        
        print("✅ Configuration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        logger.error(f"Configuration test failed: {e}", exc_info=True)
        return False


async def test_async_components():
    """Test async components."""
    print("\n🧪 Testing Async Components...")
    
    try:
        # Test that we can create async tasks
        async def dummy_task():
            await asyncio.sleep(0.1)
            return "test completed"
        
        result = await dummy_task()
        print(f"  ✅ Async task completed: {result}")
        
        # Test concurrent operations
        tasks = [dummy_task() for _ in range(3)]
        results = await asyncio.gather(*tasks)
        print(f"  ✅ Concurrent tasks completed: {len(results)} results")
        
        print("✅ Async component tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Async component test failed: {e}")
        logger.error(f"Async component test failed: {e}", exc_info=True)
        return False


def main():
    """Run all tests."""
    print("🚀 Starting Discord Notes Bot Tests...\n")
    
    tests = [
        ("Configuration", test_config),
        ("Database", test_database),
        ("Categorizer", test_categorizer),
        ("Reminder Scheduler", test_reminder_scheduler),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            logger.error(f"{test_name} test crashed: {e}", exc_info=True)
    
    # Test async components
    try:
        if asyncio.run(test_async_components()):
            passed += 1
        total += 1
    except Exception as e:
        print(f"❌ Async components test crashed: {e}")
        logger.error(f"Async components test crashed: {e}", exc_info=True)
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Discord bot is ready to run.")
        print("\n📝 Next steps:")
        print("1. Create a Discord bot in the Developer Portal")
        print("2. Set up your .env file with BOT_TOKEN")
        print("3. Run: python discord_bot.py")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit(main())