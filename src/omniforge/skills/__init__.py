"""Agent skills management and progressive disclosure system."""
from omniforge.skills.registry import SkillMetadata, SkillRegistry
from omniforge.skills.loader import (
    get_skill_registry,
    select_skills_for_task,
    load_skills_for_task,
    reset_skill_registry,
)

__all__ = [
    "SkillMetadata",
    "SkillRegistry",
    "get_skill_registry",
    "select_skills_for_task",
    "load_skills_for_task",
    "reset_skill_registry",
]
