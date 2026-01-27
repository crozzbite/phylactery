"""Session management for Phylactery agents."""
import os
import uuid
from typing import Dict, Optional
from datetime import datetime, timedelta

from .core.engine import AgentEngine
from .core.loader import brain


class SessionManager:
    """Manages user sessions and AgentEngine instances."""
    
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}  # {session_token: {engine, user, created_at, last_activity}}
        self.session_timeout = timedelta(hours=24)  # Sessions expire after 24h of inactivity
    
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """Authenticate user and create a session token."""
        sudo_username = os.getenv("SUDO_USERNAME")
        sudo_password = os.getenv("SUDO_PASSWORD")
        
        if username == sudo_username and password == sudo_password:
            session_token = str(uuid.uuid4())
            self.sessions[session_token] = {
                "user": username,
                "engine": None,  # Will be created on first chat
                "created_at": datetime.now(),
                "last_activity": datetime.now()
            }
            return session_token
        return None
    
    async def get_engine(self, session_token: str, agent_name: str) -> Optional[AgentEngine]:
        """Get or create an AgentEngine for this session."""
        if session_token not in self.sessions:
            return None
        
        session = self.sessions[session_token]
        
        # Check if session expired
        if datetime.now() - session["last_activity"] > self.session_timeout:
            del self.sessions[session_token]
            return None
        
        # Update last activity
        session["last_activity"] = datetime.now()
        
        # Create engine if it doesn't exist
        if session["engine"] is None:
            session["engine"] = await brain.get_engine(agent_name)
        
        return session["engine"]
    
    def logout(self, session_token: str) -> bool:
        """Logout and destroy session."""
        if session_token in self.sessions:
            del self.sessions[session_token]
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions."""
        now = datetime.now()
        expired = [
            token for token, session in self.sessions.items()
            if now - session["last_activity"] > self.session_timeout
        ]
        for token in expired:
            del self.sessions[token]


# Global session manager instance
session_manager = SessionManager()
