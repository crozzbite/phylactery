from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from .core.engine import AgentEngine
from .core.loader import brain


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load Brain on Startup."""
    brain.load_brain()
    yield
    # Clean up (if needed)


app = FastAPI(title="Phylactery API", version="0.1.0", lifespan=lifespan)


@app.get("/")
def read_root():
    """Root endpoint showing loaded agents and skills."""
    return {
        "status": "Phylactery is breathing. 💀",
        "loaded_agents": list(brain.agents.keys()),
        "loaded_skills": list(brain.skills.keys()),
    }


class ChatRequest(BaseModel):
    """Chat request model."""

    message: str


@app.post("/chat/{agent_name}")
async def chat_with_agent(agent_name: str, request: ChatRequest):
    """Chat with a specific agent."""
    # 1. Load Agent Definition
    agent_def = brain.get_agent(agent_name)
    if not agent_def:
        return {"error": "Agent not found"}

    # 2. Spin up Engine (In production, cache this!)
    try:
        engine = AgentEngine(agent_def)
        response = await engine.ainvoke(request.message)
        return {"agent": agent_name, "response": response}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}
