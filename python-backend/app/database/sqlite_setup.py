from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

SQLITE_URL = "sqlite:///./aigod.db"          # ← файл будет создан рядом с main.py

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