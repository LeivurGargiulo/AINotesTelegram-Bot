# Telegram Notes Bot

A smart Telegram bot that helps you organize your thoughts with automatic categorization using a local LLM. The bot can categorize notes into tasks, ideas, quotes, or other categories, and provides powerful search and management features.

## Features

- **Smart Note Categorization**: Automatically categorizes notes using a local LLM
- **Multiple Categories**: Supports task, idea, quote, and other categories
- **Search Functionality**: Find notes by keywords
- **User-Friendly Interface**: Clean, intuitive commands with helpful responses
- **Data Persistence**: SQLite database for reliable data storage
- **Error Handling**: Graceful error handling with user-friendly messages
- **Scalable Architecture**: Modular design for easy extension

## Commands

- `/start` - Welcome message
- `/help` - Show all available commands
- `/add <note text>` - Add a new note with automatic categorization
- `/list [category]` - List all notes or filter by category
- `/delete <note_id>` - Delete a note by ID
- `/search <keyword>` - Search notes by keyword

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
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram bot token (required) | - |
| `DATABASE_FILE` | SQLite database file path | `notes_bot.db` |
| `LLM_API_URL` | LLM API endpoint | `http://localhost:11434/api/generate` |
| `LLM_MODEL` | LLM model name | `llama2` |

### LLM Integration

The bot supports multiple LLM APIs:

1. **Ollama** (default): Uses the Ollama API format
2. **OpenAI-compatible**: Uses OpenAI-compatible API format

The bot will automatically try both formats and fall back to 'other' category if the LLM is unavailable.

## Project Structure

```
├── bot.py              # Main bot application
├── bot_handlers.py     # Command handlers
├── database.py         # Database operations
├── llm_client.py       # LLM integration
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
└── README.md          # This file
```

## Database Schema

The bot uses SQLite with the following schema:

```sql
CREATE TABLE notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    note_text TEXT NOT NULL,
    category TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

## Extending the Bot

The modular architecture makes it easy to add new features:

1. **Add new commands**: Create handlers in `bot_handlers.py`
2. **Add new LLM providers**: Extend `llm_client.py`
3. **Add new data fields**: Modify `database.py` schema
4. **Add scheduling**: Integrate with `apscheduler` or similar

### Example: Adding Reminder Functionality

```python
# In bot_handlers.py
async def set_reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Add reminder logic here
    pass

# In bot.py
application.add_handler(CommandHandler("remind", set_reminder_command))
```

## Troubleshooting

### Common Issues

1. **"BOT_TOKEN environment variable is required"**
   - Make sure you've created a `.env` file with your bot token
   - Verify the token is correct (get a new one from @BotFather if needed)

2. **"LLM categorization failed"**
   - Check if your local LLM is running
   - Verify the API URL and model name in `.env`
   - Check LLM logs for errors

3. **"Database error"**
   - Ensure the bot has write permissions in the directory
   - Check if the database file is corrupted (delete and restart)

4. **"Invalid category"**
   - The LLM returned an unexpected category
   - The bot will automatically fall back to 'other'

### Logs

The bot provides detailed logging. Check the console output for:
- Bot startup messages
- LLM API calls and responses
- Database operations
- Error details

## Security Considerations

- Keep your bot token secure and never commit it to version control
- The bot only stores notes for authenticated users
- Each user can only access their own notes
- Consider using environment variables for sensitive configuration

## Contributing

Feel free to submit issues, feature requests, or pull requests to improve the bot!

## License

This project is open source. Feel free to use and modify as needed.