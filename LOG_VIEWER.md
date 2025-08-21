# 📊 Soft Terminal Log Viewer

## Overview
The Soft Terminal LLM now includes a comprehensive log viewer to track and analyze all conversations. This viewer provides insights into usage patterns and conversation history.

## Features

### 📈 Statistics Dashboard
- **Total Conversations**: Overall count of all Q&A exchanges
- **Today's Conversations**: Count of conversations from the current day
- **Unique Sessions**: Number of distinct user sessions
- **Average Response Length**: Mean character count of responses

### 🔍 Filtering Options
- **Date Filter**: Select specific date for viewing logs
- **Session Filter**: Search by session ID
- **Language Filter**: Filter by language (pt, pt-PT, en)
- **Search**: Full-text search across questions and responses

### 📝 Log Display
Each log entry shows:
- Timestamp with date and time
- Session ID for tracking conversations
- Question asked by the user
- Complete response from the assistant
- Metadata (language, response length, day of week)

## Access

### Web Interface
Navigate to: `http://localhost:8000/logs`

### API Endpoint
Raw JSON data: `http://localhost:8000/logs-data`

## Log Storage

Logs are stored in JSONL format at:
- Docker: `/app/logs/conversations_YYYYMMDD.jsonl`
- Host: `./logs/conversations_YYYYMMDD.jsonl`

Each line contains a JSON object with:
```json
{
  "session_id": "unique-id",
  "timestamp": "ISO-8601 timestamp",
  "day_of_week": "weekday name",
  "time_of_day": "HH:MM:SS",
  "language": "detected language",
  "question": "user's question",
  "response": "assistant's response",
  "response_length": 123,
  "question_length": 45
}
```

## Features

### Auto-refresh
The viewer automatically refreshes every 30 seconds to show new conversations.

### Responsive Design
The interface adapts to different screen sizes, from desktop to mobile.

### Real-time Updates
As new conversations happen in the main app, they appear in the log viewer after the next refresh.

## Use Cases

1. **Monitoring Usage**: Track how many conversations are happening daily
2. **Quality Assurance**: Review responses for appropriateness and accuracy
3. **Pattern Analysis**: Identify common questions and topics
4. **Session Tracking**: Follow a specific user's conversation flow
5. **Language Distribution**: See which languages are being used

## Technical Details

- Built with vanilla JavaScript for simplicity
- No external dependencies required
- Follows the Daylight Canvas design theme
- Uses the same Lexend font family as the main app
- Implements efficient filtering without page reloads