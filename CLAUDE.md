# 🤖 CLAUDE.md - AI Assistant Context Guide

## Welcome, Future Claude!

This document provides essential context for understanding and working with the Soft Terminal LLM codebase. Please read this before making any changes.

## 🎯 Product Vision & Intent

### Core Mission
Create a **safe, engaging, and educational** conversational AI experience for 7-year-old children, specifically designed for deployment on Raspberry Pi 5 in Portuguese-speaking households.

### Key Design Decisions

1. **Target Audience**: 7-year-old Portuguese-speaking children
2. **Hardware**: Raspberry Pi 5 with 8GB RAM (WiFi-enabled)
3. **Language Model**: Anthropic Claude Sonnet 4 (via API)
4. **UI Language**: Portuguese (PT-PT) - all interface text
5. **Response Language**: Adapts to question language (PT/EN)

### Product Philosophy
- **NOT prescriptive**: Let Claude naturally generate age-appropriate responses
- **NOT limiting**: No artificial 2-sentence limits or overly strict constraints
- **YES natural**: Trust Claude's ability to communicate with children
- **YES flexible**: Allow varied response lengths based on context

## 🏗️ Technical Architecture

### Current Stack
```
Frontend: React + Vite + ReactMarkdown
Backend: FastAPI + Anthropic API
Database: None (stateless, logs to JSONL)
Container: Docker Compose
Deployment: Raspberry Pi 5
```

### Critical Implementation Details

#### 1. Markdown Rendering (CRUCIAL)
- **Frontend uses ReactMarkdown** - NOT dangerouslySetInnerHTML
- **Backend returns raw markdown** - NO HTML conversion
- **Lists MUST use line breaks** - Each bullet on its own line
- **CSS handles all styling** - Via `.markdown-content` classes
- **IMPORTANT**: ReactMarkdown does NOT accept className prop - apply classes to parent div

#### 2. Session Management
- Sessions are UUID-based
- Conversation history maintains 6 messages (3 exchanges)
- Each session logged to JSONL files
- Reset button creates new session

#### 3. API Integration
- Uses Anthropic's async client
- Model: `claude-3-5-sonnet-20241022` (Sonnet 4 model ID)
- Temperature: 0.7 for creativity
- Max tokens: 300 for appropriate response length

#### 4. Logging System
- Format: JSONL (one JSON object per line)
- Location: `./logs/conversations_YYYYMMDD.jsonl`
- Includes: timestamp, session_id, Q&A, metadata
- Viewer: Available at `/logs` endpoint

## 📁 Key Files to Understand

### Backend (`/api`)
- **main.py**: Core API endpoints, session management, logging, log viewer
- **llm_interface.py**: Anthropic integration, response generation
- **prompts.py**: System prompts with formatting rules
- **models.py**: Pydantic models for API contracts

### Frontend (`/ui`)
- **App.jsx**: Main component with ReactMarkdown, session logic
- **App.css**: Daylight Canvas theme implementation
- **copy.js**: Portuguese translations (PT-PT)
- **package.json**: Dependencies including react-markdown

### Configuration
- **docker-compose.yml**: Service orchestration, volume mounts
- **.env**: API keys and configuration

## 🚨 Common Pitfalls & Solutions

### 1. Formatting Issues
**Problem**: Lists/paragraphs not rendering properly
**Solution**: Ensure backend returns raw markdown with proper line breaks

### 2. API Key Errors
**Problem**: Anthropic API key not found
**Solution**: Check `.env` file and docker-compose env_file configuration

### 3. Session Context Lost
**Problem**: Bot doesn't remember previous messages
**Solution**: Verify history array is being passed in API calls

### 4. UI Not Updating
**Problem**: Changes not reflected in browser
**Solution**: Frontend uses Vite HMR - check port 3000, not 5173

### 5. Logs Not Appearing
**Problem**: Conversation logs empty
**Solution**: Check volume mount in docker-compose, verify write permissions

