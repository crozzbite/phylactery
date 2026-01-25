from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class Skill(BaseModel):
    name: str
    description: str
    version: str = "1.0.0"
    tags: List[str] = []
    content: str  # The full markdown content (Critical Patterns, etc.)
    path: str

class Agent(BaseModel):
    name: str
    role: str
    description: str
    skills: List[str] = []  # List of skill names referenced
    instructions: str  # The system prompt body
    path: str
