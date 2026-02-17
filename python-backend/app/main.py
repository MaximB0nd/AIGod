from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.data.default_agents_data import agents_data
from app.database.sqlite_setup import Base, SessionLocal, engine, get_db
from app.models.agent import Agent
from app.routers.agents import router as agents_router
from app.routers.auth import router as auth_router
from app.routers.room_agents import router as room_agents_router
from app.routers.rooms import router as rooms_router
from app.routers.system import router as system_router
from app.routers.websocket import router as websocket_router


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
API бэкенда для хакатона «Виртуальный мир: симулятор живых существ».

Все эндпоинты под префиксом `/api`. Авторизация: Bearer token (кроме register/login).
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "auth", "description": "Регистрация, логин, текущий пользователь"},
        {"name": "system", "description": "Проверка работы"},
        {"name": "rooms", "description": "Комнаты"},
        {"name": "room-agents", "description": "Агенты, события, лента в комнате"},
        {"name": "agents", "description": "Каталог агентов (для добавления в комнату)"},
        {"name": "websocket", "description": "Поток событий в реальном времени"},
    ],
    lifespan=lifespan,
)

# API под префиксом /api
app.include_router(system_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(rooms_router, prefix="/api")
app.include_router(room_agents_router, prefix="/api/rooms")
app.include_router(agents_router, prefix="/api")
app.include_router(websocket_router, prefix="/api")

# Создаём таблицы
Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"message": "AIgod backend", "docs": "/docs", "api": "/api"}


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