## 🎨 Design System: Daylight Canvas

### Visual Principles
- **Gradients**: Soft blue-to-white backgrounds
- **Typography**: Lexend font for readability
- **Colors**: Calming blues and greens
- **Animations**: Subtle, non-distracting
- **Spacing**: Generous padding for clarity

### Component Patterns
- **Loading**: Three bouncing dots
- **Buttons**: Rounded, elevated on hover
- **Messages**: Chat bubbles with sender distinction
- **Input**: Fixed bottom position, persistent focus

## 🔧 Development Workflow

### Making Changes

1. **Always read existing code first**
   ```bash
   # Check current implementation
   Read api/main.py
   Read ui/src/App.jsx
   ```

2. **Test changes incrementally**
   ```bash
   # Run tests after each change
   ./test_system.sh
   ```

3. **Preserve Portuguese translations**
   - All UI text must be in PT-PT
   - Check `copy.js` for existing translations

4. **Maintain conversation logging**
   - Never remove logging functionality
   - Ensure all Q&A pairs are logged

### Testing Checklist
- [ ] API health endpoint responds
- [ ] Sessions create successfully
- [ ] Questions get responses
- [ ] Lists format correctly
- [ ] Logs record conversations
- [ ] Log viewer displays data
- [ ] UI loads and is interactive
- [ ] Portuguese text displays correctly

## 📋 User Preferences & Feedback

### What Users Want
- Natural, conversational responses
- Quick loading times
- Visual feedback during processing
- Easy conversation reset
- Ability to review past conversations

### What Users DON'T Want
- Overly restrictive content filtering
- Too-short responses (2 sentences too limiting)
- Complex UI elements
- English interface text (must be Portuguese)
- Slow response times

## 🚀 Deployment Notes

### Raspberry Pi Specifics
- Runs on port 3000 (UI) and 8000 (API)
- Designed for 8GB model
- WiFi connection required for API calls
- Can run in kiosk mode with Chromium

### Docker Commands
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Restart after changes
docker-compose restart api

# Full rebuild
docker-compose down && docker-compose up -d --build
```

## 💡 Future Considerations

### Potential Enhancements (User Requested)
- Voice input/output (Piper TTS mentioned)
- Offline fallback mode
- Multiple language support
- Parent dashboard
- Educational games

### Technical Debt
- No database (intentional - keep simple)
- No user authentication (by design)
- No state persistence between container restarts

## ⚠️ Critical Warnings

1. **NEVER remove the Anthropic API integration** - Core functionality
2. **ALWAYS maintain Portuguese UI** - Primary user requirement
3. **PRESERVE conversation logging** - Parent oversight feature
4. **KEEP ReactMarkdown rendering** - Fixes formatting issues
5. **DON'T over-engineer** - This is for 7-year-olds

## 🆘 Emergency Fixes

### If formatting breaks:
```javascript
// Ensure App.jsx uses (NO className on ReactMarkdown!):
<div className="bubble markdown-content">
  <ReactMarkdown>
    {message.response}
  </ReactMarkdown>
</div>
```

### If API fails:
```python
# Check llm_interface.py has:
api_key = os.getenv("ANTHROPIC_API_KEY")
```

### If logs disappear:
```yaml
# Verify docker-compose.yml has:
volumes:
  - ./logs:/app/logs
```

## 📝 Session Context

When continuing work on this project:
1. Check recent logs for user interaction patterns
2. Test the log viewer for conversation history
3. Verify Portuguese translations are complete
4. Ensure all tests pass before claiming completion

## 🎯 Success Metrics

Your changes are successful when:
- A 7-year-old can use it without help
- Parents can review all conversations
- Responses are natural and educational
- The UI is responsive and delightful
- Everything works on Raspberry Pi 5

---

**Remember**: This is a tool for children's education and wonder. Every decision should prioritize simplicity, safety, and delight. When in doubt, choose the solution that would make a 7-year-old smile.

Good luck, future Claude! 🌟