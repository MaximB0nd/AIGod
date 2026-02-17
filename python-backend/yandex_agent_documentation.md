# README: Система AI-агентов для FastAPI

## Описание

Готовая система для интеграции AI-агентов (персонажей) на базе YandexGPT в FastAPI приложение. Позволяет создавать эндпоинты для общения с разными AI-персонажами, каждый из которых имеет уникальный характер и промпт.

## Быстрый старт за 5 минут

### 1. Установка

```bash
pip install fastapi uvicorn python-dotenv yandex-ai-studio-sdk

2. Структура проекта
text

fastapi-agents/
├── .env                    # Твои ключи (не в git)
├── .env.example            # Пример для других разработчиков
├── agents.py               # Код системы агентов
├── main.py                 # FastAPI приложение
└── README.md               # Этот файл

3. Настройка окружения

Создай файл .env:
env

YANDEX_CLOUD_FOLDER=b1gqf7r7l4hfhjdhfjkdhf
YANDEX_CLOUD_API_KEY=AQVN1orPXF7kjsdhfkjsdhfkjsdhfkjsdhf

Создай .env.example для других:
env

YANDEX_CLOUD_FOLDER=your_folder_id_here
YANDEX_CLOUD_API_KEY=your_api_key_here

4. Код системы агентов

Создай файл agents.py:
python

"""
Модуль AI-агентов для FastAPI
"""

import os
from typing import Dict
from dotenv import load_dotenv
from yandex_ai_studio_sdk import AIStudio

load_dotenv()

YANDEX_CLOUD_FOLDER = os.getenv("YANDEX_CLOUD_FOLDER")
YANDEX_CLOUD_API_KEY = os.getenv("YANDEX_CLOUD_API_KEY")
TEMPERATURE = 0.5


class YandexAgentClient:
    """Клиент для работы с YandexGPT API"""
    
    def __init__(self):
        if not YANDEX_CLOUD_FOLDER or not YANDEX_CLOUD_API_KEY:
            raise ValueError("YANDEX_CLOUD_FOLDER и YANDEX_CLOUD_API_KEY должны быть заданы в .env")
        
        # Очищаем ключ от возможного префикса
        clean_api_key = YANDEX_CLOUD_API_KEY.replace("Api-Key ", "").strip()
        
        self.sdk = AIStudio(
            folder_id=YANDEX_CLOUD_FOLDER,
            auth=clean_api_key
        )
        
        self.assistants: Dict[str, any] = {}
        self.threads: Dict[str, any] = {}
    
    def _get_or_create_assistant(self, agent):
        """Получает или создает ассистента"""
        if agent.name not in self.assistants:
            model = self.sdk.models.completions("yandexgpt")
            model = model.configure(temperature=TEMPERATURE)
            
            self.assistants[agent.name] = self.sdk.assistants.create(
                model=model,
                instruction=agent.prompt,
                name=agent.name
            )
        return self.assistants[agent.name]
    
    def _get_or_create_thread(self, session_id: str):
        """Получает или создает тред (сессию диалога)"""
        if session_id not in self.threads:
            self.threads[session_id] = self.sdk.threads.create()
        return self.threads[session_id]
    
    def send_message(self, agent, session_id: str, text: str) -> str:
        """
        Отправляет сообщение и возвращает ответ
        
        Args:
            agent: объект Agent
            session_id: ID сессии пользователя
            text: текст сообщения
            
        Returns:
            str: ответ ассистента
        """
        try:
            assistant = self._get_or_create_assistant(agent)
            thread = self._get_or_create_thread(session_id)
            
            # Создаем сообщение пользователя
            self.sdk.messages.create(
                thread_id=thread.id,
                role="user",
                text=text
            )
            
            # Запускаем обработку
            run = self.sdk.runs.create(
                assistant_id=assistant.id,
                thread_id=thread.id
            )
            
            run.wait()
            
            # Получаем ответ
            messages = self.sdk.messages.list(thread_id=thread.id)
            
            for message in messages:
                if message.role == "assistant":
                    return message.text
            
            return "Извините, не удалось получить ответ"
            
        except Exception as e:
            print(f"Ошибка: {e}")
            return "Произошла ошибка при обработке запроса"


class Agent:
    """Класс для создания AI-персонажа"""
    
    def __init__(self, name: str, prompt: str):
        """
        Args:
            name: имя агента (должно быть уникальным)
            prompt: системный промпт, определяющий характер
        """
        self.name = name
        self.prompt = prompt


# Создаем единственный экземпляр клиента для всего приложения
agent_client = YandexAgentClient()

5. FastAPI приложение

Создай файл main.py:
python

"""
FastAPI приложение с AI-агентами
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
from agents import Agent, agent_client

app = FastAPI(title="AI Agents API", description="API для общения с AI-персонажами")

# ============================================
# МОДЕЛИ ДАННЫХ
# ============================================

class MessageRequest(BaseModel):
    """Модель запроса на отправку сообщения"""
    agent_name: str
    session_id: str
    message: str

class MessageResponse(BaseModel):
    """Модель ответа"""
    response: str
    agent_name: str
    session_id: str

class CreateAgentRequest(BaseModel):
    """Модель для создания нового агента"""
    name: str
    prompt: str

class AgentResponse(BaseModel):
    """Модель ответа с информацией об агенте"""
    name: str
    prompt: str
    message: str

# ============================================
# ХРАНИЛИЩЕ АГЕНТОВ
# ============================================

# Словарь для хранения всех созданных агентов
# Ключ - имя агента, значение - объект Agent
agents_db: Dict[str, Agent] = {}

# Создаем несколько агентов по умолчанию
agents_db["копатич"] = Agent(
    name="Копатыч",
    prompt="""Ты Копатыч из Смешариков. Ты добрый медведь, любишь огород и мёд.
              Говори просто, по-деревенски. Часто используй "эх", "ну", "ой".
              Ты хозяйственный и осторожный, не любишь авантюры."""
)

agents_db["кар_карыч"] = Agent(
    name="Кар Карыч",
    prompt="""Ты Кар Карыч из Смешариков. Ты артист, поэт, путешественник.
              Говори красиво, с пафосом. Любишь рассказывать истории.
              Часто используй театральные выражения."""
)

agents_db["совунья"] = Agent(
    name="Совунья",
    prompt="""Ты Совунья из Смешариков. Ты заботливая, любишь спорт и здоровый образ жизни.
              Даешь советы по здоровью. Ворчишь, но по-доброму.
              Часто используй "Ох уж эта молодежь", "Надо закаляться"."""
)

# ============================================
# ЭНДПОИНТЫ API
# ============================================

@app.get("/", tags=["Root"])
async def root():
    """Корневой эндпоинт"""
    return {
        "message": "AI Agents API",
        "endpoints": [
            "/agents - список всех агентов",
            "/agents/{name} - информация об агенте",
            "/agents/create - создать нового агента",
            "/chat - отправить сообщение"
        ]
    }

@app.get("/agents", response_model=Dict[str, AgentResponse], tags=["Agents"])
async def list_agents():
    """Возвращает список всех доступных агентов"""
    return {
        name: {
            "name": agent.name,
            "prompt": agent.prompt[:100] + "..." if len(agent.prompt) > 100 else agent.prompt,
            "message": f"Агент {agent.name} готов к работе"
        }
        for name, agent in agents_db.items()
    }

@app.get("/agents/{name}", tags=["Agents"])
async def get_agent(name: str):
    """Возвращает информацию о конкретном агенте"""
    agent = agents_db.get(name.lower())
    if not agent:
        raise HTTPException(status_code=404, detail=f"Агент {name} не найден")
    
    return {
        "name": agent.name,
        "prompt": agent.prompt,
        "available": True
    }

@app.post("/agents/create", response_model=AgentResponse, tags=["Agents"])
async def create_agent(request: CreateAgentRequest):
    """Создает нового агента"""
    name = request.name.lower()
    
    if name in agents_db:
        raise HTTPException(status_code=400, detail=f"Агент с именем {request.name} уже существует")
    
    new_agent = Agent(name=request.name, prompt=request.prompt)
    agents_db[name] = new_agent
    
    return {
        "name": new_agent.name,
        "prompt": new_agent.prompt,
        "message": f"Агент {new_agent.name} успешно создан"
    }

@app.post("/chat", response_model=MessageResponse, tags=["Chat"])
async def chat(request: MessageRequest):
    """
    Отправляет сообщение AI-агенту и возвращает ответ
    
    Пример запроса:
    {
        "agent_name": "копатич",
        "session_id": "user_123",
        "message": "Привет! Как дела?"
    }
    """
    # Ищем агента
    agent = agents_db.get(request.agent_name.lower())
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Агент '{request.agent_name}' не найден. Доступные агенты: {list(agents_db.keys())}"
        )
    
    try:
        # Отправляем сообщение
        response = agent_client.send_message(
            agent=agent,
            session_id=request.session_id,
            text=request.message
        )
        
        return MessageResponse(
            response=response,
            agent_name=agent.name,
            session_id=request.session_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обработке запроса: {str(e)}")

@app.delete("/agents/{name}", tags=["Agents"])
async def delete_agent(name: str):
    """Удаляет агента"""
    name = name.lower()
    if name not in agents_db:
        raise HTTPException(status_code=404, detail=f"Агент {name} не найден")
    
    del agents_db[name]
    return {"message": f"Агент {name} удален"}

# ============================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

Запуск приложения
bash

uvicorn main:app --reload

Приложение будет доступно по адресу: http://localhost:8000

Документация Swagger: http://localhost:8000/docs
Использование API
1. Посмотреть всех агентов
bash

curl -X GET "http://localhost:8000/agents"

Ответ:
json

{
  "копатич": {
    "name": "Копатыч",
    "prompt": "Ты Копатыч из Смешариков. Ты добрый медведь, любишь огород и мёд...",
    "message": "Агент Копатыч готов к работе"
  }
}

2. Отправить сообщение агенту
bash

curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "копатич",
    "session_id": "user_123",
    "message": "Привет! Чем занимаешься?"
  }'

Ответ:
json

{
  "response": "Ох, привет! Да вот, на огороде копаюсь. Картошку сажаю. Эх, хорошая нынче земля! А ты чего?",
  "agent_name": "Копатыч",
  "session_id": "user_123"
}

3. Создать нового агента
bash

curl -X POST "http://localhost:8000/agents/create" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Пин",
    "prompt": "Ты Пин из Смешариков. Ты изобретатель-механик. Говори с акцентом. Любишь изобретать и чинить."
  }'

4. Продолжить диалог (тот же session_id)
bash

curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "копатич",
    "session_id": "user_123",
    "message": "А мед у тебя есть?"
  }'

Агент помнит предыдущий разговор.
Интеграция с фронтендом
Пример на JavaScript
javascript

async function sendMessage(agentName, sessionId, message) {
  const response = await fetch('http://localhost:8000/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      agent_name: agentName,
      session_id: sessionId,
      message: message
    })
  });
  
  const data = await response.json();
  return data.response;
}

// Использование
sendMessage('копатич', 'user_123', 'Привет!')
  .then(response => console.log('Ответ:', response));

Пример на Python (для другого бэкенда)
python

import requests

def chat_with_agent(agent_name, session_id, message):
    url = "http://localhost:8000/chat"
    data = {
        "agent_name": agent_name,
        "session_id": session_id,
        "message": message
    }
    
    response = requests.post(url, json=data)
    return response.json()["response"]

# Использование
ответ = chat_with_agent("копатич", "user_123", "Как дела?")
print(ответ)

Важные моменты
1. session_id

    Один пользователь = один session_id

    Храни session_id на фронтенде (localStorage) или в базе данных

    Если хочешь начать диалог заново - используй новый session_id

2. Агенты

    Имена агентов регистронезависимые (все приводятся к нижнему регистру)

    При создании агента имя должно быть уникальным

    Промпт определяет характер - чем подробнее, тем лучше

3. Обработка ошибок

Всегда проверяй ответ от API:
python

response = requests.post("http://localhost:8000/chat", json=data)
if response.status_code == 200:
    return response.json()["response"]
else:
    print(f"Ошибка: {response.json()['detail']}")

4. Производительность

    Агенты кэшируются на бэкенде

    Сессии диалогов тоже кэшируются

    Для продакшена добавь Redis для хранения сессий

Расширение функциональности
Добавление авторизации
python

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # Проверь токен (JWT, API key и т.д.)
    if token != "secret_token":
        raise HTTPException(status_code=401)
    return token

@app.post("/chat", response_model=MessageResponse)
async def chat(
    request: MessageRequest,
    token: str = Depends(verify_token)
):
    # Тот же код
    ...

Сохранение истории в базу данных
python

from sqlalchemy import create_engine, Column, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Модель для истории сообщений
class MessageHistory(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True)
    session_id = Column(String)
    agent_name = Column(String)
    user_message = Column(Text)
    agent_response = Column(Text)
    created_at = Column(DateTime)

# Сохраняй перед отправкой ответа
def save_to_db(session_id, agent_name, user_message, agent_response):
    # код сохранения
    pass

Troubleshooting
Ошибка "Агент не найден"

Проверь список агентов через GET /agents и используй точное имя.
Ошибка аутентификации Yandex

Проверь .env файл:

    Нет лишних пробелов

    Правильные ли ключи

    Не истек ли API ключ

Долгий ответ

    Проверь интернет соединение

    Уменьши температуру (сделай агента менее креативным)

    Используй более быструю модель (yandexgpt-lite)

Примеры промптов
python

# Продажник
prompt = """Ты менеджер по продажам. Рассказывай о преимуществах продукта.
            Будь настойчив, но не навязчив. Задавай уточняющие вопросы."""

# Психолог
prompt = """Ты психолог. Выслушивай, задавай правильные вопросы.
            Не давай прямых советов, помогай клиенту самому найти решение.
            Будь эмпатичным."""

# Учитель английского
prompt = """Ты учитель английского. Общайся на английском, но если ученик не понимает,
            переходи на русский. Исправляй ошибки. Хвали за успехи."""

