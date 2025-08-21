from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from contextlib import asynccontextmanager
import os
import json
from datetime import datetime
from typing import Dict, List
import uuid
import logging
from pathlib import Path
import glob

from models import (
    AskRequest, AskResponse, Message,
    TTSRequest, TTSResponse,
    HealthResponse, VersionResponse
)
from pydantic import BaseModel
from typing import Optional
from llm_interface import get_llm_backend
from utils import (
    generate_context_id, chunk_text,
    is_safe_topic, count_tokens_approximate
)
from prompts import SYSTEM_PROMPT_V2
from kid_safety import (
    detect_language, enforce_kid_safety, format_for_language
)


# Context storage (in-memory for MVP)
contexts: Dict[str, Dict] = {}

# Settings model
class UserSettings(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None  # "male", "female", "neutral"
    date_of_birth: Optional[str] = None  # ISO format
    
# Settings storage (persisted to file)
SETTINGS_FILE = Path("/app/settings.json")

def load_settings() -> UserSettings:
    """Load user settings from file."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                return UserSettings(**data)
        except:
            pass
    return UserSettings()

def save_settings(settings: UserSettings):
    """Save user settings to file."""
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings.dict(), f, indent=2)

# Conversation logger
class ConversationLogger:
    def __init__(self):
        self.logs_dir = Path("/app/logs")
        self.logs_dir.mkdir(exist_ok=True)
        
    def log_exchange(self, session_id: str, question: str, response: str, language: str):
        """Log a Q&A exchange to a JSON file."""
        timestamp = datetime.now()
        
        # Create daily log file
        log_file = self.logs_dir / f"conversations_{timestamp.strftime('%Y%m%d')}.jsonl"
        
        log_entry = {
            "session_id": session_id,
            "timestamp": timestamp.isoformat(),
            "day_of_week": timestamp.strftime("%A"),
            "time_of_day": timestamp.strftime("%H:%M:%S"),
            "language": language,
            "question": question,
            "response": response,
            "response_length": len(response),
            "question_length": len(question)
        }
        
        # Append to JSONL file (one JSON object per line)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    def start_session(self):
        """Generate a new session ID for tracking conversations."""
        return str(uuid.uuid4())[:8]

conversation_logger = ConversationLogger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Soft Terminal API...")
    yield
    # Shutdown
    if os.getenv("SAVE_TRANSCRIPTS") == "true":
        # Save transcripts to file
        os.makedirs("transcripts", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"transcripts/session_{timestamp}.json", "w") as f:
            json.dump(contexts, f, indent=2)


app = FastAPI(
    title="Soft Terminal LLM API",
    version="1.0.0",
    docs_url="/docs",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Use the new Kid Tutor v2 prompt
SYSTEM_PROMPT = SYSTEM_PROMPT_V2


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")


@app.get("/version", response_model=VersionResponse)
async def version():
    return VersionResponse(ui="1.0.0", api="1.0.0")


@app.post("/new-session")
async def new_session():
    """Start a new conversation session."""
    session_id = conversation_logger.start_session()
    return {"session_id": session_id}


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    # Check topic safety
    is_safe, safety_message = is_safe_topic(request.question)
    if not is_safe:
        return AskResponse(
            response=safety_message,
            formatted_response=f"<p>{safety_message}</p>"
        )
    
    try:
        # Detect language from the question
        language = detect_language(request.question)
        
        # Get LLM response with conversation history
        llm = get_llm_backend()
        
        # Build conversation history for the LLM
        messages = []
        for msg in request.history[-6:]:  # Keep last 3 exchanges for context
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add current date/time and user settings to system prompt
        from datetime import datetime
        import locale
        try:
            locale.setlocale(locale.LC_TIME, 'pt_PT.UTF-8')
        except:
            pass  # Fallback to default locale
        
        now = datetime.now()
        date_str = now.strftime("%A, %d de %B de %Y")
        
        # Load user settings to personalize response
        settings = load_settings()
        personalization = ""
        
        if settings.name:
            personalization += f"\n\nA criança com quem estás a falar chama-se {settings.name}."
        
        if settings.gender:
            if settings.gender == "female":
                personalization += " Ela é uma menina, usa sempre pronomes femininos."
            elif settings.gender == "male":
                personalization += " Ele é um menino, usa sempre pronomes masculinos."
        
        if settings.date_of_birth:
            try:
                dob = datetime.fromisoformat(settings.date_of_birth)
                age = (now - dob).days // 365
                personalization += f" Tem {age} anos."
            except:
                pass
        
        system_with_date = f"{SYSTEM_PROMPT}{personalization}\n\nHoje é {date_str}."
        
        response = await llm.generate(
            system=system_with_date,
            user=request.question,
            history=messages,  # Pass conversation history
            max_tokens=int(os.getenv("MAX_TOKENS", 800)),  # Increased to prevent truncation
            temperature=float(os.getenv("TEMPERATURE", 0.7))  # Slightly higher for fun
        )
        
        full_text = response['text'].strip()
        
        # DEBUG: Log raw response from Claude
        newline_count = full_text.count('\n')
        print(f"\n=== DEBUG: Raw Claude Response ===")
        print(f"Question: {request.question[:100]}...")
        print(f"Raw response:\n{full_text}")
        print(f"Response has {newline_count} newlines")
        print(f"=================================\n")
        
        # JUST PASS IT THROUGH - NO PROCESSING!
        # Detect language just for logging
        language = detect_language(request.question)
        
        # Log the conversation exchange
        session_id = request.session_id or conversation_logger.start_session()
        conversation_logger.log_exchange(
            session_id=session_id,
            question=request.question,
            response=full_text,
            language=language
        )
        
        # Return EXACTLY what Claude sent - NO MODIFICATIONS
        return AskResponse(
            response=full_text
        )
        
    except Exception as e:
        print(f"Error in /ask: {e}")
        raise HTTPException(status_code=500, detail="Something went wrong. Let's try again!")



@app.post("/tts", response_model=TTSResponse)
async def tts(request: TTSRequest):
    # Stub implementation for TTS
    # Will integrate Piper TTS when running on Raspberry Pi
    return TTSResponse(audio_url=None)


# Settings endpoints
@app.get("/settings", response_model=UserSettings)
async def get_settings():
    """Get current user settings."""
    return load_settings()


@app.post("/settings", response_model=UserSettings)
async def update_settings(settings: UserSettings):
    """Update user settings."""
    save_settings(settings)
    return settings


# Log viewer endpoints
@app.get("/logs-data")
async def get_logs_data():
    """Get all conversation logs as JSON."""
    logs_dir = Path("/app/logs")
    all_logs = []
    
    if logs_dir.exists():
        # Get all log files sorted by date
        log_files = sorted(logs_dir.glob("conversations_*.jsonl"))
        
        for log_file in log_files:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            log_entry = json.loads(line)
                            all_logs.append(log_entry)
                        except json.JSONDecodeError:
                            continue
    
    return JSONResponse(content={"logs": all_logs})


@app.get("/logs", response_class=HTMLResponse)
async def view_logs():
    """Serve the log viewer HTML page."""
    html_content = """<!DOCTYPE html>
<html lang="pt">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Soft Terminal - Visualizador de Logs</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Lexend', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(180deg, #FEFFFF 0%, #F0F9FF 50%, #E5F4FF 100%);
            color: #1e2846;
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        h1 {
            color: #1e2846;
            margin-bottom: 30px;
            font-size: 32px;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(8px);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 8px 24px rgba(20, 20, 40, 0.06);
            border: 1px solid rgba(30, 40, 70, 0.08);
        }
        
        .stat-value {
            font-size: 36px;
            font-weight: 600;
            color: #5cd6b5;
        }
        
        .stat-label {
            color: #7A889B;
            margin-top: 8px;
        }
        
        .filters {
            background: white;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
            box-shadow: 0 4px 14px rgba(20, 20, 40, 0.05);
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            align-items: center;
        }
        
        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        
        label {
            font-size: 14px;
            color: #7A889B;
            font-weight: 500;
        }
        
        input, select {
            padding: 10px 14px;
            border: 1px solid rgba(30, 40, 70, 0.10);
            border-radius: 8px;
            font-size: 16px;
            font-family: inherit;
            background: white;
        }
        
        input:focus, select:focus {
            outline: none;
            box-shadow: 0 0 0 3px rgba(92, 214, 181, 0.2);
        }
        
        button {
            background: #5cd6b5;
            color: white;
            border: none;
            border-radius: 999px;
            padding: 10px 20px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        
        button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(92, 214, 181, 0.3);
        }
        
        .logs-container {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 14px rgba(20, 20, 40, 0.05);
            max-height: 600px;
            overflow-y: auto;
        }
        
        .log-entry {
            border-bottom: 1px solid #f0f2f5;
            padding: 20px 0;
        }
        
        .log-entry:last-child {
            border-bottom: none;
        }
        
        .log-header {
            display: flex;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .log-number {
            background: #5cd6b5;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-weight: 600;
            margin-right: 8px;
            font-size: 12px;
        }
        
        .log-time {
            font-size: 14px;
            color: #7A889B;
        }
        
        .log-session {
            background: #F2FBF7;
            color: #0d3b2a;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-family: monospace;
        }
        
        .log-question {
            font-weight: 500;
            margin-bottom: 8px;
            color: #1e2846;
        }
        
        .log-response {
            color: #4A5568;
            line-height: 1.6;
            white-space: pre-wrap;
        }
        
        .log-meta {
            display: flex;
            gap: 16px;
            margin-top: 12px;
            font-size: 12px;
            color: #7A889B;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #7A889B;
        }
        
        .empty {
            text-align: center;
            padding: 40px;
            color: #7A889B;
        }
        
        /* Session grouping styles */
        .session-group {
            margin-bottom: 20px;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 14px rgba(20, 20, 40, 0.05);
        }
        
        .session-header {
            padding: 16px 20px;
            background: linear-gradient(90deg, #5cd6b5, #4fc7a8);
            color: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 12px;
            transition: background 0.2s;
        }
        
        .session-header:hover {
            background: linear-gradient(90deg, #4fc7a8, #42b89b);
        }
        
        .session-toggle {
            font-size: 14px;
            width: 20px;
        }
        
        .session-info {
            flex: 1;
        }
        
        .session-preview {
            font-size: 14px;
            opacity: 0.9;
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        
        .session-content {
            padding: 0;
        }
        
        /* Settings Section */
        .settings-section {
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 30px;
            box-shadow: 0 4px 14px rgba(20, 20, 40, 0.05);
        }
        
        .settings-section h2 {
            color: #1e2846;
            margin: 0 0 20px 0;
            font-size: 24px;
        }
        
        .settings-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .settings-field label {
            display: block;
            margin-bottom: 6px;
            color: #7A889B;
            font-size: 14px;
            font-weight: 500;
        }
        
        .settings-field input,
        .settings-field select {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #e5e5e5;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.2s;
        }
        
        .settings-field input:focus,
        .settings-field select:focus {
            outline: none;
            border-color: #5cd6b5;
            box-shadow: 0 0 0 3px rgba(92, 214, 181, 0.15);
        }
        
        .save-settings {
            background: #5cd6b5;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .save-settings:hover {
            background: #4fc7a8;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(92, 214, 181, 0.3);
        }
        
        .settings-message {
            margin-top: 12px;
            padding: 12px;
            border-radius: 8px;
            display: none;
        }
        
        .settings-message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
            display: block;
        }
        
        .settings-message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
            display: block;
        }
        
        @media (max-width: 640px) {
            .filters {
                flex-direction: column;
                align-items: stretch;
            }
            
            .filter-group {
                width: 100%;
            }
            
            input, select {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Painel de Administração</h1>
        
        <!-- Settings Section -->
        <div class="settings-section">
            <h2>⚙️ Configurações da Criança</h2>
            <div class="settings-grid">
                <div class="settings-field">
                    <label for="childName">Nome</label>
                    <input type="text" id="childName" placeholder="Ex: Diana">
                </div>
                <div class="settings-field">
                    <label for="childGender">Género</label>
                    <select id="childGender">
                        <option value="">Selecionar...</option>
                        <option value="female">Menina</option>
                        <option value="male">Menino</option>
                        <option value="neutral">Neutro</option>
                    </select>
                </div>
                <div class="settings-field">
                    <label for="childDOB">Data de Nascimento</label>
                    <input type="date" id="childDOB">
                </div>
                <button onclick="saveSettings()" class="save-settings">💾 Guardar Configurações</button>
            </div>
            <div id="settingsMessage" class="settings-message"></div>
        </div>
        
        <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e5e5;">
        
        <h2>📈 Estatísticas</h2>
        <div class="stats" id="stats">
            <div class="stat-card">
                <div class="stat-value" id="totalConversations">0</div>
                <div class="stat-label">Total de Conversas</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="todayConversations">0</div>
                <div class="stat-label">Conversas Hoje</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="uniqueSessions">0</div>
                <div class="stat-label">Sessões Únicas</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="avgResponseLength">0</div>
                <div class="stat-label">Tamanho Médio Resposta</div>
            </div>
        </div>
        
        <div class="filters">
            <div class="filter-group">
                <label for="dateFilter">Data</label>
                <input type="date" id="dateFilter">
            </div>
            <div class="filter-group">
                <label for="sessionFilter">Sessão</label>
                <input type="text" id="sessionFilter" placeholder="ID da sessão">
            </div>
            <div class="filter-group">
                <label for="languageFilter">Idioma</label>
                <select id="languageFilter">
                    <option value="">Todos</option>
                    <option value="pt">Português</option>
                    <option value="pt-PT">Português (PT)</option>
                    <option value="en">English</option>
                </select>
            </div>
            <div class="filter-group">
                <label for="searchFilter">Pesquisar</label>
                <input type="text" id="searchFilter" placeholder="Pesquisar perguntas...">
            </div>
            <button onclick="applyFilters()">Filtrar</button>
            <button onclick="clearFilters()">Limpar</button>
        </div>
        
        <div class="logs-container" id="logsContainer">
            <div class="loading">A carregar conversas...</div>
        </div>
    </div>
    
    <script>
        let allLogs = [];
        let filteredLogs = [];
        
        // Load settings when page loads
        async function loadSettings() {
            try {
                const response = await fetch('/settings');
                if (response.ok) {
                    const settings = await response.json();
                    document.getElementById('childName').value = settings.name || '';
                    document.getElementById('childGender').value = settings.gender || '';
                    document.getElementById('childDOB').value = settings.date_of_birth || '';
                }
            } catch (error) {
                console.error('Error loading settings:', error);
            }
        }
        
        // Save settings
        async function saveSettings() {
            const settings = {
                name: document.getElementById('childName').value,
                gender: document.getElementById('childGender').value,
                date_of_birth: document.getElementById('childDOB').value
            };
            
            try {
                const response = await fetch('/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(settings)
                });
                
                const messageDiv = document.getElementById('settingsMessage');
                if (response.ok) {
                    messageDiv.className = 'settings-message success';
                    messageDiv.textContent = '✅ Configurações guardadas com sucesso!';
                    setTimeout(() => {
                        messageDiv.className = 'settings-message';
                        messageDiv.textContent = '';
                    }, 3000);
                } else {
                    messageDiv.className = 'settings-message error';
                    messageDiv.textContent = '❌ Erro ao guardar configurações';
                }
            } catch (error) {
                console.error('Error saving settings:', error);
                const messageDiv = document.getElementById('settingsMessage');
                messageDiv.className = 'settings-message error';
                messageDiv.textContent = '❌ Erro ao guardar configurações';
            }
        }
        
        async function loadLogs() {
            try {
                const response = await fetch('/logs-data');
                const data = await response.json();
                allLogs = data.logs.sort((a, b) => 
                    new Date(b.timestamp) - new Date(a.timestamp)
                );
                filteredLogs = allLogs;
                updateStats();
                renderLogs();
            } catch (error) {
                console.error('Error loading logs:', error);
                document.getElementById('logsContainer').innerHTML = 
                    '<div class="empty">Erro ao carregar conversas</div>';
            }
        }
        
        function updateStats() {
            // Total conversations
            document.getElementById('totalConversations').textContent = filteredLogs.length;
            
            // Today's conversations
            const today = new Date().toISOString().split('T')[0];
            const todayCount = filteredLogs.filter(log => 
                log.timestamp.startsWith(today)
            ).length;
            document.getElementById('todayConversations').textContent = todayCount;
            
            // Unique sessions
            const uniqueSessions = new Set(filteredLogs.map(log => log.session_id)).size;
            document.getElementById('uniqueSessions').textContent = uniqueSessions;
            
            // Average response length
            const avgLength = filteredLogs.length > 0
                ? Math.round(filteredLogs.reduce((sum, log) => sum + log.response_length, 0) / filteredLogs.length)
                : 0;
            document.getElementById('avgResponseLength').textContent = avgLength;
        }
        
        function renderLogs() {
            const container = document.getElementById('logsContainer');
            
            if (filteredLogs.length === 0) {
                container.innerHTML = '<div class="empty">Nenhuma conversa encontrada</div>';
                return;
            }
            
            // Group logs by session
            const sessions = {};
            filteredLogs.forEach(log => {
                if (!sessions[log.session_id]) {
                    sessions[log.session_id] = [];
                }
                sessions[log.session_id].push(log);
            });
            
            // Sort sessions by most recent activity
            const sortedSessions = Object.entries(sessions)
                .sort(([,a], [,b]) => new Date(b[0].timestamp) - new Date(a[0].timestamp));
            
            // Render sessions
            container.innerHTML = sortedSessions.map(([sessionId, logs], index) => {
                // Sort logs within session by timestamp (oldest first for chronological order)
                const chronologicalLogs = [...logs].sort((a, b) => 
                    new Date(a.timestamp) - new Date(b.timestamp)
                );
                
                const firstLog = chronologicalLogs[0];
                const sessionDate = new Date(firstLog.timestamp);
                const formattedDate = sessionDate.toLocaleDateString('pt-PT');
                const formattedTime = sessionDate.toLocaleTimeString('pt-PT');
                const isExpanded = index === 0; // Only expand the most recent session
                
                return `
                    <div class="session-group">
                        <div class="session-header" onclick="toggleSession('${sessionId}')">
                            <span class="session-toggle" id="toggle-${sessionId}">${isExpanded ? '▼' : '▶'}</span>
                            <span class="session-info">
                                <strong>Sessão ${sessionId}</strong> - 
                                ${formattedDate} às ${formattedTime} - 
                                ${chronologicalLogs.length} pergunta${chronologicalLogs.length > 1 ? 's' : ''}
                            </span>
                            <span class="session-preview">${escapeHtml(firstLog.question.substring(0, 50))}...</span>
                        </div>
                        <div class="session-content" id="session-${sessionId}" style="display: ${isExpanded ? 'block' : 'none'}">
                            ${chronologicalLogs.map((log, logIndex) => {
                                const logDate = new Date(log.timestamp);
                                const logTime = logDate.toLocaleTimeString('pt-PT');
                                
                                return `
                                    <div class="log-entry">
                                        <div class="log-header">
                                            <span class="log-number">Q${logIndex + 1}</span>
                                            <span class="log-time">${logTime}</span>
                                        </div>
                                        <div class="log-question">❓ ${escapeHtml(log.question)}</div>
                                        <div class="log-response">💬 ${escapeHtml(log.response)}</div>
                                        <div class="log-meta">
                                            <span>🌐 ${log.language}</span>
                                            <span>📏 ${log.response_length} caracteres</span>
                                        </div>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        function toggleSession(sessionId) {
            const content = document.getElementById(`session-${sessionId}`);
            const toggle = document.getElementById(`toggle-${sessionId}`);
            
            if (content.style.display === 'none') {
                content.style.display = 'block';
                toggle.textContent = '▼';
            } else {
                content.style.display = 'none';
                toggle.textContent = '▶';
            }
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function applyFilters() {
            const dateFilter = document.getElementById('dateFilter').value;
            const sessionFilter = document.getElementById('sessionFilter').value.toLowerCase();
            const languageFilter = document.getElementById('languageFilter').value;
            const searchFilter = document.getElementById('searchFilter').value.toLowerCase();
            
            filteredLogs = allLogs.filter(log => {
                // Date filter
                if (dateFilter && !log.timestamp.startsWith(dateFilter)) {
                    return false;
                }
                
                // Session filter
                if (sessionFilter && !log.session_id.toLowerCase().includes(sessionFilter)) {
                    return false;
                }
                
                // Language filter
                if (languageFilter && log.language !== languageFilter) {
                    return false;
                }
                
                // Search filter
                if (searchFilter && 
                    !log.question.toLowerCase().includes(searchFilter) && 
                    !log.response.toLowerCase().includes(searchFilter)) {
                    return false;
                }
                
                return true;
            });
            
            updateStats();
            renderLogs();
        }
        
        function clearFilters() {
            document.getElementById('dateFilter').value = '';
            document.getElementById('sessionFilter').value = '';
            document.getElementById('languageFilter').value = '';
            document.getElementById('searchFilter').value = '';
            filteredLogs = allLogs;
            updateStats();
            renderLogs();
        }
        
        // Load settings and logs on page load
        loadSettings();
        loadLogs();
        
        // Auto-refresh every 30 seconds
        setInterval(loadLogs, 30000);
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)