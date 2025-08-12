# Enhanced Discord Notes Bot

A production-ready Discord bot for note-taking with automatic categorization, reminders, and advanced features. Built with security, performance, and scalability in mind.

## 🚀 Features

### Core Functionality
- **📝 Note Management**: Create, list, search, and delete notes
- **🏷️ Automatic Categorization**: Notes are automatically categorized as task, idea, quote, or other
- **🔍 Smart Search**: Search through your notes with keyword matching
- **⏰ Reminder System**: Set reminders for notes with flexible time formats
- **📊 User Statistics**: Track your note usage and activity

### Production Features
- **🔒 Security**: Rate limiting, user blocking, guild restrictions
- **⚡ Performance**: Connection pooling, caching, optimized queries
- **📈 Monitoring**: Health checks, performance metrics, error tracking
- **🛡️ Error Handling**: Comprehensive error handling and recovery
- **🔄 Graceful Shutdown**: Proper cleanup and resource management

### Advanced Capabilities
- **📄 Pagination**: Efficient handling of large note collections
- **💾 Caching**: Intelligent caching to reduce database load
- **🎯 Rate Limiting**: Per-user and per-command rate limiting
- **📊 Analytics**: Detailed performance and usage statistics
- **🔧 Configuration**: Environment-based configuration management

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- Discord Bot Token
- Git

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd discord-notes-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements_discord.txt
   ```

3. **Create environment file**
   ```bash
   cp .env.example .env
   ```

4. **Configure environment variables**
   ```bash
   # Required
   DISCORD_BOT_TOKEN=your_discord_bot_token_here
   
   # Optional (with defaults)
   DATABASE_FILE=notes_bot.db
   LOG_LEVEL=INFO
   LOG_FILE=discord_bot.log
   REMINDER_TIMEZONE=UTC
   RATE_LIMIT_ENABLED=true
   CACHE_ENABLED=true
   ```

5. **Run the bot**
   ```bash
   python discord_bot.py
   ```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DISCORD_BOT_TOKEN` | Required | Discord bot token |
