import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

from .core.db import init_db
from .core.loader import brain
from .core.settings import settings
from .api.routes import auth, chat, runs, user, artifacts


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Load Brain and Init DB on Startup."""
    # Startup State
    app.state.ready = False
    
    try:
        await init_db()
        await brain.load_brain()
        app.state.ready = True
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        app.state.ready = False

    # Background Pruner Task
    stop_event = asyncio.Event()

    async def pruner():
        while not stop_event.is_set():
            try:
                await brain.prune_inactive_engines(ttl_seconds=300)
            except Exception as e:
                logger.error(f"Error in pruning task: {e}")
            await asyncio.sleep(60) # Check every minute

    prune_task = asyncio.create_task(pruner())

    yield
    
    # Shutdown
    stop_event.set()
    prune_task.cancel()
    # Ideally close MCP connections here if engines expose a close method


app = FastAPI(title="Phylactery API", version="0.1.0", lifespan=lifespan)

# Add CORS Middleware
# WARNING: Ensure settings.CORS_ORIGINS only contains production domains in a live environment!
# The current default includes localhost:4200 for development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(runs.router)
app.include_router(user.router)
app.include_router(artifacts.router)


@app.get("/health/live")
def health_live():
    return {"status": "ok"}

@app.get("/health/ready")
def health_ready():
    if not getattr(app.state, "ready", False):
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Not ready")
    return {"status": "ready"}


@app.get("/")
def read_root() -> dict[str, list[str] | str]:
    """Root endpoint showing loaded agents and skills."""
    return {
        "status": "Phylactery, Alive again!. 💀",
        "loaded_agents": list(brain.agents.keys()),
        "loaded_skills": list(brain.skills.keys()),
    }
