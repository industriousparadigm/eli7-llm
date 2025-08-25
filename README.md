# 🌟 Soft Terminal LLM

A gentle, kid-friendly AI conversational interface designed specifically for 7-year-olds, running on Raspberry Pi 5.

## 🎯 Purpose

This application provides a safe, educational, and engaging way for young children to interact with AI. It features:
- Age-appropriate responses using simple language
- Portuguese (PT-PT) interface for native speakers
- Beautiful, calming "Daylight Canvas" design
- Conversation monitoring and logging for parents/educators

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Anthropic API key (for Claude Sonnet 4)
- 8GB RAM minimum (designed for Raspberry Pi 5)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/soft-terminal-llm.git
cd soft-terminal-llm
```

2. Create a `.env` file in the root directory:
```bash
ANTHROPIC_API_KEY=your-api-key-here
```

3. Start the application:
```bash
docker-compose up -d
```

4. Access the application:
- **Main App**: http://localhost:5173 (Note: UI runs on Vite port)
- **Log Viewer**: http://localhost:8000/logs
- **API Docs**: http://localhost:8000/docs

## 🍓 Raspberry Pi Deployment

### One-Command Deploy from Mac/Linux

After initial Pi setup, deploy changes with:
```bash
./deploy-to-pi.sh
```

This script:
- Syncs code to Pi (excluding node_modules)
- Copies production environment (.env.production → .env)
- Installs dependencies
- Restarts all services
- Shows access URLs and log commands

### Initial Pi Setup

1. **Flash Raspberry Pi OS** using Raspberry Pi Imager:
   - Choose Raspberry Pi OS Lite (64-bit)
   - Configure WiFi, SSH, and user in settings
   - Username: diogo, Password: diogo (or your preference)

2. **SSH into Pi and run setup**:
```bash
ssh diogo@192.168.1.100
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs xorg openbox chromium-browser fonts-noto-color-emoji
```

3. **Deploy the app**:
```bash
# On your Mac:
./deploy-to-pi.sh
```

4. **Display on Pi Screen** (optional):
```bash
# On Pi:
~/soft-terminal-llm/launch-browser.sh
```

### Production Environment

Create `.env.production` (gitignored) with your secrets:
```bash
# Production environment variables for Raspberry Pi
ANTHROPIC_API_KEY=your-actual-api-key
API_PORT=8000
UI_PORT=5173
TEMPERATURE=0.7
MAX_TOKENS=1500
```

## 🏗️ Architecture

```
soft-terminal-llm/
├── api/                    # FastAPI backend
│   ├── main.py            # API endpoints & log viewer
│   ├── llm_interface.py   # Anthropic Claude integration
│   ├── prompts.py         # System prompts
│   └── models.py          # Data models
├── ui/                     # React frontend
│   ├── src/
│   │   ├── App.jsx        # Main application
│   │   ├── App.css        # Daylight Canvas styling
│   │   └── copy.js        # Portuguese translations
│   └── package.json       # Dependencies
├── logs/                   # Conversation logs (auto-created)
├── docker-compose.yml      # Container orchestration
└── .env                   # Environment variables
```

## 🎨 Features

### For Kids
- **Simple Interface**: One input field, clear responses
- **Visual Feedback**: Loading animations, smooth transitions
- **Portuguese Language**: Native PT-PT interface
- **Safe Responses**: Age-appropriate content only
- **Easy Reset**: "Nova conversa" button to start fresh

### For Parents/Educators
- **Conversation Logs**: All interactions are logged
- **Log Viewer**: Web interface to review conversations
- **Statistics**: Track usage patterns and engagement
- **Filtering**: Search and filter logs by date, session, content
- **Export Ready**: JSONL format for data analysis

## 🔧 Configuration

### Environment Variables
```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional
API_PORT=8000
UI_PORT=3000
LOG_LEVEL=INFO
```

### System Requirements
- **Minimum**: 4GB RAM, 2 CPU cores
- **Recommended**: 8GB RAM, 4 CPU cores (Raspberry Pi 5)
- **Storage**: 1GB for application + logs

## 📊 Log Viewer

Access detailed conversation analytics at `/logs`:

- **Total Conversations**: Overall interaction count
- **Today's Activity**: Daily usage tracking
- **Session Management**: Track individual users
- **Response Analysis**: Average response lengths
- **Search & Filter**: Find specific conversations
- **Auto-refresh**: Real-time updates every 30 seconds

## 🛠️ Development

### Local Development Setup

1. Backend:
```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

2. Frontend:
```bash
cd ui
npm install
npm run dev
```

### Testing

Run the comprehensive test suite:
```bash
./test_system.sh
```

This verifies:
- API health
- Session management
- Markdown formatting
- Log endpoints
- UI accessibility

## 🐛 Troubleshooting

### Common Issues

**API Key Error**
```
Error: ANTHROPIC_API_KEY not found
Solution: Ensure .env file exists with valid API key
```

**Container Won't Start**
```
Error: Port already in use
Solution: Change ports in docker-compose.yml or stop conflicting services
```

**No Responses**
```
Error: Request timeout
Solution: Check internet connection and API key validity
```

### Logs Location
- Application logs: `docker-compose logs -f api`
- Conversation logs: `./logs/conversations_*.jsonl`

## 📝 API Documentation

### Core Endpoints

#### POST /ask
Submit a question and receive a response
```json
{
  "question": "Como funcionam os arco-íris?",
  "history": [],
  "session_id": "unique-id"
}
```

#### GET /new-session
Create a new conversation session
```json
{
  "session_id": "generated-uuid"
}
```

#### GET /logs
View the web-based log viewer interface

#### GET /logs-data
Retrieve raw log data in JSON format

Full API documentation available at `/docs` when running.

## 🌍 Language Support

Currently supports:
- **Portuguese (PT-PT)**: Primary interface language
- **English**: API responses adapt to question language

## 🔒 Security & Privacy

- All conversations are logged locally
- No data is sent to external services except Anthropic API
- Logs are stored in JSONL format for easy audit
- Session IDs are randomly generated UUIDs
- No personal information is collected

## 🤝 Contributing

We welcome contributions! Please ensure:
1. Code follows existing patterns
2. Portuguese translations are included
3. Features are kid-appropriate
4. Tests pass before submitting PR

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- **Anthropic Claude**: For powering intelligent, safe responses
- **Lexend Font**: For improved readability
- **Daylight Canvas Design**: For the calming visual aesthetic
- **React & FastAPI**: For the robust application framework

## 📞 Support

For issues or questions:
- Create an issue on GitHub
- Check logs at `/logs` for conversation history
- Review API docs at `/docs` for technical details

---

Built with ❤️ for curious young minds