import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
from sqlalchemy.orm import Session

from app.data.default_agents_data import agents_data
from app.services.orchestration_background import registry
from app.database.sqlite_setup import Base, SessionLocal, engine, get_db
from sqlalchemy import inspect

from app.models.default_agent import DefaultAgent
from app.routers.agents import router as agents_router
from app.routers.default_agents import router as default_agents_router
from app.routers.auth import router as auth_router
from app.routers.prompts import router as prompts_router
from app.routers.room_agents import router as room_agents_router
from app.routers.rooms import router as rooms_router
from app.routers.system import router as system_router
from app.routers.websocket import router as websocket_router


def migrate_add_orchestration_type():
    """Добавить колонку orchestration_type в rooms, если её нет."""
    from sqlalchemy import text
    try:
        insp = inspect(engine)
        if "rooms" not in insp.get_table_names():
            return
        cols = [c["name"] for c in insp.get_columns("rooms")]
        if "orchestration_type" in cols:
            return
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE rooms ADD COLUMN orchestration_type VARCHAR DEFAULT 'single'"))
            conn.commit()
    except Exception as e:
        print(f"Migration orchestration_type: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("→ Запуск lifespan (startup)")
    try:
        migrate_add_orchestration_type()
    except Exception as e:
        print(f"Ошибка миграции: {e}")
    try:
        with SessionLocal() as db:
            init_default_agents(db)
    except Exception as e:
        print(f"Ошибка в lifespan: {e}")
    yield
    print("→ Завершение lifespan (shutdown)")
    try:
        await registry.stop_all()
    except Exception as e:
        print(f"Ошибка при остановке оркестраций: {e}")


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
        {"name": "default-agents", "description": "Шаблоны агентов для предзаполнения формы"},
        {"name": "prompts", "description": "Системные промпты и шаблоны для агентов"},
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
app.include_router(default_agents_router, prefix="/api")
app.include_router(prompts_router, prefix="/api")
app.include_router(websocket_router, prefix="/api")

# Создаём таблицы
Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"message": "AIgod backend", "docs": "/docs", "api": "/api"}


def init_default_agents(db: Session):
    """Заполнить таблицу default_agents шаблонами (если пуста). Таблица agents изначально пуста."""
    count = db.query(DefaultAgent).count()
    if count > 0:
        print(f"Шаблоны агентов уже существуют ({count} шт.), пропускаем")
        return

    print("→ Создаём шаблоны агентов в default_agents...")
    try:
        for data in agents_data:
            d = DefaultAgent(
                name=data["name"],
                personality=data["personality"],
                avatar_url=data.get("avatar_url"),
            )
            db.add(d)
        db.commit()
        print(f"→ Добавлено {len(agents_data)} шаблонов")
    except Exception as e:
        db.rollback()
        print(f"Ошибка при добавлении шаблонов: {e}")
