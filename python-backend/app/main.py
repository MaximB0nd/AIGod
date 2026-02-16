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

app = FastAPI(title="AIgod", lifespan=lifespan)

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

# Проверка работы бека
@app.get("/")
def root():
    return {"message": "AIgod backend работает"}

# Проверка подключения к БД
@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    return {"status": "база подключена"}

# Получение всех агентов
@app.get("/agents")
def get_all_agents(db: Session = Depends(get_db)):
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