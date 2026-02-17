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
