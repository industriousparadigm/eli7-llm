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
        
        # Add current date/time to system prompt
        from datetime import datetime
        import locale
        try:
            locale.setlocale(locale.LC_TIME, 'pt_PT.UTF-8')
        except:
            pass  # Fallback to default locale
        
        now = datetime.now()
        date_str = now.strftime("%A, %d de %B de %Y")
        system_with_date = f"{SYSTEM_PROMPT}\n\nHoje é {date_str}."
        
        response = await llm.generate(
            system=system_with_date,
            user=request.question,
            history=messages,  # Pass conversation history
            max_tokens=int(os.getenv("MAX_TOKENS", 300)),  # Increased for full responses
            temperature=float(os.getenv("TEMPERATURE", 0.7))  # Slightly higher for fun
        )
        
        full_text = response['text'].strip()
        
        # Apply kid-safety filtering and rewriting
        full_text, was_modified = enforce_kid_safety(full_text, language)
        
        # Apply language-specific formatting
        full_text = format_for_language(full_text, language)
        
        # Log if the response was modified for safety
        if was_modified:
            print(f"Response modified by kid-safety filter for: {request.question[:50]}...")
        
        # Log the conversation exchange
        session_id = request.session_id or conversation_logger.start_session()
        conversation_logger.log_exchange(
            session_id=session_id,
            question=request.question,
            response=full_text,
            language=language
        )
        
        # Return raw markdown - frontend will handle formatting
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
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
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
        <h1>📊 Visualizador de Conversas</h1>
        
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
            
            container.innerHTML = filteredLogs.map(log => {
                const date = new Date(log.timestamp);
                const formattedDate = date.toLocaleDateString('pt-PT');
                const formattedTime = date.toLocaleTimeString('pt-PT');
                
                return `
                    <div class="log-entry">
                        <div class="log-header">
                            <span class="log-time">${formattedDate} às ${formattedTime}</span>
                            <span class="log-session">${log.session_id}</span>
                        </div>
                        <div class="log-question">❓ ${escapeHtml(log.question)}</div>
                        <div class="log-response">💬 ${escapeHtml(log.response)}</div>
                        <div class="log-meta">
                            <span>🌐 ${log.language}</span>
                            <span>📏 ${log.response_length} caracteres</span>
                            <span>📅 ${log.day_of_week}</span>
                        </div>
                    </div>
                `;
            }).join('');
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
        
        // Load logs on page load
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