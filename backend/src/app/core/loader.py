import logging
import asyncio
import time
from pathlib import Path
from typing import TYPE_CHECKING, List, Set, Dict, Optional, Tuple

import frontmatter

from .models import Agent, Skill
from .memory import memory

if TYPE_CHECKING:
    from .engine import AgentEngine

logger = logging.getLogger(__name__)


class BrainLoader:
    def __init__(self, base_path: str = ".agent"):
        self.base_path = Path(base_path)
        self.agents: Dict[str, Agent] = {}
        self.skills: Dict[str, Skill] = {}
        self.active_engines: Dict[str, "AgentEngine"] = {}
        self._engine_locks: Dict[str, asyncio.Lock] = {}

        # Config: warmup solo lo crítico
        self.core_warmup_agents: Set[str] = {"phylactery", "mcp_admin"}

    async def load_brain(self) -> None:
        """Reloads all agents and skills from the filesystem."""
    async def load_brain(self) -> None:
        """Reloads all agents and skills from the filesystem."""
        # 1. Safe Reload: Close existing engines to prevent stale state
        for name, engine in list(self.active_engines.items()):
            lock = self._engine_locks.get(name)
            if lock:
                async with lock:
                    await engine.aclose()
            else:
                await engine.aclose()
        self.active_engines.clear()
        self._engine_locks.clear()

        # 2. Clear previous state to prevent duplicates on reload
        self.skills.clear()
        self.agents.clear()
        
        self._load_skills()
        self._load_agents()
        logger.info(f"💀 Bones Loaded: {len(self.skills)} Skills, {len(self.agents)} Agents.")

        # Memory indexing (Fault Tolerant)
        if self.skills:
            logger.info("🧠 Syncing Short-term (RAM) to Long-term (Pinecone)...")
            try:
                await memory.index_skills(list(self.skills.values()))
            except Exception:
                # Degradation: Start even if long-term memory is down
                logger.exception("⚠️ Memory indexing skipped (degraded startup)")

        # Warmup selectivo
        warm = self.core_warmup_agents.intersection(self.agents.keys())
        logger.info(f"🔥 Warming up Core Agents: {sorted(warm)}")

        for agent_name in warm:
            try:
                await self.get_engine(agent_name)
                logger.info(f"✅ Warmup OK: {agent_name}")
            except Exception as e:
                logger.exception(f"❌ Warmup FAIL: {agent_name} - {e}")

    async def get_engine(self, agent_name: str) -> Optional["AgentEngine"]:
        """Returns a cached engine or creates a new one (thread-safe)."""
        from .engine import AgentEngine

        # Lock por agente para evitar race conditions
        lock = self._engine_locks.get(agent_name)
        if lock is None:
            lock = asyncio.Lock()
            self._engine_locks[agent_name] = lock

        async with lock:
            # Double-check cache inside lock
            cached = self.active_engines.get(agent_name)
            if cached is not None:
                cached.last_used = time.time()
                return cached

            agent_def = self.get_agent(agent_name)
            if not agent_def:
                return None

            logger.info(f"🧠 Initializing new engine for {agent_name}...")
            engine = AgentEngine(agent_def)
            await engine.initialize()



            engine.last_used = time.time()
            self.active_engines[agent_name] = engine
            return engine

    async def prune_inactive_engines(self, ttl_seconds: int = 300) -> None:
        """Removes engines that haven't been used within the TTL."""
        now = time.time()
        to_delete: List[str] = []

        for name, engine in self.active_engines.items():
            # Use getattr with default to avoid crashes if attribute missing
            last_used = getattr(engine, "last_used", now)
            if now - last_used > ttl_seconds:
                to_delete.append(name)

        for name in to_delete:
            logger.info(f"🧹 Lich's Sweep: Pruning inactive engine {name}")
            
            # Secure pruning with lock to avoid race conditions
            lock = self._engine_locks.get(name)
            if lock:
                async with lock:
                    engine = self.active_engines.pop(name, None)
                    if engine:
                        await engine.aclose()
            else:
                # Fallback if no lock found (rare)
                engine = self.active_engines.pop(name, None)
                if engine:
                    await engine.aclose()
            
            self._engine_locks.pop(name, None)

    # -------- Skills --------

    def _load_skills(self) -> None:
        skills_path = self.base_path / "skills"
        if not skills_path.exists():
            return

        for skill_dir in skills_path.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            try:
                post = frontmatter.load(skill_file)
                meta = post.metadata

                skill = Skill(
                    name=meta.get("name", skill_dir.name),
                    description=meta.get("description", "No description"),
                    version=meta.get("metadata", {}).get("version", "1.0.0"),
                    tags=meta.get("metadata", {}).get("tags", []),
                    content="",  # loaded on-demand
                    path=str(skill_file),
                )
                self.skills[skill.name] = skill
            except Exception as e:
                logger.exception(f"❌ Error loading skill {skill_file}: {e}")

    def load_skill_content(self, skill_name: str) -> str:
        skill = self.skills.get(skill_name)
        if not skill:
            return ""

        if skill.content:
            return skill.content

        try:
            post = frontmatter.load(skill.path)
            skill.content = post.content
            logger.info(f"📖 Loaded full content for skill: {skill_name}")
            return skill.content
        except Exception as e:
            logger.exception(f"❌ Error loading skill content {skill.path}: {e}")
            return ""

    def get_relevant_skills(self, query: str, max_skills: int = 3) -> List[Skill]:
        query_lower = query.lower()
        relevant: List[Tuple[Skill, int]] = []

        for skill in self.skills.values():
            desc_lower = (skill.description or "").lower()
            score = 0
            for word in query_lower.split():
                if len(word) > 3 and word in desc_lower:
                    score += 1
            if score > 0:
                relevant.append((skill, score))

        relevant.sort(key=lambda x: x[1], reverse=True)
        top_skills = [skill for skill, _ in relevant[:max_skills]]

        for skill in top_skills:
            if not skill.content:
                self.load_skill_content(skill.name)

        return top_skills

    # -------- Agents --------

    def _load_agents(self) -> None:
        potential_agents = [
            f for f in self.base_path.rglob("*.md")
            if "skills" not in f.parts and f.name not in {"AGENTS.md", "README.md"}
        ]

        for agent_file in potential_agents:
            try:
                post = frontmatter.load(agent_file)
                meta = post.metadata

                agent = Agent(
                    name=agent_file.stem,
                    role=meta.get("role", "Assistant"),
                    description=meta.get("description", "No description"),
                    instructions=post.content,
                    path=str(agent_file),
                    ai_provider=meta.get("ai_provider"),
                    mcp_servers=meta.get("mcp_servers", []),
                )
                self.agents[agent.name] = agent
            except Exception as e:
                logger.exception(f"❌ Error loading agent {agent_file}: {e}")

    def get_agent(self, name: str) -> Optional[Agent]:
        return self.agents.get(name)

    def get_skill(self, name: str) -> Optional[Skill]:
        return self.skills.get(name)


# Global Instance
brain = BrainLoader("../.agent")
