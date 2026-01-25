
from pydantic import BaseModel


class Skill(BaseModel):
    name: str
    description: str
    version: str = "1.0.0"
    tags: list[str] = []
    content: str  # The full markdown content (Critical Patterns, etc.)
    path: str

class Agent(BaseModel):
    name: str
    role: str
    description: str
    skills: list[str] = []  # List of skill names referenced
    instructions: str  # The system prompt body
    path: str
