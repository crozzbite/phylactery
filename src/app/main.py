from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .core.loader import brain
from .api.routes import auth, chat


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Load Brain on Startup."""
    await brain.load_brain()
    yield
    # Clean up (if needed)


app = FastAPI(title="Phylactery API", version="0.1.0", lifespan=lifespan)

# Include Routers
app.include_router(auth.router)
app.include_router(chat.router)


@app.get("/")
def read_root() -> dict[str, list[str] | str]:
    """Root endpoint showing loaded agents and skills."""
    return {
        "status": "Phylactery, Alive again!. 💀",
        "loaded_agents": list(brain.agents.keys()),
        "loaded_skills": list(brain.skills.keys()),
    }
