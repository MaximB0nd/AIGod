"""
Фикстуры для тестов.
Используется in-memory SQLite и моки для изоляции от внешних сервисов (Yandex API).
"""
# Важно: до импорта app задать in-memory БД
import os
os.environ["SQLITE_DB_PATH"] = ":memory:"

from typing import Generator

import pytest


@pytest.fixture(scope="function")
def db_session():
    """Сессия БД (in-memory). Перед каждым тестом — чистая БД."""
    from app.database.sqlite_setup import SessionLocal, Base, engine
    # Импорт моделей — регистрирует таблицы в Base.metadata
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


@pytest.fixture(scope="function")
def app_with_test_db(db_session):
    """Приложение с подменой get_db на тестовую сессию."""
    from app.main import app
    from app.database.sqlite_setup import get_db

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def client(app_with_test_db):
    from fastapi.testclient import TestClient
    return TestClient(app_with_test_db)


@pytest.fixture
def test_user(db_session):
    """Создать пользователя для тестов."""
    from app.models.user import User
    from app.utils.auth import get_password_hash
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("password123"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Bearer token для авторизованных запросов."""
    from app.utils.auth import create_access_token
    from app.config import config
    from datetime import timedelta
    token = create_access_token(
        data={"sub": test_user.email},
        expires_delta=timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_room(db_session, test_user):
    """Комната пользователя."""
    from app.models.room import Room
    room = Room(name="Тестовая комната", description="Для тестов", user_id=test_user.id)
    db_session.add(room)
    db_session.commit()
    db_session.refresh(room)
    return room


@pytest.fixture
def test_agent(db_session):
    """Агент для тестов (не привязан к комнате)."""
    from app.models.agent import Agent
    agent = Agent(
        name="Копатыч",
        personality="Ты Копатыч из Смешариков. Добрый медведь-огородник.",
        state_vector={"mood": "neutral", "mood_level": 0.5},
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


@pytest.fixture
def room_with_agent(db_session, test_room, test_agent):
    """Комната с добавленным агентом."""
    test_room.agents.append(test_agent)
    db_session.commit()
    db_session.refresh(test_room)
    return test_room, test_agent
