from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class Message(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)
    history: List[Message] = Field(default_factory=list)
    session_id: Optional[str] = None


class MoreRequest(BaseModel):
    context_id: str = Field(..., min_length=8)


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)


class AskResponse(BaseModel):
    response: str  # Raw markdown text from Claude


class TTSResponse(BaseModel):
    audio_url: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"


class VersionResponse(BaseModel):
    ui: str = "1.0.0"
    api: str = "1.0.0"