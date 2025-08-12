# Discord Notes Bot

A feature-rich Discord bot for organizing and managing personal notes with automatic categorization, reminders, and search functionality. This bot was converted from a Telegram bot to work seamlessly with Discord's API.

## Features

- 📝 **Note Management**: Add, list, delete, and search notes
- 🏷️ **Automatic Categorization**: Notes are automatically categorized as task, idea, quote, or other
- ⏰ **Reminders**: Set reminders for notes with flexible time formats
- 🔍 **Search**: Find notes by keywords
- 📊 **Pagination**: Browse notes with paginated results
- 🛡️ **User Isolation**: Each user's notes are completely private
- 📈 **Debug Tools**: Monitor bot status and performance

## Commands

| Command | Description | Example |
|---------|-------------|---------|
| `!start` | Welcome message and bot introduction | `!start` |
| `!help` | Show all available commands | `!help` |
| `!add <text>` | Add a new note | `!add Buy groceries tomorrow` |
| `!list [category]` | List all notes or filter by category | `!list task` |
| `!delete <id>` | Delete a note by ID | `!delete 5` |
| `!search <keyword>` | Search notes by keyword | `!search meeting` |
| `!remind <id> <time>` | Set a reminder for a note | `!remind 5 in 2 hours` |
| `!reminders` | List all scheduled reminders | `!reminders` |
| `!debug` | Show bot status and debug info | `!debug` |

### Categories
- `task` - Tasks and to-dos
- `idea` - Ideas and concepts
- `quote` - Quotes and references
- `other` - Miscellaneous notes

### Time Formats for Reminders
- Relative: `in 30 minutes`, `in 2 hours`, `in 1 day`
- Time: `2:30pm`, `14:30`
- Date: `2024-01-15`, `01/15/2024`

## Setup Instructions

### 1. Prerequisites
- Python 3.8 or higher
- A Discord bot token
- Discord server where you have admin permissions

### 2. Create a Discord Bot
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to the "Bot" section and click "Add Bot"
4. Copy the bot token (you'll need this later)
5. Under "Privileged Gateway Intents", enable:
   - Message Content Intent
   - Server Members Intent

### 3. Install Dependencies
```bash
pip install -r requirements_discord.txt
```

### 4. Environment Configuration
Create a `.env` file in the project root:
```env
BOT_TOKEN=your_discord_bot_token_here
DATABASE_FILE=discord_notes_bot.db
LOG_LEVEL=INFO
LOG_FILE=discord_bot.log
REMINDER_TIMEZONE=UTC
```

### 5. Invite Bot to Server
1. Go to OAuth2 > URL Generator in the Discord Developer Portal
2. Select "bot" under scopes
3. Select the following permissions:
   - Send Messages
   - Use Slash Commands
   - Read Message History
   - Add Reactions
   - Embed Links
4. Use the generated URL to invite the bot to your server

### 6. Run the Bot
```bash
python discord_bot.py
```

## Architecture

### File Structure
```
├── discord_bot.py              # Main bot entry point
├── discord_handlers.py         # Command handlers and logic
├── discord_reminder_scheduler.py # Reminder scheduling system
├── database.py                 # Database operations
├── note_categorizer.py         # Note categorization logic
├── config.py                   # Configuration settings
├── logger.py                   # Logging setup
├── requirements_discord.txt    # Python dependencies
└── README_DISCORD.md          # This file
```

### Key Components

#### Discord Bot (`discord_bot.py`)
- Bot initialization and configuration
- Event handling setup
- Global error handling
- Graceful shutdown

#### Command Handlers (`discord_handlers.py`)
- All Discord commands using `@bot.command()` decorators
- Rich embed responses for better UX
- Command cooldowns and rate limiting
- Comprehensive error handling

#### Reminder Scheduler (`discord_reminder_scheduler.py`)
- Async task scheduling using APScheduler
- Flexible time parsing for reminders
- Discord channel-based reminder delivery
- Persistent reminder storage

#### Database (`database.py`)
- SQLite database for note storage
- User isolation and data privacy
- Efficient pagination and search
- Reminder tracking

## Conversion Notes

This Discord bot was converted from a Telegram bot with the following key adaptations:

### Command System
- **Telegram**: `/command` format with `CommandHandler`
- **Discord**: `!command` format with `@bot.command()` decorators

### Message Handling
- **Telegram**: `Update` and `ContextTypes` objects
- **Discord**: `Context` objects with `ctx.send()`

### UI Elements
- **Telegram**: Inline keyboards and Markdown formatting
- **Discord**: Rich embeds with fields and colors

### Reminders
- **Telegram**: Direct message to user
- **Discord**: Channel-based delivery with embed formatting

### Error Handling
- **Telegram**: Global error handler with `add_error_handler`
- **Discord**: `on_command_error` event with comprehensive error types

## Development

### Adding New Commands
1. Add the command function in `discord_handlers.py`
2. Use the `@bot.command()` decorator
3. Add cooldown if needed: `@cooldown(1, 5, BucketType.user)`
4. Use embeds for rich responses
5. Add proper error handling

### Testing
```bash
# Run tests
pytest

# Run with async support
pytest --asyncio-mode=auto
```

### Logging
The bot uses structured logging with different levels:
- `INFO`: General bot activity
- `WARNING`: Non-critical issues
- `ERROR`: Command failures and exceptions
- `DEBUG`: Detailed debugging information

## Deployment

### Local Development
```bash
python discord_bot.py
```

### Production Deployment
1. Set up a VPS or cloud server
2. Install Python and dependencies
3. Set environment variables
4. Use a process manager like `systemd` or `supervisor`
5. Set up logging rotation

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements_discord.txt .
RUN pip install -r requirements_discord.txt

COPY . .
CMD ["python", "discord_bot.py"]
```

## Troubleshooting

### Common Issues

1. **Bot not responding**
   - Check if bot token is correct
   - Verify bot has proper permissions
   - Check logs for error messages

2. **Commands not working**
   - Ensure bot has "Message Content Intent" enabled
   - Check command prefix (default: `!`)
   - Verify bot is online

3. **Reminders not sending**
   - Check timezone configuration
   - Verify APScheduler is running
   - Check channel permissions

4. **Database errors**
   - Ensure write permissions to database file
   - Check database file path in config
   - Verify SQLite is working

### Debug Commands
- Use `!debug` to check bot status
- Check logs for detailed error information
- Monitor bot uptime and performance

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for error details
3. Open an issue on GitHub with detailed information