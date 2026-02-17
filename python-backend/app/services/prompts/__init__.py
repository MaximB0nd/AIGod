"""
Системные промпты и шаблоны для построения агентов.
"""
from .system_prompts import (
    SYSTEM_PROMPT_BASE,
    SYSTEM_PROMPT_ORCHESTRATION,
    SYSTEM_PROMPT_SINGLE,
    get_system_prompt,
)
from .agent_templates import (
    AGENT_TEMPLATES,
    build_agent_prompt,
    build_minimal_prompt,
    build_full_prompt,
    get_template,
)

__all__ = [
    "SYSTEM_PROMPT_BASE",
    "SYSTEM_PROMPT_ORCHESTRATION",
    "SYSTEM_PROMPT_SINGLE",
    "get_system_prompt",
    "AGENT_TEMPLATES",
    "build_agent_prompt",
    "build_minimal_prompt",
    "build_full_prompt",
    "get_template",
]
