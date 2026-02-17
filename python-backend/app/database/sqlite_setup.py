import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.pool import StaticPool

# Путь к БД: через env для Docker (абсолютный /app/data/aigod.db), для тестов :memory:
_db_path = os.getenv("SQLITE_DB_PATH", "aigod.db")
if _db_path == ":memory:":
    SQLITE_URL = "sqlite:///:memory:"
elif _db_path.startswith("/"):
    SQLITE_URL = f"sqlite:////{_db_path}"
else:
    SQLITE_URL = f"sqlite:///./{_db_path}"

_is_memory = ":memory:" in SQLITE_URL
engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},  # для FastAPI + тестов (многопоточность)
    poolclass=StaticPool if _is_memory else None,  # один connection для :memory:
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()   # все модели наследуются от этого Base

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()