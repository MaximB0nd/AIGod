"""Роуты для системных промптов и шаблонов агентов."""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.prompts import (
    AGENT_TEMPLATES,
    SYSTEM_PROMPT_BASE,
    get_system_prompt,
    build_agent_prompt,
    get_template,
)

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("/system")
def get_system_prompts():
    """
    Получить доступные системные промпты.
    """
    return {
        "base": SYSTEM_PROMPT_BASE,
        "single": get_system_prompt(mode="single"),
        "orchestration": get_system_prompt(mode="orchestration"),
    }


@router.get("/templates")
def list_templates():
    """
    Список шаблонов для построения агентов.
    """
    return {
        "templates": list(AGENT_TEMPLATES.keys()),
        "descriptions": {
            "minimal": "Минимальный: имя и характер",
            "full": "Развёрнутый: характер и стиль речи",
            "expert": "Эксперт/консультант",
            "character": "Персонаж из произведения",
            "npc": "NPC в игре/симуляции",
        },
    }


@router.get("/templates/{name}")
def get_template_preview(name: str):
    """
    Получить шаблон с плейсхолдерами.
    """
    try:
        template = get_template(name)
        return {"name": name, "template": template}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


class BuildPromptIn(BaseModel):
    """Параметры для сборки промпта из шаблона."""
    template_name: str = Field(..., description="minimal, full, expert, character, npc")
    name: str = Field(..., min_length=1)
    character: str = Field(..., min_length=1)
    speech_style: Optional[str] = None
    traits: Optional[str] = None
    phrases: Optional[str] = None
    universe: Optional[str] = None
    role: Optional[str] = None
    expertise: Optional[str] = None
    motivation: Optional[str] = None
    attitude: Optional[str] = None


@router.post("/build")
def build_from_template(data: BuildPromptIn):
    """
    Собрать промпт агента из шаблона.

    Обязательные поля: template_name, name, character.
    Остальные — по необходимости шаблона.
    """
    kwargs = {
        k: v for k, v in data.model_dump().items()
        if k not in ("template_name", "name", "character") and v is not None
    }
    try:
        prompt = build_agent_prompt(
            data.template_name,
            name=data.name,
            character=data.character,
            **kwargs,
        )
        return {"prompt": prompt, "template": data.template_name}
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))
