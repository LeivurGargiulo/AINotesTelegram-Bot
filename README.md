# Telegram Notes Bot

A smart Telegram bot that helps you organize your thoughts with automatic categorization using a local LLM. The bot can categorize notes into tasks, ideas, quotes, or other categories, and provides powerful search, pagination, and reminder features.

## Features

- **Smart Note Categorization**: Automatically categorizes notes using a local LLM
- **Multiple Categories**: Supports task, idea, quote, and other categories
- **Pagination Support**: Navigate through large numbers of notes with inline buttons
- **Search Functionality**: Find notes by keywords with pagination
- **Reminder System**: Set reminders for notes with flexible time formats
- **Structured Logging**: Comprehensive logging with different levels and file rotation
- **User-Friendly Interface**: Clean, intuitive commands with helpful responses
- **Data Persistence**: SQLite database for reliable data storage
- **Error Handling**: Graceful error handling with user-friendly messages
- **Scalable Architecture**: Modular design for easy extension
- **Comprehensive Testing**: Unit tests for all major functionality

## Commands

- `/start` - Welcome message
- `/help` - Show all available commands
- `/add <note text>` - Add a new note with automatic categorization
- `/list [category]` - List all notes or filter by category (paginated)
- `/delete <note_id>` - Delete a note by ID
- `/search <keyword>` - Search notes by keyword (paginated)
- `/remind <note_id> <time>` - Set a reminder for a note
- `/reminders` - List your scheduled reminders

## Prerequisites

1. **Python 3.8+**
2. **Telegram Bot Token** (get from [@BotFather](https://t.me/BotFather))
3. **Local LLM** (Ollama, local OpenAI-compatible API, etc.)

## Installation

1. **Clone or download the project files**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your Telegram bot token:
   ```
   BOT_TOKEN=your_actual_bot_token_here
   ```

4. **Set up a local LLM** (choose one option):

   **Option A: Ollama (Recommended)**
   ```bash
   # Install Ollama
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Pull a model (e.g., llama2)
   ollama pull llama2
   
   # Start Ollama service
   ollama serve
   ```

   **Option B: Other local LLM**
   - Set up any OpenAI-compatible API locally
   - Update `LLM_API_URL` in your `.env` file
   - Update `LLM_MODEL` to match your model name

## Usage

1. **Start the bot**:
   ```bash
   python bot.py
   ```

2. **Find your bot on Telegram** and start chatting!

3. **Example usage**:
   ```
   /add Buy groceries tomorrow
   /add Great idea for a new app
   /add "Be the change you wish to see in the world" - Gandhi
   /list
   /list task
   /search meeting
   /delete 5
   /remind 5 in 2 hours
   /reminders
   ```

## New Features

### Pagination
- Notes are displayed in pages of 10 items each
- Use inline "Previous" and "Next" buttons to navigate
- Works with both `/list` and `/search` commands
- Shows current page and total count

### Reminder System
- Set reminders for any note using `/remind <note_id> <time>`
- Supports multiple time formats:
  - Relative: `in 30 minutes`, `in 2 hours`, `in 1 day`
  - Absolute time: `2:30pm`, `14:30`
  - Specific date: `2024-01-15`
- View all scheduled reminders with `/reminders`
- Automatic reminder delivery via Telegram messages

### Structured Logging
- Configurable log levels (DEBUG, INFO, WARNING, ERROR)
- Log rotation with file size limits
- Separate console and file logging
- Detailed logging for all major operations

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram bot token (required) | - |
| `DATABASE_FILE` | SQLite database file path | `notes_bot.db` |
| `LLM_API_URL` | LLM API endpoint | `http://localhost:11434/api/generate` |
| `LLM_MODEL` | LLM model name | `llama2` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `LOG_FILE` | Log file path | `bot.log` |
| `REMINDER_TIMEZONE` | Timezone for reminders | `UTC` |

### LLM Integration

The bot supports multiple LLM APIs:

**Ollama API** (default):
- Endpoint: `http://localhost:11434/api/generate`
- Models: llama2, mistral, codellama, etc.

**OpenAI-compatible API**:
- Endpoint: `http://localhost:8000/v1/chat/completions`
- Models: Any OpenAI-compatible model

The bot automatically tries different API formats and falls back to 'other' category if LLM is unavailable.

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
python test_bot.py

# Run with pytest (if installed)
pytest test_bot.py -v
```

The test suite covers:
- Database operations (CRUD, pagination, search)
- LLM client functionality and fallback logic
- Reminder scheduler operations
- Integration tests for complete workflows

## Project Structure

```
├── bot.py                 # Main bot application
├── bot_handlers.py        # Command handlers and business logic
├── database.py           # Database operations and models
├── llm_client.py         # LLM integration and categorization
├── reminder_scheduler.py # Reminder scheduling functionality
├── logger.py             # Structured logging configuration
├── config.py             # Configuration settings
├── test_bot.py           # Comprehensive test suite
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variables template
└── README.md             # This file
```

## Dependencies

- `python-telegram-bot==20.7` - Telegram Bot API wrapper
- `requests==2.31.0` - HTTP requests for LLM API
- `python-dotenv==1.0.0` - Environment variable management
- `APScheduler==3.10.4` - Task scheduling for reminders
- `pytest==7.4.3` - Testing framework
- `pytest-asyncio==0.21.1` - Async testing support

## Troubleshooting

### Common Issues

1. **Bot not responding**:
   - Check if `BOT_TOKEN` is set correctly in `.env`
   - Verify the bot is running with `python bot.py`

2. **LLM categorization not working**:
   - Ensure your local LLM is running
   - Check `LLM_API_URL` and `LLM_MODEL` in `.env`
   - The bot will fall back to 'other' category if LLM is unavailable

3. **Reminders not working**:
   - Check if the bot is running continuously
   - Verify `REMINDER_TIMEZONE` is set correctly
   - Check logs for scheduler errors

4. **Database errors**:
   - Ensure write permissions for the database file
   - Check `DATABASE_FILE` path in `.env`

### Logs

Check the log file (default: `bot.log`) for detailed information:
```bash
tail -f bot.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is open source and available under the MIT License.