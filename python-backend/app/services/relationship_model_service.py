"""
Сервис для интеграции relationship_model с комнатами.

Хранит RelationshipManager на каждую комнату, синхронизирует начальное состояние с БД.
"""
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.database.sqlite_setup import SessionLocal
from app.models.relationship import Relationship as DBRelationship
from app.services.relationship_model import RelationshipManager

logger = logging.getLogger("aigod.relationship_model")


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
    Использует HeuristicRelationshipAnalyzer для обновления графа без LLM.
    """
    from app.services.relationship_model.heuristic_analyzer import HeuristicRelationshipAnalyzer

    room_id = room.id
    agent_by_id = {a.id: a.name for a in room.agents}
    agent_names = list(agent_by_id.values())

    analyzer = HeuristicRelationshipAnalyzer(influence_coefficient=0.3)
    manager = RelationshipManager(analyzer=analyzer)
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


async def sync_graph_to_db_and_broadcast(room, manager: RelationshipManager) -> None:
    """
    Сохранить граф RelationshipManager в БД и разослать обновления через WebSocket.
    Создаёт строки для ВСЕХ пар агентов комнаты (0.0 если нет данных) — чтобы фронтенд видел отношения.
    """
    from app.ws import broadcast_graph_edge

    room_id = room.id
    agents = list(room.agents)
    name_to_id = {a.name: a.id for a in agents}
    agent_ids = list(name_to_id.values())
    session: Session = SessionLocal()
    seen_pairs: set[tuple[int, int]] = set()
    try:
        # 1. Сначала создаём/обновляем все пары агентов (чтобы фронтенд видел отношения даже без сообщений)
        for i, a1 in enumerate(agent_ids):
            for a2 in agent_ids[i + 1 :]:
                if a1 == a2:
                    continue
                a_lo, a_hi = min(a1, a2), max(a1, a2)
                if (a_lo, a_hi) in seen_pairs:
                    continue
                seen_pairs.add((a_lo, a_hi))
                db_rel = session.query(DBRelationship).filter(
                    DBRelationship.room_id == room_id,
                    DBRelationship.agent1_id == a_lo,
                    DBRelationship.agent2_id == a_hi,
                ).first()
                if not db_rel:
                    session.add(DBRelationship(
                        room_id=room_id,
                        agent1_id=a_lo,
                        agent2_id=a_hi,
                        sympathy_value=0.0,
                        interaction_count=0,
                    ))

        # 2. Обновляем значения из графа (анализ сообщений)
        graph_seen: set[tuple[int, int]] = set()
        for from_name, targets in manager.graph.edges.items():
            from_id = name_to_id.get(from_name)
            if not from_id:
                continue
            for to_name, rel in targets.items():
                to_id = name_to_id.get(to_name)
                if not to_id or from_id == to_id:
                    continue
                a1, a2 = min(from_id, to_id), max(from_id, to_id)
                if (a1, a2) in graph_seen:
                    continue
                graph_seen.add((a1, a2))
                val = (manager.get_relationship_value(from_name, to_name) + manager.get_relationship_value(to_name, from_name)) / 2.0
                db_rel = session.query(DBRelationship).filter(
                    DBRelationship.room_id == room_id,
                    DBRelationship.agent1_id == a1,
                    DBRelationship.agent2_id == a2,
                ).first()
                if db_rel:
                    db_rel.sympathy_value = round(val, 4)
                    db_rel.interaction_count = (db_rel.interaction_count or 0) + 1
                else:
                    session.add(DBRelationship(
                        room_id=room_id,
                        agent1_id=a1,
                        agent2_id=a2,
                        sympathy_value=round(val, 4),
                        interaction_count=1,
                    ))
                await broadcast_graph_edge(room_id, str(a1), str(a2), round(val, 4))
        session.commit()
    except Exception as e:
        session.rollback()
        logger.warning("sync_graph_to_db_and_broadcast: %s", e)
    finally:
        session.close()
