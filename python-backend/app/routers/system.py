from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.sqlite_setup import get_db

router = APIRouter(tags=["system"])

# Системные endpoints для проверки работы системы

@router.get("/", summary="Проверка работы")
def root():
    """Проверка, что бэкенд запущен."""
    return {"message": "AIgod backend работает"}


@router.get("/test-db", summary="Проверка БД")
def test_db(db: Session = Depends(get_db)):
    """Проверка подключения к базе данных."""
    return {"status": "база подключена"}
