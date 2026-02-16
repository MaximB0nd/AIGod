# app/main.py
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.database.sqlite_setup import engine, Base, get_db   # файл конфигурации БД
from app.models import *

app = FastAPI(title="AIgod")

# Создаём таблицы при первом запуске (для прототипа нормально)
Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"message": "AIgod backend работает"}

@app.get("/test-db")
def test_db(db: Session = Depends(get_db)):
    return {"status": "база подключена"}