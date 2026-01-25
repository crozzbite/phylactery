from pathlib import Path

import frontmatter

from .models import Agent, Skill


class BrainLoader:
    def __init__(self, base_path: str = ".agent"):
        self.base_path = Path(base_path)
        self.agents: dict[str, Agent] = {}
        self.skills: dict[str, Skill] = {}

    def load_brain(self) -> None:
        """Reloads all agents and skills from the filesystem."""
        self._load_skills()
        self._load_agents()
        print(f"💀 Bones Loaded: {len(self.skills)} Skills, {len(self.agents)} Agents.")

    def _load_skills(self) -> None:
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

                        skill = Skill(
                            name=meta.get("name", skill_dir.name),
                            description=meta.get("description", "No description"),
                            version=meta.get("metadata", {}).get("version", "1.0.0"),
                            tags=meta.get("metadata", {}).get("tags", []),
                            content=post.content,
                            path=str(skill_file)
                        )
                        self.skills[skill.name] = skill
                    except Exception as e:
                        print(f"❌ Error loading skill {skill_file}: {e}")

    def _load_agents(self) -> None:
        agents_path = self.base_path / "agents"
        if not agents_path.exists():
            return

        for agent_file in agents_path.glob("*.md"):
            try:
                post = frontmatter.load(agent_file)
                meta = post.metadata

                # Parse referenced skills (if any) from content links or metadata
                # For now, we assume metadata 'skills' list or inferred from text
                # Simple implementation: metadata based

                agent = Agent(
                    name=agent_file.stem,
                    role=meta.get("role", "Assistant"),
                    description=meta.get("description", "No description"),
                    instructions=post.content,
                    path=str(agent_file)
                )
                self.agents[agent.name] = agent
            except Exception as e:
                print(f"❌ Error loading agent {agent_file}: {e}")

    def get_agent(self, name: str) -> Agent | None:
        return self.agents.get(name)

    def get_skill(self, name: str) -> Skill | None:
        return self.skills.get(name)

# Global Instance
brain = BrainLoader()
