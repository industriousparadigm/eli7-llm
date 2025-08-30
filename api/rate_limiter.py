"""Rate limiting for API endpoints to prevent abuse."""
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Tuple
import asyncio

class RateLimiter:
    """Simple in-memory rate limiter for child safety."""
    
    def __init__(self, max_requests: int = 30, window_minutes: int = 10):
        self.max_requests = max_requests
        self.window = timedelta(minutes=window_minutes)
        self.requests: Dict[str, list] = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def check_rate_limit(self, session_id: str) -> Tuple[bool, str]:
        """Check if session has exceeded rate limit."""
        async with self._lock:
            now = datetime.now()
            
            # Clean old requests
            if session_id in self.requests:
                self.requests[session_id] = [
                    req_time for req_time in self.requests[session_id]
                    if now - req_time < self.window
                ]
            
            # Check limit
            if len(self.requests[session_id]) >= self.max_requests:
                return False, "Too many questions! Take a break and come back in a few minutes 😊"
            
            # Record request
            self.requests[session_id].append(now)
            return True, ""
    
    async def get_remaining(self, session_id: str) -> int:
        """Get remaining requests for session."""
        async with self._lock:
            now = datetime.now()
            if session_id in self.requests:
                valid_requests = [
                    req for req in self.requests[session_id]
                    if now - req < self.window
                ]
                return max(0, self.max_requests - len(valid_requests))
            return self.max_requests

# Global rate limiter instance
rate_limiter = RateLimiter()