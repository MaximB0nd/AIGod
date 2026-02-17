"""Утилиты для расчёта mood агента из state_vector."""
MOOD_PRESETS = {
    "happy": {"mood": "happy", "level": 0.8, "icon": "😊", "color": "#4ade80"},
    "neutral": {"mood": "neutral", "level": 0.5, "icon": "😐", "color": "#94a3b8"},
    "sad": {"mood": "sad", "level": 0.2, "icon": "😢", "color": "#f87171"},
    "angry": {"mood": "angry", "level": 0.1, "icon": "😠", "color": "#ef4444"},
    "excited": {"mood": "excited", "level": 0.9, "icon": "🤩", "color": "#eab308"},
}


def get_agent_mood(state_vector: dict | None) -> dict:
    """Извлечь mood из state_vector или вернуть neutral по умолчанию."""
    if not state_vector or "mood" not in state_vector:
        return MOOD_PRESETS["neutral"].copy()
    m = state_vector.get("mood", "neutral")
    preset = MOOD_PRESETS.get(m, MOOD_PRESETS["neutral"]).copy()
    preset["level"] = state_vector.get("mood_level", preset["level"])
    return preset
