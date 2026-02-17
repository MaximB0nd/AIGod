"""
Шаблоны промптов для построения агентов.
Используются при создании новых агентов или генерации personality из краткого описания.
"""
from typing import Optional

# Шаблоны по категориям
AGENT_TEMPLATES = {
    # Базовый шаблон — минимум полей
    "minimal": """Ты {name}.

{character}

Отвечай коротко и в характере.""",

    # Развёрнутый шаблон
    "full": """**Персонаж:** {name}

**Характер и роль:**
{character}

**Стиль речи:** {speech_style}

**Особенности:**
- Отвечай от первого лица.
- Сохраняй тон и манеру персонажа.
- Используй характерные фразы, когда уместно.
""",

    # Шаблон для эксперта/консультанта
    "expert": """Ты {name} — эксперт в области: {expertise}.

**Твоя роль:**
{character}

**Стиль общения:**
- Отвечай по существу.
- Приводи примеры, когда это помогает.
- Если не знаешь — честно скажи.
- Обращайся к пользователю уважительно.
""",

    # Шаблон для персонажа из произведений
    "character": """**Персонаж:** {name}
**Вселенная:** {universe}
**Роль:** {role}

**Характер:**
{character}

**Стиль речи:**
{speech_style}

**Ключевые черты:**
{traits}

**Типичные фразы (используй уместно):**
{phrases}

Отвечай от лица персонажа, сохраняя его личность и манеру общения.""",

    # Шаблон для NPC в игре/симуляции
    "npc": """Ты {name} — персонаж в симуляции.

**Описание:**
{character}

**Мотивация:** {motivation}

**Отношение к игроку:** {attitude}

**Стиль общения:** {speech_style}

Реагируй на действия пользователя в соответствии с характером. Будь естественным.
""",
}

# Значения по умолчанию для недостающих полей
TEMPLATE_DEFAULTS = {
    "speech_style": "естественный, разговорный",
    "traits": "дружелюбный, отзывчивый",
    "phrases": "—",
    "universe": "—",
    "role": "участник событий",
    "expertise": "общие вопросы",
    "motivation": "общаться и помогать",
    "attitude": "дружелюбный",
}


def get_template(name: str) -> str:
    """
    Получить шаблон по имени.

    Args:
        name: ключ из AGENT_TEMPLATES (minimal, full, expert, character, npc)

    Returns:
        Строка шаблона с плейсхолдерами {name}, {character} и др.

    Raises:
        KeyError: если шаблон не найден.
    """
    if name not in AGENT_TEMPLATES:
        raise KeyError(f"Template '{name}' not found. Available: {list(AGENT_TEMPLATES)}")
    return AGENT_TEMPLATES[name]


def build_agent_prompt(
    template_name: str,
    name: str,
    character: str,
    **kwargs,
) -> str:
    """
    Собрать промпт агента из шаблона и параметров.

    Args:
        template_name: ключ шаблона (minimal, full, expert, character, npc)
        name: имя агента
        character: описание характера/роли
        **kwargs: дополнительные поля (speech_style, traits, phrases, universe, role, expertise, motivation, attitude)

    Returns:
        Готовый промпт для personality агента.
    """
    template = get_template(template_name)
    params = {
        "name": name,
        "character": character,
        **TEMPLATE_DEFAULTS,
        **{k: v for k, v in kwargs.items() if v is not None},
    }
    return template.format(**params)


def build_minimal_prompt(name: str, character: str) -> str:
    """Упрощённая сборка для минимального шаблона."""
    return build_agent_prompt("minimal", name=name, character=character)


def build_full_prompt(
    name: str,
    character: str,
    speech_style: Optional[str] = None,
) -> str:
    """Сборка развёрнутого промпта."""
    return build_agent_prompt(
        "full",
        name=name,
        character=character,
        speech_style=speech_style or TEMPLATE_DEFAULTS["speech_style"],
    )
