"""Skill loader helpers and task-oriented skill selection."""
import logging
from typing import Sequence
from omniforge.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)

_registry: SkillRegistry | None = None

SKILL_KEYWORDS_MAP: dict[str, list[str]] = {
    "planning": ["plan", "break down", "steps", "strategy"],
    "web-research": ["search", "find", "look up", "web", "internet", "latest", "current"],
    "deep-research": ["research", "compare", "analyze papers", "literature", "survey"],
    "source-verification": ["verify", "check source", "citation", "reliable"],
    "coding": ["code", "implement", "program", "build", "create", "python", "function"],
    "debugging": ["debug", "fix", "error", "bug", "issue", "traceback"],
    "data-analysis": ["data", "csv", "excel", "analyze", "statistics", "dataset", "plot"],
    "document-analysis": ["pdf", "document", "docx", "read file", "summarize document"],
    "report-generation": ["report", "write up", "summary", "compile findings"],
    "media-generation": ["image", "picture", "video", "generate image", "create image", "visual"],
}


def get_skill_registry(skills_dir: str = "skills") -> SkillRegistry:
    """Get or initialize the global SkillRegistry instance."""
    global _registry
    if _registry is None:
        _registry = SkillRegistry(skills_dir)
    return _registry


def reset_skill_registry() -> None:
    """Reset the global skill registry instance (useful for testing or directory changes)."""
    global _registry
    _registry = None


def select_skills_for_task(
    task_description: str,
    registry: SkillRegistry,
    keywords_map: dict[str, Sequence[str]] | None = None,
) -> list[str]:
    """Select appropriate skills based on keyword matching against the task description.

    Args:
        task_description: Free-form description of the user goal or task.
        registry: Initialized SkillRegistry instance containing available skills.
        keywords_map: Optional custom mapping of skill names to trigger keywords.

    Returns:
        List of matching skill names available in the registry, defaulting to ['planning'].
    """
    mapping = keywords_map or SKILL_KEYWORDS_MAP
    selected: list[str] = []
    task_lower = task_description.lower()

    for skill_name, keywords in mapping.items():
        if any(kw in task_lower for kw in keywords):
            if skill_name in registry.skills and skill_name not in selected:
                selected.append(skill_name)

    if not selected:
        # Default fallback to planning if available, or first available skill
        if "planning" in registry.skills:
            return ["planning"]
        available = registry.list_skills()
        return [available[0]] if available else ["planning"]

    return selected


def load_skills_for_task(
    task_description: str,
    registry: SkillRegistry | None = None,
) -> dict[str, str]:
    """Identify and load full markdown instructions for skills matching a task.

    Args:
        task_description: Task description string.
        registry: Optional SkillRegistry instance. If None, uses default singleton.

    Returns:
        Dictionary mapping skill name to loaded markdown content.
    """
    reg = registry or get_skill_registry()
    chosen_names = select_skills_for_task(task_description, reg)
    loaded: dict[str, str] = {}
    for name in chosen_names:
        loaded[name] = reg.load_skill(name)
    return loaded
