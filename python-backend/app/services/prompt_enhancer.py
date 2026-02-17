"""
Обогащение промптов контекстом из сервисов: отношения, память, эмоции.
Используется в llm_service и оркестрации.
"""


def enhance_prompt_with_relationship(
    relationship_manager,
    agent_name: str,
    prompt: str,
) -> str:
    """Добавить в промпт информацию об отношениях агента с другими."""
    if not relationship_manager:
        return prompt
    try:
        rels = relationship_manager.get_entity_relationships(agent_name)
        if not rels:
            return prompt
        lines = ["\n[Твои отношения с другими:]"]
        for other, value in rels.items():
            if other != agent_name:
                rel_type = relationship_manager.get_relationship_type(agent_name, other)
                emoji = _emoji_for_value(value)
                lines.append(f"  {emoji} {other}: {rel_type} ({value:.2f})")
        lines.append("Учитывай эти отношения в ответе.\n")
        return "\n".join(lines) + prompt
    except Exception:
        return prompt


def _emoji_for_value(value: float) -> str:
    if value >= 0.7:
        return "❤️"
    if value >= 0.4:
        return "😊"
    if value >= 0.1:
        return "🙂"
    if value >= -0.1:
        return "😐"
    if value >= -0.4:
        return "😕"
    if value >= -0.7:
        return "😠"
    return "💔"


def enhance_prompt_with_emotional_state(emotional_integration, agent_name: str, prompt: str) -> str:
    """Добавить эмоциональное состояние агента в промпт."""
    if not emotional_integration:
        return prompt
    try:
        return emotional_integration.enhance_prompt_with_emotions(agent_name, prompt)
    except Exception:
        return prompt


def enhance_prompt_with_memory(memory_integration, agent_name: str, prompt: str, query: str | None = None) -> str:
    """Добавить контекст из памяти в промпт."""
    if not memory_integration:
        return prompt
    try:
        return memory_integration.enhance_prompt_with_context(agent_name, prompt, query)
    except Exception:
        return prompt
