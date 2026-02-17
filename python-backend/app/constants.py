"""
Константы приложения.
"""
from enum import Enum


class OrchestrationType(str, Enum):
    """Типы паттернов взаимодействия агентов в комнате."""

    SINGLE = "single"  # Пользователь общается с одним агентом
    CIRCULAR = "circular"  # Агенты общаются по кругу, пользователь может вмешаться
    NARRATOR = "narrator"  # Агент-рассказчик управляет повествованием
    FULL_CONTEXT = "full_context"  # Полный контекст для всех агентов


ORCHESTRATION_TYPE_DEFAULT = OrchestrationType.SINGLE.value
