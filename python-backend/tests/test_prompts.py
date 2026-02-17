"""Тесты для эндпоинтов промптов и шаблонов."""
from fastapi.testclient import TestClient


def test_get_system_prompts(client: TestClient):
    """GET /api/prompts/system возвращает системные промпты."""
    response = client.get("/api/prompts/system")
    assert response.status_code == 200
    data = response.json()
    assert "base" in data
    assert "single" in data
    assert "orchestration" in data
    assert "персонаж" in data["base"].lower()


def test_list_templates(client: TestClient):
    """GET /api/prompts/templates возвращает список шаблонов."""
    response = client.get("/api/prompts/templates")
    assert response.status_code == 200
    data = response.json()
    assert "templates" in data
    assert "minimal" in data["templates"]
    assert "full" in data["templates"]


def test_get_template(client: TestClient):
    """GET /api/prompts/templates/minimal возвращает шаблон."""
    response = client.get("/api/prompts/templates/minimal")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "minimal"
    assert "{name}" in data["template"]
    assert "{character}" in data["template"]


def test_build_from_template(client: TestClient):
    """POST /api/prompts/build собирает промпт из шаблона."""
    response = client.post(
        "/api/prompts/build",
        json={
            "template_name": "minimal",
            "name": "Тестовый агент",
            "character": "Добрый помощник.",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "prompt" in data
    assert "Тестовый агент" in data["prompt"]
    assert "Добрый помощник" in data["prompt"]
    assert data["template"] == "minimal"
