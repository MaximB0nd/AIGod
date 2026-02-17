"""
События оркестрации.

UserMessageEvent — сообщение пользователя в комнату.
Попадает в очередь оркестрации → strategy.handle_user_message → агенты отвечают.
"""
from dataclasses import dataclass


@dataclass
class UserMessageEvent:
    """Событие: пользователь отправил сообщение в чат комнаты."""
    room_id: int
    text: str
    sender: str
