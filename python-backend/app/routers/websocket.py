"""WebSocket для потока событий комнаты."""
import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/rooms", tags=["websocket"])


@router.websocket("/{room_id}/stream")
async def room_stream(
    websocket: WebSocket,
    room_id: int,
    token: str = Query(None),
):
    """
    WebSocket поток событий комнаты.
    Подключение: ws://.../api/rooms/{roomId}/stream?token=JWT
    """
    await websocket.accept()

    try:
        # Заглушка: полная версия с очередью событий будет позже
        await websocket.send_json({
            "type": "info",
            "payload": {
                "message": f"Подключено к комнате {room_id}. Поток событий в реальном времени будет реализован с очередью сообщений.",
                "roomId": str(room_id),
            },
        })
        # Держим соединение открытым, ждём сообщения от клиента
        while True:
            data = await websocket.receive_text()
            # Эхо или обработка команд
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "payload": {}})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
