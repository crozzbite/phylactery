import logging
import asyncio
import time
from pathlib import Path
from typing import TYPE_CHECKING

import frontmatter

from .models import Agent, Skill
from .memory import memory

if TYPE_CHECKING:
    from .engine import AgentEngine

logger = logging.getLogger(__name__)


class BrainLoader:
    def __init__(self, base_path: str = ".agent"):
        self.base_path = Path(base_path)
        self.agents: dict[str, Agent] = {}
        self.skills: dict[str, Skill] = {}
        self.active_engines: dict[str, "AgentEngine"] = {}

    async def load_brain(self) -> None:
        """Reloads all agents and skills from the filesystem."""
        self._load_skills()
        self._load_agents()
        logger.info(f"💀 Bones Loaded: {len(self.skills)} Skills, {len(self.agents)} Agents.")
        
        # Trigger Memory Indexing
        if self.skills:
            logger.info("🧠 Syncing Short-term (RAM) to Long-term (Pinecone)...")
            await memory.index_skills(list(self.skills.values()))

    async def get_engine(self, agent_name: str) -> "AgentEngine":
        """Returns a cached engine or creates a new one."""
        from .engine import AgentEngine

        if agent_name in self.active_engines:
            logger.info(f"✨ Invoking cached engine for {agent_name}")
            return self.active_engines[agent_name]

        agent_def = self.get_agent(agent_name)
        if not agent_def:
            return None

        logger.info(f"🧠 Initializing new engine for {agent_name}...")
        engine = AgentEngine(agent_def)
        # We handle async init here
        if agent_def.mcp_servers:
            await engine._init_mcp_tools(agent_def.mcp_servers)

        self.active_engines[agent_name] = engine
        return engine

    def prune_inactive_engines(self, ttl_seconds: int = 300) -> None:
        """Removes engines that haven't been used within the TTL."""
        now = time.time()
        to_delete = []

        for name, engine in self.active_engines.items():
            # Ensure the engine tracks its last used time
            last_used = getattr(engine, "last_used", now)
            if now - last_used > ttl_seconds:
                to_delete.append(name)

        for name in to_delete:
            logger.info(f"🧹 Lich's Sweep: Pruning inactive engine {name}")
            del self.active_engines[name]

    def _load_skills(self) -> None:
        """
        Load skills with progressive disclosure.
        
        Only loads frontmatter metadata initially. Full content is loaded
        on-demand when a skill is relevant to the current query.
        """
        skills_path = self.base_path / "skills"
        if not skills_path.exists():
            return

        # Walk through skill directories
        for skill_dir in skills_path.iterdir():
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    try:
                        post = frontmatter.load(skill_file)
                        meta = post.metadata

                        # Progressive Disclosure: Only load metadata initially
                        skill = Skill(
                            name=meta.get("name", skill_dir.name),
                            description=meta.get("description", "No description"),
                            version=meta.get("metadata", {}).get("version", "1.0.0"),
                            tags=meta.get("metadata", {}).get("tags", []),
                            content="",  # Empty initially, loaded on-demand
                            path=str(skill_file),
                        )
                        self.skills[skill.name] = skill
                    except Exception as e:
                        logger.error(f"❌ Error loading skill {skill_file}: {e}")
    
    def load_skill_content(self, skill_name: str) -> str:
        """
        Load full content of a skill on-demand.
        
        Args:
            skill_name: Name of the skill to load
            
        Returns:
            Full skill content, or empty string if not found
        """
        skill = self.skills.get(skill_name)
        if not skill:
            return ""
        
        # If content already loaded, return it
        if skill.content:
            return skill.content
        
        # Load full content from file
        try:
            post = frontmatter.load(skill.path)
            skill.content = post.content
            logger.info(f"📖 Loaded full content for skill: {skill_name}")
            return skill.content
        except Exception as e:
            logger.error(f"❌ Error loading skill content {skill.path}: {e}")
            return ""
    
    def get_relevant_skills(self, query: str, max_skills: int = 3) -> list[Skill]:
        """
        Get skills relevant to a query using progressive disclosure.
        
        Args:
            query: User query to match against skill descriptions
            max_skills: Maximum number of skills to return
            
        Returns:
            List of relevant skills with full content loaded
        """
        query_lower = query.lower()
        relevant: list[tuple[Skill, int]] = []
        
        # Score skills by keyword matches in description
        for skill in self.skills.values():
            desc_lower = skill.description.lower()
            score = 0
            
            # Simple keyword matching (can be improved with embeddings later)
            for word in query_lower.split():
                if len(word) > 3 and word in desc_lower:
                    score += 1
            
            if score > 0:
                relevant.append((skill, score))
        
        # Sort by score and take top N
        relevant.sort(key=lambda x: x[1], reverse=True)
        top_skills = [skill for skill, _ in relevant[:max_skills]]
        
        # Load full content for relevant skills
        for skill in top_skills:
            if not skill.content:
                self.load_skill_content(skill.name)
        
        return top_skills


    def _load_agents(self) -> None:
        # Phase 8 Fix: Recursive agent discovery (for architecture agents)
        # Scan everything except 'skills' folder
        potential_agents = [
            f for f in self.base_path.rglob("*.md")
            if "skills" not in f.parts and f.name != "AGENTS.md" and f.name != "README.md"
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
                logger.error(f"❌ Error loading agent {agent_file}: {e}")

    def get_agent(self, name: str) -> Agent | None:
        return self.agents.get(name)

    def get_skill(self, name: str) -> Skill | None:
        return self.skills.get(name)


# Global Instance
brain = BrainLoader("brain")
