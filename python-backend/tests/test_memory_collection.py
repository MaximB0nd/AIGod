"""
Тесты сбора данных для памяти агентов.

Проверяет:
1. API корректно возвращает воспоминания из SQL-таблицы Memory
2. Запись в SQL Memory работает (когда кто-то пишет)
3. Цепочка сбора: сообщение → memory integration → куда сохраняется?
4. Выявлена ли проблема: context_memory пишет в ChromaDB/in-memory, API читает из SQL
"""
import os
import unittest.mock as mock
import pytest

# In-memory DB до импортов, ChromaDB в /tmp для тестов
os.environ["SQLITE_DB_PATH"] = ":memory:"
os.environ.setdefault("CHROMA_PERSIST_DIR", "/tmp/aigod_test_chroma")


@pytest.fixture
def db_session():
    """Чистая in-memory сессия."""
    from app.database.sqlite_setup import SessionLocal, Base, engine
    from app.models import agent, event, memory, message, plan, relationship, room, user  # noqa: F401

    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def test_user(db_session):
    from app.models.user import User
    from app.utils.auth import get_password_hash
    user = User(
        email="memtest@example.com",
        username="memuser",
        hashed_password=get_password_hash("password123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    from app.utils.auth import create_access_token
    from app.config import config
    from datetime import timedelta
    token = create_access_token(
        data={"sub": test_user.email},
        expires_delta=timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def room_with_agent(db_session, test_user):
    from app.models.room import Room
    from app.models.agent import Agent

    room = Room(
        name="Тест памяти",
        description="Для проверки сбора",
        user_id=test_user.id,
    )
    db_session.add(room)
    db_session.flush()

    agent = Agent(
        name="Копатыч",
        personality="Добрый медведь",
        state_vector={"mood": "neutral", "mood_level": 0.5},
        user_id=test_user.id,
    )
    db_session.add(agent)
    db_session.flush()

    room.agents.append(agent)
    db_session.commit()
    db_session.refresh(room)
    db_session.refresh(agent)
    return room, agent


@pytest.fixture
def app_client(db_session, room_with_agent, auth_headers):
    from app.main import app
    from app.database.sqlite_setup import get_db
    from fastapi.testclient import TestClient

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.headers.update(auth_headers)
    yield client
    app.dependency_overrides.clear()


class TestMemoryApiReadPath:
    """API корректно читает воспоминания из SQL Memory."""

    def test_agent_full_out_returns_key_memories_when_present(
        self, db_session, room_with_agent, app_client
    ):
        """Если в Memory есть записи — API возвращает keyMemories."""
        from app.models.memory import Memory

        room, agent = room_with_agent
        db_session.add(
            Memory(
                agent_id=agent.id,
                room_id=room.id,
                content="Пользователь спросил про урожай. Я ответил про мёд.",
                importance=0.8,
            )
        )
        db_session.add(
            Memory(
                agent_id=agent.id,
                room_id=room.id,
                content="Вспомнил прошлый разговор о пчёлах.",
                importance=0.6,
            )
        )
        db_session.commit()

        r = app_client.get(f"/api/rooms/{room.id}/agents/{agent.id}")
        assert r.status_code == 200
        data = r.json()
        assert "keyMemories" in data
        assert len(data["keyMemories"]) == 2
        assert "Пользователь спросил" in data["keyMemories"][0]["content"]
        assert data["keyMemories"][0]["importance"] == 0.8

    def test_agent_full_out_returns_empty_memories_when_none(
        self, room_with_agent, app_client
    ):
        """Если записей нет — keyMemories пустой массив."""
        room, agent = room_with_agent
        r = app_client.get(f"/api/rooms/{room.id}/agents/{agent.id}")
        assert r.status_code == 200
        data = r.json()
        assert "keyMemories" in data
        assert data["keyMemories"] == []

    def test_get_agent_memories_endpoint_returns_stored_memories(
        self, db_session, room_with_agent, app_client
    ):
        """GET /agents/{id}/memories возвращает записи из SQL."""
        from app.models.memory import Memory

        room, agent = room_with_agent
        db_session.add(
            Memory(
                agent_id=agent.id,
                room_id=room.id,
                content="Тестовое воспоминание",
                importance=0.9,
            )
        )
        db_session.commit()

        r = app_client.get(
            f"/api/rooms/{room.id}/agents/{agent.id}/memories",
            params={"limit": 10, "offset": 0},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert len(data["memories"]) == 1
        assert data["memories"][0]["content"] == "Тестовое воспоминание"
        assert data["memories"][0]["importance"] == 0.9


class TestMemoryWritePath:
    """Проверка записи в память — есть ли цепочка от сообщений до SQL Memory."""

    def test_sql_memory_table_populated_by_message_flow(
        self, db_session, room_with_agent, app_client
    ):
        """
        После обмена сообщениями таблица Memory заполняется.

        _update_room_services_on_message теперь пишет в SQL Memory,
        поэтому API keyMemories возвращает данные.
        """
        import time
        from app.models.memory import Memory

        room, agent = room_with_agent

        # Отправляем сообщение в чат (без реального LLM — мокаем)
        with mock.patch(
            "app.routers.room_agents.get_agent_response",
            return_value="Привет! Я Копатыч, рад тебя видеть.",
        ):
            r = app_client.post(
                f"/api/rooms/{room.id}/agents/{agent.id}/messages",
                json={"text": "Привет!", "sender": "user"},
            )
            assert r.status_code == 200

        # Даём время фоновой задаче _update_room_services_on_message завершиться
        time.sleep(0.5)
        db_session.expire_all()
        count = db_session.query(Memory).filter(
            Memory.agent_id == agent.id,
            Memory.room_id == room.id,
        ).count()
        assert count >= 1, (
            "После сообщения SQL Memory должна содержать запись от агента. "
            "Проверьте _update_room_services_on_message и _write_agent_memory_to_sql."
        )
        mem = db_session.query(Memory).filter(
            Memory.agent_id == agent.id,
            Memory.room_id == room.id,
        ).first()
        assert "Копатыч" in mem.content or "Привет" in mem.content

    def test_manual_memory_insert_then_api_returns_it(
        self, db_session, room_with_agent, app_client
    ):
        """Ручная вставка в Memory — API видит данные. Читающий путь работает."""
        from app.models.memory import Memory

        room, agent = room_with_agent
        m = Memory(
            agent_id=agent.id,
            room_id=room.id,
            content="Вручную добавленное воспоминание",
            importance=0.7,
        )
        db_session.add(m)
        db_session.commit()

        r = app_client.get(f"/api/rooms/{room.id}/agents/{agent.id}")
        assert r.status_code == 200
        assert any(
            "Вручную добавленное" in mem["content"]
            for mem in r.json()["keyMemories"]
        )


class TestContextMemoryIntegration:
    """Проверка, что context_memory (MemoryManager) получает данные."""

    @pytest.mark.asyncio
    async def test_memory_integration_on_agent_message_stores_internally(
        self, room_with_agent
    ):
        """
        MemoryOrchestrationIntegration.on_agent_message сохраняет в MemoryManager.
        Данные попадают в short_term и context_window, но НЕ в SQL Memory.
        """
        from app.services.room_services_registry import get_memory_integration

        room, agent = room_with_agent
        integration = get_memory_integration(room)
        if integration is None:
            pytest.skip("Memory integration не инициализирована")

        result = await integration.on_agent_message(
            message="Агент ответил: да, я помню этот разговор.",
            sender=agent.name,
            conversation_id=f"room_{room.id}",
            metadata={"room_id": room.id},
        )
        assert "memory_id" in result
        assert "context_window_size" in result
        assert integration.stats["messages_processed"] >= 1
        assert integration.stats["memories_created"] >= 1

        # Данные должны быть в MemoryManager
        assert len(integration.memory_manager.short_term) >= 1
        assert len(integration.memory_manager.context_window.messages) >= 1

    @pytest.mark.asyncio
    async def test_memory_integration_on_user_message_stores(
        self, room_with_agent
    ):
        """on_user_message тоже сохраняет в MemoryManager."""
        from app.services.room_services_registry import get_memory_integration

        room, agent = room_with_agent
        integration = get_memory_integration(room)
        if integration is None:
            pytest.skip("Memory integration не инициализирована")

        await integration.on_user_message(
            message="Привет, как дела?",
            conversation_id=f"room_{room.id}",
            participants=[agent.name],
        )
        assert integration.stats["messages_processed"] >= 1
        assert len(integration.memory_manager.short_term) >= 1


class TestMemoryModelAndGapDirect:
    """Быстрые unit-тесты без загрузки приложения."""

    def test_memory_model_structure(self, db_session):
        """Memory (SQL) сохраняет и читает данные."""
        from app.models.memory import Memory
        from app.models.agent import Agent
        from app.models.room import Room
        from app.models.user import User
        from app.utils.auth import get_password_hash

        user = User(
            email="u@x.com",
            username="u",
            hashed_password=get_password_hash("p"),
        )
        db_session.add(user)
        db_session.flush()
        room = Room(name="R", user_id=user.id)
        db_session.add(room)
        db_session.flush()
        agent = Agent(name="A", personality="P", user_id=user.id)
        db_session.add(agent)
        db_session.flush()
        room.agents.append(agent)
        db_session.commit()

        m = Memory(
            agent_id=agent.id,
            room_id=room.id,
            content="Тест",
            importance=0.9,
        )
        db_session.add(m)
        db_session.commit()

        read = db_session.query(Memory).filter(Memory.agent_id == agent.id).first()
        assert read is not None
        assert read.content == "Тест"
        assert read.importance == 0.9

    def test_context_memory_stores_internally_only(
        self, db_session, room_with_agent
    ):
        """
        MemoryOrchestrationIntegration.on_agent_message сохраняет в MemoryManager.
        SQL Memory пишется отдельно из _update_room_services_on_message.
        """
        from app.models.memory import Memory
        from app.services.room_services_registry import get_memory_integration
        import asyncio

        room, agent = room_with_agent
        integration = get_memory_integration(room)
        if integration is None:
            pytest.skip("Memory integration недоступна")

        # Прямой вызов on_agent_message — без моста в room_agents
        asyncio.run(
            integration.on_agent_message(
                "Ответ агента",
                agent.name,
                f"room_{room.id}",
                metadata={"room_id": room.id},
            )
        )
        # Интеграция не пишет в SQL — это делает _update_room_services_on_message
        count = db_session.query(Memory).filter(
            Memory.agent_id == agent.id,
        ).count()
        assert count == 0


class TestMemoryCollectionGap:
    """
    Сводный тест: есть ли разрыв между записью и чтением.
    """

    def test_sql_memory_populated_via_update_room_services(
        self, db_session, room_with_agent
    ):
        """
        _update_room_services_on_message пишет в SQL Memory.
        API (GET /agents/{id}) читает из SQL — данные доступны.
        """
        from app.models.memory import Memory
        from app.routers.room_agents import _update_room_services_on_message

        room, agent = room_with_agent

        sql_before = db_session.query(Memory).filter(
            Memory.agent_id == agent.id,
        ).count()
        assert sql_before == 0

        # Вызываем напрямую (как после обмена сообщениями)
        _update_room_services_on_message(
            room_id=room.id,
            agents=list(room.agents),
            user_text="Привет",
            user_sender="user",
            agent_response="Тестовый ответ агента",
            agent_name=agent.name,
        )

        db_session.expire_all()
        sql_after = db_session.query(Memory).filter(
            Memory.agent_id == agent.id,
        ).count()
        assert sql_after >= 1, "SQL Memory должна содержать запись после _update_room_services_on_message"
