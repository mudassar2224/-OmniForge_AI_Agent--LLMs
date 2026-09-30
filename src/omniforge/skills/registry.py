"""Registry for agent skills with progressive disclosure."""
import logging
from pathlib import Path
from pydantic import BaseModel, Field

try:
    import yaml
except ImportError:
    yaml = None  # Fallback frontmatter parsing if pyyaml is not installed

logger = logging.getLogger(__name__)


class SkillMetadata(BaseModel):
    """Metadata representing an agent skill."""

    name: str = Field(description="Unique name of the skill")
    description: str = Field(default="", description="Brief summary of skill capabilities")
    path: str = Field(description="Filesystem path to the SKILL.md file")
    loaded: bool = Field(default=False, description="Whether full skill instructions are loaded")
    content: str = Field(default="", description="Full markdown instructions for the skill")


class SkillRegistry:
    """Registry for agent skills with progressive disclosure.

    Allows discovering available skills and presenting compact summaries to LLMs,
    loading full detailed instructions only when a skill is actively required.
    """

    def __init__(self, skills_dir: str | Path = "skills") -> None:
        candidate = Path(skills_dir)
        if not candidate.exists() and not candidate.is_absolute():
            # Try resolving relative to OmniForge project root
            project_skills = Path(__file__).resolve().parents[3] / candidate
            if project_skills.exists():
                candidate = project_skills
        self.skills_dir: Path = candidate
        self.skills: dict[str, SkillMetadata] = {}
        self._discover_skills()

    def _discover_skills(self) -> None:
        """Discover skills by scanning the skills directory for SKILL.md files."""
        if not self.skills_dir.exists():
            logger.debug("Skills directory does not exist: %s", self.skills_dir)
            return

        for skill_dir in sorted(self.skills_dir.iterdir()):
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    meta = self._parse_skill_metadata(skill_file, skill_dir.name)
                    if meta:
                        self.skills[meta.name] = meta
                        logger.debug("Registered skill: %s from %s", meta.name, skill_file)

    def _parse_skill_metadata(self, skill_file: Path, dir_name: str) -> SkillMetadata | None:
        """Parse SKILL.md frontmatter for name and description."""
        try:
            text = skill_file.read_text(encoding="utf-8")
            # Parse YAML frontmatter between --- markers
            if text.startswith("---"):
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    raw_frontmatter = parts[1].strip()
                    parsed: dict = {}
                    if yaml is not None:
                        parsed = yaml.safe_load(raw_frontmatter) or {}
                    else:
                        # Lightweight key-value fallback
                        for line in raw_frontmatter.splitlines():
                            if ":" in line:
                                k, v = line.split(":", 1)
                                parsed[k.strip()] = v.strip().strip("'\"")

                    return SkillMetadata(
                        name=parsed.get("name", dir_name),
                        description=parsed.get("description", ""),
                        path=str(skill_file),
                    )

            # Fallback: use directory name and leading excerpt
            fallback_desc = ""
            for line in text.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    fallback_desc = stripped[:200]
                    break

            return SkillMetadata(
                name=dir_name,
                description=fallback_desc,
                path=str(skill_file),
            )
        except Exception as e:
            logger.error("Failed to parse skill metadata from %s: %e", skill_file, e)
            return None

    def get_skill_summaries(self) -> str:
        """Get a compact summary of all available skills for the LLM."""
        lines = []
        for name, meta in sorted(self.skills.items()):
            lines.append(f"- {name}: {meta.description}")
        return "\n".join(lines) if lines else "No skills available."

    def load_skill(self, name: str) -> str:
        """Load full skill content. Only call when skill is needed."""
        if name not in self.skills:
            return f"Skill '{name}' not found."
        skill = self.skills[name]
        if not skill.loaded:
            try:
                skill.content = Path(skill.path).read_text(encoding="utf-8")
                skill.loaded = True
            except Exception as e:
                logger.error("Error loading skill '%s': %s", name, e)
                return f"Error loading skill: {e}"
        return skill.content

    def list_skills(self) -> list[str]:
        """Return the names of all registered skills."""
        return sorted(list(self.skills.keys()))

    def get_skill(self, name: str) -> SkillMetadata | None:
        """Retrieve metadata for a specific skill by name."""
        return self.skills.get(name)

    def reload(self) -> None:
        """Re-scan the skills directory to discover newly added or updated skills."""
        self.skills.clear()
        self._discover_skills()
