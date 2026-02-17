"""
Тесты для orchestration_type в комнатах.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def room_with_agent_circular(db_session, test_user, room_with_agent):
    """Комната с orchestration_type=circular и агентом."""
    room, agent = room_with_agent
    room.orchestration_type = "circular"
    db_session.commit()
    db_session.refresh(room)
    return room, agent


def test_create_room_with_orchestration_type(client: TestClient, auth_headers: dict):
    """Создание комнаты с выбором типа оркестрации."""
    response = client.post(
        "/api/rooms",
        json={
            "name": "Комната циркуляр",
            "description": "Тест",
            "orchestration_type": "circular",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["orchestration_type"] == "circular"
    assert data["name"] == "Комната циркуляр"


def test_create_room_default_orchestration_type(client: TestClient, auth_headers: dict):
    """Без orchestration_type — по умолчанию single."""
    response = client.post(
        "/api/rooms",
        json={"name": "Простая комната"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["orchestration_type"] == "single"


def test_update_room_description_and_speed(client: TestClient, auth_headers: dict, test_room):
    """Обновление описания и/или скорости комнаты."""
    response = client.patch(
        f"/api/rooms/{test_room.id}",
        json={"description": "Новое описание", "speed": 2.0},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Новое описание"
    assert response.json()["speed"] == 2.0


def test_update_room_only_description(client: TestClient, auth_headers: dict, test_room):
    """Частичное обновление: только описание."""
    response = client.patch(
        f"/api/rooms/{test_room.id}",
        json={"description": "Только описание"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Только описание"


def test_update_room_only_speed(client: TestClient, auth_headers: dict, test_room):
    """Частичное обновление: только скорость."""
    response = client.patch(
        f"/api/rooms/{test_room.id}",
        json={"speed": 0.5},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["speed"] == 0.5


@patch("app.routers.room_agents.get_agent_response")
def test_send_message_calls_llm_for_single_mode(
    mock_get_response,
    client: TestClient,
    auth_headers: dict,
    room_with_agent,
):
    """В режиме single POST message вызывает get_agent_response (ChatService)."""
    room, agent = room_with_agent
    mock_get_response.return_value = "Ответ"

    response = client.post(
        f"/api/rooms/{room.id}/agents/{agent.id}/messages",
        json={"text": "Привет", "sender": "user"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    mock_get_response.assert_called_once_with(agent, f"room_{room.id}_agent_{agent.id}", "Привет")


@patch("app.routers.room_agents.registry")
def test_send_message_uses_orchestration_for_circular_mode(
    mock_registry,
    client: TestClient,
    auth_headers: dict,
    room_with_agent_circular,
):
    """В режиме circular POST message кладёт сообщение в оркестрацию, не вызывает get_agent_response."""
    room, agent = room_with_agent_circular
    mock_client = MagicMock()
    mock_client.send_user_message = AsyncMock()
    mock_registry.get_or_start = AsyncMock(return_value=mock_client)

    with patch("app.routers.room_agents.get_agent_response") as mock_llm:
        response = client.post(
            f"/api/rooms/{room.id}/agents/{agent.id}/messages",
            json={"text": "Обсудим тему", "sender": "user"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    mock_registry.get_or_start.assert_called_once()
    mock_client.send_user_message.assert_called_once_with("Обсудим тему")
    mock_llm.assert_not_called()
    assert response.json().get("agentResponse") is None
