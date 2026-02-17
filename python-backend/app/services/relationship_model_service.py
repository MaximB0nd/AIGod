"""
Сервис для интеграции relationship_model с комнатами.

Хранит RelationshipManager на каждую комнату, синхронизирует начальное состояние с БД.
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.database.sqlite_setup import SessionLocal
from app.models.relationship import Relationship as DBRelationship
from app.services.relationship_model import RelationshipManager


def _sync_from_db(manager: RelationshipManager, room_id: int, agent_by_id: dict) -> None:
    """Загрузить отношения из БД в RelationshipManager (БД хранит неориентированные пары)."""
    session: Session = SessionLocal()
    try:
        rels = session.query(DBRelationship).filter(DBRelationship.room_id == room_id).all()
        for r in rels:
            name1 = agent_by_id.get(r.agent1_id)
            name2 = agent_by_id.get(r.agent2_id)
            if name1 and name2:
                # БД: неориентированное ребро, relationship-model: ориентированное — задаём оба направления
                for from_n, to_n in [(name1, name2), (name2, name1)]:
                    current = manager.get_relationship_value(from_n, to_n)
                    delta = r.sympathy_value - current
                    if abs(delta) > 1e-6:
                        manager.update_relationship(from_n, to_n, delta, reason="sync_from_db", source="db")
    finally:
        session.close()


def get_or_create_relationship_manager(room) -> RelationshipManager:
    """
    Получить или создать RelationshipManager для комнаты.

    Регистрирует агентов и синхронизирует с БД.
    """
    room_id = room.id
    agent_by_id = {a.id: a.name for a in room.agents}
    agent_names = list(agent_by_id.values())

    manager = RelationshipManager(analyzer=None)
    manager.register_participants(agent_names)
    _sync_from_db(manager, room_id, agent_by_id)

    return manager


# Реестр: room_id -> RelationshipManager (in-memory, без persistence между запросами)
# Для полной персистентности нужно сохранять в БД при каждом изменении
_registry: dict[int, RelationshipManager] = {}


def get_relationship_manager(room) -> RelationshipManager:
    """
    Получить RelationshipManager для комнаты.
    Создаёт новый при каждом вызове и синкает с БД — данные из relationship-model
    дополняются актуальными значениями из БД (relationships table).
    """
    return get_or_create_relationship_manager(room)