| `DATABASE_FILE` | `notes_bot.db` | SQLite database file path |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FILE` | `discord_bot.log` | Log file path |
| `REMINDER_TIMEZONE` | `UTC` | Timezone for reminders |
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting |
| `RATE_LIMIT_BUCKET_SIZE` | `10` | Rate limit bucket size |
| `RATE_LIMIT_WINDOW` | `60` | Rate limit window in seconds |
| `CACHE_ENABLED` | `true` | Enable caching |
| `CACHE_TTL` | `300` | Cache TTL in seconds |
| `REMINDER_MAX_PER_USER` | `10` | Maximum reminders per user |
| `ALLOWED_GUILDS` | Empty | Comma-separated list of allowed guild IDs |
| `BLOCKED_USERS` | Empty | Comma-separated list of blocked user IDs |

### Command Cooldowns

| Command | Cooldown | Description |
|---------|----------|-------------|
| `add` | 5 seconds | Add new note |
| `list` | 3 seconds | List notes |
| `delete` | 3 seconds | Delete note |
| `search` | 3 seconds | Search notes |
| `remind` | 5 seconds | Set reminder |
| `reminders` | 3 seconds | List reminders |
| `status` | 10 seconds | Bot status |

## 📖 Usage

### Basic Commands

```
!start          - Welcome message and bot introduction
!help           - Show all available commands
!add <text>     - Add a new note with automatic categorization
!list           - List all your notes (paginated)
!list <category> - List notes from specific category
!delete <id>    - Delete a note by ID
!search <keyword> - Search notes containing keyword
!remind <id> <time> - Set a reminder for a note
!reminders      - List your scheduled reminders
!stats          - View your note statistics
!status         - Bot health and performance info
```

### Time Formats for Reminders

The bot supports various time formats:

- **Relative**: `in 30 minutes`, `in 2 hours`, `in 1 day`
- **Time**: `14:30`, `2:30pm`, `2:30 PM`
- **Date**: `2024-01-15`, `01/15/2024`
- **Natural**: `tomorrow`, `next week`

### Note Categories

Notes are automatically categorized based on keywords:

- **Task**: Contains words like "todo", "task", "buy", "meeting"
- **Idea**: Contains words like "idea", "think", "maybe", "could"
- **Quote**: Contains words like "said", "quote", "words"
- **Other**: Default category for other notes

## 🏗️ Architecture

### Core Components

1. **Discord Bot (`discord_bot.py`)**
   - Main bot application with health monitoring
   - Signal handling and graceful shutdown
   - Background task management

2. **Command Handlers (`discord_handlers.py`)**
   - All Discord command implementations
   - Error handling and user feedback
   - Performance monitoring integration

3. **Database (`database.py`)**
   - Connection pooling for performance
   - Caching layer with TTL
   - Optimized queries with indexes

4. **Rate Limiter (`rate_limiter.py`)**
   - Advanced rate limiting with sliding windows
   - Security middleware for user management
   - Suspicious activity tracking

5. **Reminder Scheduler (`discord_reminder_scheduler.py`)**
   - Robust reminder scheduling with error handling
   - Flexible time parsing
   - User limit management

6. **Logger (`logger.py`)**
   - Structured logging with performance tracking
   - Error tracking and statistics
   - Rotating log files

### Security Features

- **Rate Limiting**: Prevents abuse with configurable limits
- **User Blocking**: Block specific users from using the bot
- **Guild Restrictions**: Limit bot to specific Discord servers
- **Input Validation**: Comprehensive validation of all inputs
- **Error Handling**: Secure error messages without information leakage

### Performance Optimizations

- **Connection Pooling**: Efficient database connection management
- **Caching**: Intelligent caching with TTL and invalidation
- **Database Indexes**: Optimized queries for fast retrieval
- **Async Operations**: Non-blocking I/O operations
- **Resource Management**: Proper cleanup and memory management

## 📊 Monitoring and Health

### Health Checks

The bot includes comprehensive health monitoring:

- **Uptime Tracking**: Bot uptime and status
- **Latency Monitoring**: Discord API latency tracking
- **Error Tracking**: Error rates and types
- **Performance Metrics**: Operation timing and statistics
- **Resource Usage**: Memory and connection pool status

### Logging

Structured logging with multiple levels:

- **DEBUG**: Detailed debugging information
- **INFO**: General operational information
- **WARNING**: Warning conditions
- **ERROR**: Error conditions with context

### Status Command

Use `!status` to view:
- Bot uptime and latency
- Guild and user counts
- Recent performance metrics
- Error statistics
- Database status

## 🔍 Troubleshooting

### Common Issues

1. **Bot not responding**
   - Check if bot token is correct
   - Verify bot has proper permissions
   - Check logs for error messages

2. **Database errors**
   - Ensure database file is writable
   - Check disk space
   - Verify database permissions

3. **Rate limiting issues**
   - Check rate limit configuration
   - Monitor user activity
   - Adjust limits if needed

4. **Reminder not working**
   - Verify timezone configuration
   - Check reminder time format
   - Monitor scheduler logs

### Log Analysis

Check log files for:
- Error messages and stack traces
- Performance metrics
- User activity patterns
- System resource usage

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=.

# Run specific test file
pytest test_discord_bot.py
```

### Test Coverage

The bot includes tests for:
- Command functionality
- Database operations
- Rate limiting
- Error handling
- Performance monitoring

## 🚀 Deployment

### Production Deployment

1. **Environment Setup**
   ```bash
   # Set production environment variables
   export LOG_LEVEL=WARNING
   export RATE_LIMIT_ENABLED=true
   export CACHE_ENABLED=true
   ```

2. **Process Management**
   ```bash
   # Using systemd (Linux)
   sudo systemctl enable discord-notes-bot
   sudo systemctl start discord-notes-bot
   ```

3. **Monitoring**
   - Set up log rotation
   - Configure monitoring alerts
   - Monitor resource usage

### Docker Deployment

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements_discord.txt .
RUN pip install -r requirements_discord.txt

COPY . .
CMD ["python", "discord_bot.py"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Add docstrings for functions
- Include error handling
- Write comprehensive tests

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Check the troubleshooting section
- Review the logs for error messages
- Open an issue on GitHub
- Check the documentation

## 🔄 Changelog

### Version 2.0.0 (Enhanced)
- Complete rewrite with production features
- Enhanced security and rate limiting
- Performance optimizations and caching
- Comprehensive monitoring and health checks
- Improved error handling and logging
- Modular architecture for maintainability

### Version 1.0.0 (Original)
- Basic note management functionality
- Simple reminder system
- Discord integration