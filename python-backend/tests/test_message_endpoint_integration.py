"""
Интеграционные тесты для POST /api/rooms/{roomId}/agents/{agentId}/messages.
Проверяют связь эндпоинта с llm_service (мок) и сохранение в БД.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@patch("app.routers.room_agents.get_agent_response")
def test_send_message_returns_agent_response(
    mock_get_response,
    client: TestClient,
    auth_headers: dict,
    room_with_agent,
):
    """Эндпоинт вызывает get_agent_response и возвращает agentResponse в ответе."""
    room, agent = room_with_agent
    mock_get_response.return_value = "Ребяты, вы чего? Честное слово, привет!"

    response = client.post(
        f"/api/rooms/{room.id}/agents/{agent.id}/messages",
        json={"text": "Привет, Копатыч!", "sender": "user"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["text"] == "Привет, Копатыч!"
    assert data["agentResponse"] == "Ребяты, вы чего? Честное слово, привет!"
    assert data["agentId"] == str(agent.id)

    mock_get_response.assert_called_once()
    call_args = mock_get_response.call_args[0]
    assert call_args[1] == f"room_{room.id}_agent_{agent.id}"
    assert call_args[2] == "Привет, Копатыч!"


@patch("app.routers.room_agents.get_agent_response")
def test_send_message_saves_both_messages_to_db(
    mock_get_response,
    client: TestClient,
    auth_headers: dict,
    room_with_agent,
    db_session,
):
    """Сохраняются сообщение пользователя и ответ агента в БД."""
    from app.models.message import Message

    room, agent = room_with_agent
    mock_get_response.return_value = "Укуси меня пчела! Здравствуй!"

    client.post(
        f"/api/rooms/{room.id}/agents/{agent.id}/messages",
        json={"text": "Привет!", "sender": "user"},
        headers=auth_headers,
    )

    messages = db_session.query(Message).filter(Message.room_id == room.id).order_by(Message.id).all()
    assert len(messages) >= 2
    assert messages[0].text == "Привет!"
    assert messages[0].sender == "user"
    assert messages[1].text == "Укуси меня пчела! Здравствуй!"
    assert messages[1].sender == agent.name


@patch("app.routers.room_agents.get_agent_response")
def test_send_message_404_if_agent_not_in_room(
    mock_get_response,
    client: TestClient,
    auth_headers: dict,
    test_room,
    test_agent,
):
    """404 если агент не добавлен в комнату."""
    # test_room без агента, test_agent существует но не в комнате
    mock_get_response.return_value = "..."

    response = client.post(
        f"/api/rooms/{test_room.id}/agents/{test_agent.id}/messages",
        json={"text": "Привет", "sender": "user"},
        headers=auth_headers,
    )

    assert response.status_code == 404
    mock_get_response.assert_not_called()


def test_send_message_401_without_auth(client: TestClient, room_with_agent):
    """401 без Bearer token."""
    room, agent = room_with_agent
    response = client.post(
        f"/api/rooms/{room.id}/agents/{agent.id}/messages",
        json={"text": "Привет", "sender": "user"},
    )
    assert response.status_code == 401


@patch("app.routers.room_agents.broadcast_chat_message")
@patch("app.routers.room_agents.get_agent_response")
def test_send_message_triggers_websocket_broadcast(
    mock_get_response,
    mock_broadcast,
    client: TestClient,
    auth_headers: dict,
    room_with_agent,
):
    """Broadcast в WebSocket вызывается с payload, содержащим agentResponse."""
    room, agent = room_with_agent
    mock_get_response.return_value = "Ответ для рассылки"

    client.post(
        f"/api/rooms/{room.id}/agents/{agent.id}/messages",
        json={"text": "Сообщение", "sender": "user"},
        headers=auth_headers,
    )

    mock_broadcast.assert_called_once()
    call_args = mock_broadcast.call_args
    assert call_args[0][0] == room.id  # room_id
    payload = call_args[0][1]
    assert payload["text"] == "Сообщение"
    assert payload["agentResponse"] == "Ответ для рассылки"
