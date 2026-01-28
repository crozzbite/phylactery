import uuid
from datetime import datetime
from typing import Optional, List, Dict
from sqlmodel import select
from .models import RunStatus, RunResponse, JobEvent, EventType
from ..core.db import async_session_maker, RunDB, EventDB

class JobManager:
    """
    Manages the lifecycle of agent runs (jobs).
    Hardened for production with the Persistent Spinal Cord (SQL Integration).
    1. Run Ownership Binding (Mandatory)
    2. Deterministic Idempotency (Persistent)
    3. Persistent SSE Event Store
    """
    
    async def create_run(
        self, 
        agent_name: str, 
        owner_id: str,
        thread_id: Optional[str] = None, 
        idempotency_key: Optional[str] = None
    ) -> RunResponse:
        """Create a new run tracking record with ownership binding in SQL."""
        
        async with async_session_maker() as session:
            # 1. Deterministic Idempotency Check
            if idempotency_key:
                statement = select(RunDB).where(RunDB.idempotency_key == idempotency_key)
                results = await session.execute(statement)
                existing_run = results.scalar_one_or_none()
                
                if existing_run:
                    # Verify owner matches (Security Binding)
                    if existing_run.owner_id == owner_id:
                        return self._map_to_response(existing_run)
                    else:
                        raise ValueError("Idempotency key collision or unauthorized access attempt.")
            
            # 2. Create new Run
            run_db = RunDB(
                agent_name=agent_name,
                owner_id=owner_id,
                thread_id=thread_id or str(uuid.uuid4()),
                idempotency_key=idempotency_key,
                status=RunStatus.PENDING
            )
            
            session.add(run_db)
            await session.commit()
            await session.refresh(run_db)
            
            return self._map_to_response(run_db)

    async def get_run(self, run_id: str, owner_id: str) -> RunResponse:
        """Retrieve a run's public metadata WITH ownership verification in SQL."""
        async with async_session_maker() as session:
            statement = select(RunDB).where(RunDB.id == run_id)
            results = await session.execute(statement)
            run_db = results.scalar_one_or_none()
            
            if not run_db:
                raise ValueError(f"Run {run_id} not found")
                
            # Ownership Binding Enforcement
            if run_db.owner_id != owner_id:
                raise PermissionError("Unauthorized access to run.")
                
            return self._map_to_response(run_db)

    async def update_status(self, run_id: str, status: RunStatus) -> None:
        """Update the status of a run. Usually called by background tasks."""
        async with async_session_maker() as session:
            statement = select(RunDB).where(RunDB.id == run_id)
            results = await session.execute(statement)
            run_db = results.scalar_one_or_none()
            
            if run_db:
                run_db.status = status
                run_db.updated_at = datetime.utcnow()
                session.add(run_db)
                await session.commit()

    async def add_event(self, run_id: str, event_type: EventType, payload: Dict[str, object]) -> None:
        """Add a typed event to the run's persistent history."""
        async with async_session_maker() as session:
            event_db = EventDB(
                run_id=run_id,
                event_type=event_type,
                data=payload
            )
            session.add(event_db)
            
            # Also update run's updated_at
            statement = select(RunDB).where(RunDB.id == run_id)
            results = await session.execute(statement)
            run_db = results.scalar_one_or_none()
            if run_db:
                run_db.updated_at = datetime.utcnow()
                session.add(run_db)
                
            await session.commit()

    async def get_events(self, run_id: str, owner_id: str) -> List[JobEvent]:
        """Get all events for a run WITH ownership verification in SQL."""
        async with async_session_maker() as session:
            # First check ownership
            statement = select(RunDB).where(RunDB.id == run_id)
            results = await session.execute(statement)
            run_db = results.scalar_one_or_none()
            
            if not run_db:
                return []
                
            if run_db.owner_id != owner_id:
                raise PermissionError("Unauthorized access to run events.")
            
            # Fetch events
            event_statement = select(EventDB).where(EventDB.run_id == run_id).order_by(EventDB.timestamp)
            event_results = await session.execute(event_statement)
            events = event_results.scalars().all()
            
            return [
                JobEvent(event_type=e.event_type, payload=e.data)
                for e in events
            ]

    def _map_to_response(self, run_db: RunDB) -> RunResponse:
        """Helper to map DB model to API response model."""
        return RunResponse(
            run_id=run_db.id,
            agent_name=run_db.agent_name,
            status=run_db.status,
            created_at=run_db.created_at,
            updated_at=run_db.updated_at,
            thread_id=run_db.thread_id,
            owner_id=run_db.owner_id
        )

# Global instance
job_manager = JobManager()
