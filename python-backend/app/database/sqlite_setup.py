import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Путь к БД: через env для Docker (абсолютный /app/data/aigod.db), по умолчанию aigod.db
_db_path = os.getenv("SQLITE_DB_PATH", "aigod.db")
SQLITE_URL = f"sqlite:////{_db_path}" if _db_path.startswith("/") else f"sqlite:///./{_db_path}"

engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False}  # ← обязательно для FastAPI + uvicorn
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()   # все модели наследуются от этого Base

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()