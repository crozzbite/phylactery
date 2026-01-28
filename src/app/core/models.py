
from pydantic import BaseModel


class Skill(BaseModel):
    name: str
    description: str
    version: str
    tags: list[str]
    content: str
    path: str


class Agent(BaseModel):
    name: str
    role: str
    description: str
    skills: list[str] = []  # List of skill names referenced
    instructions: str  # The system prompt body
    path: str
    ai_provider: str | None = None  # Optional: override global provider
    mcp_servers: list[str] = []
