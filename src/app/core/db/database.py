import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from typing import AsyncGenerator

# Default to SQLite for Dev, allow Postgres for Prod
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./phylactery.db")

engine = create_async_engine(DATABASE_URL, echo=False, future=True)

async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db() -> None:
    """Initialize the database and create tables."""
    async with engine.begin() as conn:
        # For production with millions of rows, use Alembic. 
        # For now, SQLModel's create_all is sufficient for the Spine MVP.
        await conn.run_sync(SQLModel.metadata.create_all)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing an async session."""
    async with async_session_maker() as session:
        yield session
