from fastapi import FastAPI
from contextlib import asynccontextmanager
from .core.loader import brain

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load Brain on Startup
    brain.load_brain()
    yield
    # Clean up (if needed)

app = FastAPI(title="Phylactery API", version="0.1.0", lifespan=lifespan)

@app.get("/")
def read_root():
    return {
        "status": "Phylactery is breathing. 💀",
        "loaded_agents": list(brain.agents.keys()),
        "loaded_skills": list(brain.skills.keys())
    }

from pydantic import BaseModel
from .core.engine import AgentEngine

class ChatRequest(BaseModel):
    message: str

@app.post("/chat/{agent_name}")
async def chat_with_agent(agent_name: str, request: ChatRequest):
    # 1. Load Agent Definition
    agent_def = brain.get_agent(agent_name)
    if not agent_def:
        return {"error": "Agent not found"}

    # 2. Spin up Engine (In production, cache this!)
    try:
        engine = AgentEngine(agent_def)
        response = await engine.ainvoke(request.message)
        return {"agent": agent_name, "response": response}
    except Exception as e:
        return {"error": str(e)}


