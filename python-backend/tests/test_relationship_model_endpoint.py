"""
Тесты для эндпоинта GET /relationship-model.
"""
import pytest
from fastapi.testclient import TestClient


def test_get_relationship_model_returns_graph_and_stats(
    client: TestClient,
    auth_headers: dict,
    room_with_agent: tuple,
):
    """Эндпоинт возвращает граф, историю, статистику и маппинг agent_ids."""
    room, agent = room_with_agent

    response = client.get(
        f"/api/rooms/{room.id}/relationship-model",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "graph" in data
    assert "history" in data
    assert "stats" in data
    assert "agent_ids" in data
    assert data["agent_ids"].get(agent.name) == str(agent.id)
    assert "nodes" in data["graph"]
    assert "edges" in data["graph"]
    assert "stats" in data["graph"]


def test_get_relationship_model_401_without_auth(client: TestClient, room_with_agent):
    """Без авторизации возвращается 401."""
    room, _ = room_with_agent

    response = client.get(
        f"/api/rooms/{room.id}/relationship-model",
    )

    assert response.status_code == 401


def test_get_relationship_model_404_wrong_room(client: TestClient, auth_headers: dict):
    """Чужая комната — 404."""
    response = client.get(
        "/api/rooms/99999/relationship-model",
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_get_emotional_state(client: TestClient, auth_headers: dict, room_with_agent):
    """Эндпоинт emotional-state возвращает данные по агентам."""
    room, agent = room_with_agent

    response = client.get(
        f"/api/rooms/{room.id}/emotional-state",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "agent_ids" in data
    assert "states" in data
    assert agent.name in data.get("agent_ids", {})


def test_get_context_memory(client: TestClient, auth_headers: dict, room_with_agent):
    """Эндпоинт context-memory возвращает контекст памяти."""
    room, _ = room_with_agent

    response = client.get(
        f"/api/rooms/{room.id}/context-memory",
        headers=auth_headers,
    )

    # Может вернуть summary/stats или message о недоступности
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data or "message" in data or "error" in data
