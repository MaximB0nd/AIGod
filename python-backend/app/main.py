from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.data.default_agents_data import agents_data
from app.database.sqlite_setup import Base, SessionLocal, engine, get_db
from app.models.agent import Agent
from app.routers.agents import router as agents_router
from app.routers.auth import router as auth_router
from app.routers.rooms import router as rooms_router
from app.routers.system import router as system_router


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

## Комнаты
- **GET /rooms** — список комнат пользователя
- **POST /rooms** — создать комнату
- **GET /rooms/{id}** — получить комнату
- **PATCH /rooms/{id}** — обновить комнату
- **DELETE /rooms/{id}** — удалить комнату

Для тестирования защищённых эндпоинтов: нажмите **Authorize**, введите email и пароль.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "auth", "description": "Регистрация, логин, текущий пользователь"},
        {"name": "system", "description": "Проверка работы сервера и БД"},
        {"name": "agents", "description": "Работа с агентами"},
        {"name": "rooms", "description": "Комнаты пользователя"},
    ],
    lifespan=lifespan,
)

# Роутеры
app.include_router(system_router)
app.include_router(auth_router)
app.include_router(agents_router)
app.include_router(rooms_router)

# Создаём таблицы
Base.metadata.create_all(bind=engine)


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
