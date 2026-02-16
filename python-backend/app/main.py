from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager

from app.data.default_agents_data import agents_data
from app.database.sqlite_setup import Base, SessionLocal, engine, get_db
from app.models.agent import Agent
from app.models.message import Message
from app.models.relationship import Relationship
from app.routers.auth import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("→ Запуск lifespan (startup)")
    try:
        with SessionLocal() as db:
            init_default_agents(db)
    except Exception as e:
        print(f"Ошибка в lifespan: {e}")
    yield
    print("→ Завершение lifespan (shutdown)")

app = FastAPI(
    title="AIgod API",
    description="""
API бэкенда AIgod для хакатона.

## Аутентификация
- **POST /auth/register** — регистрация (email + пароль)
- **POST /auth/login** — логин (form: username=email, password), возвращает access_token
- **GET /auth/me** — текущий пользователь (требует Bearer token)

Для тестирования защищённых эндпоинтов: нажмите **Authorize**, введите email и пароль, получите токен.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "auth", "description": "Регистрация, логин, получение текущего пользователя"},
        {"name": "system", "description": "Проверка работы сервера и БД"},
        {"name": "agents", "description": "Работа с агентами"},
    ],
    lifespan=lifespan,
)

# Роутеры
app.include_router(auth_router)

# Создаём таблицы
Base.metadata.create_all(bind=engine)

# Заполнение БД агентами
def init_default_agents(db: Session):
    count = db.query(Agent).count()
    if count > 0:
        print(f"Агенты уже существуют ({count} шт.), пропускаем создание")
        return

    print("→ Создаём 6 агентов...")

    

    try:
        for data in agents_data:
            agent = Agent(**data, state_vector={})
            db.add(agent)
        db.commit()
        print("→ Успешно добавлено 6 агентов")
    except Exception as e:
        db.rollback()
        print(f"Ошибка при добавлении агентов: {e}")


# -------------------------------
# Роуты
# -------------------------------

@app.get("/", tags=["system"], summary="Проверка работы")
def root():
    """Проверка, что бэкенд запущен."""
    return {"message": "AIgod backend работает"}


@app.get("/test-db", tags=["system"], summary="Проверка БД")
def test_db(db: Session = Depends(get_db)):
    """Проверка подключения к базе данных."""
    return {"status": "база подключена"}


@app.get("/agents", tags=["agents"], summary="Список агентов")
def get_all_agents(db: Session = Depends(get_db)):
    """Получить всех агентов из базы."""
    agents = db.query(Agent).all()
    if not agents:
        return {"message": "Агенты не найдены", "count": 0}

    return [
        {
            "id": agent.id,
            "name": agent.name,
            "personality": agent.personality[:80] + "..." if len(agent.personality) > 80 else agent.personality,
            "avatar_url": agent.avatar_url or "(нет аватара)",
            "state_vector": agent.state_vector
        }
        for agent in agents
    ]