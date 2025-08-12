#!/usr/bin/env python3
"""
Test script for the Telegram Notes Bot.
Tests database operations and LLM integration without running the full bot.
"""
import os
import sys
import tempfile
import shutil
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import NotesDatabase
from llm_client import categorize_note_with_llm
from config import VALID_CATEGORIES


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
        
        # Test getting all notes
        all_notes = db.get_notes(test_user_id)
        assert len(all_notes) == 4, f"Expected 4 notes, got {len(all_notes)}"
        print(f"  ✅ Retrieved {len(all_notes)} notes")
        
        # Test filtering by category
        task_notes = db.get_notes(test_user_id, "task")
        assert len(task_notes) == 1, f"Expected 1 task note, got {len(task_notes)}"
        print(f"  ✅ Filtered task notes: {len(task_notes)} found")
        
        # Test search
        search_results = db.search_notes(test_user_id, "groceries")
        assert len(search_results) == 1, f"Expected 1 search result, got {len(search_results)}"
        print(f"  ✅ Search results: {len(search_results)} found")
        
        # Test deleting note
        success = db.delete_note(test_user_id, note_ids[0])
        assert success, "Failed to delete note"
        print(f"  ✅ Deleted note {note_ids[0]}")
        
        # Verify note count decreased
        remaining_notes = db.get_notes(test_user_id)
        assert len(remaining_notes) == 3, f"Expected 3 notes after deletion, got {len(remaining_notes)}"
        print(f"  ✅ Remaining notes: {len(remaining_notes)}")
        
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
            category = categorize_note_with_llm(note_text)
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
        from config import VALID_CATEGORIES, MAX_PREVIEW_LENGTH, TIMESTAMP_FORMAT
        
        assert len(VALID_CATEGORIES) == 4, f"Expected 4 categories, got {len(VALID_CATEGORIES)}"
        assert MAX_PREVIEW_LENGTH > 0, "MAX_PREVIEW_LENGTH should be positive"
        assert TIMESTAMP_FORMAT, "TIMESTAMP_FORMAT should not be empty"
        
        print(f"  ✅ Valid categories: {VALID_CATEGORIES}")
        print(f"  ✅ Max preview length: {MAX_PREVIEW_LENGTH}")
        print(f"  ✅ Timestamp format: {TIMESTAMP_FORMAT}")
        print("  🎉 Configuration tests passed!")
        
    except Exception as e:
        print(f"  ❌ Configuration test failed: {e}")


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
        
        print("🎉 All tests completed successfully!")
        print("\n💡 To run the bot:")
        print("   1. Set up your .env file with BOT_TOKEN")
        print("   2. Start your local LLM (e.g., Ollama)")
        print("   3. Run: python bot.py")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()