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


@router.get("/test-chromadb", summary="Проверка ChromaDB")
def test_chromadb():
    """
    Проверка работы ChromaDB для памяти.
    ChromaDB используется в context_memory для векторного поиска (долгосрочная память).
    При сбое память работает в short-term режиме (без ChromaDB).
    """
    import sys
    result = {"chromadb_available": False, "vector_store_init": False, "error": None}
    try:
        from app.services.context_memory.vector_store import CHROMA_AVAILABLE
        result["chromadb_available"] = CHROMA_AVAILABLE
        if not CHROMA_AVAILABLE:
            result["error"] = "ChromaDB не установлен (pip install chromadb)"
            return result
    except Exception as e:
        result["error"] = f"Import: {type(e).__name__}: {str(e)[:200]}"
        return result

    try:
        import chromadb
        result["chromadb_version"] = chromadb.__version__
    except Exception:
        pass

    try:
        import numpy
        result["numpy_version"] = numpy.__version__
    except Exception:
        pass

    try:
        from app.services.context_memory.vector_store import VectorMemoryStore
        from app.config import config
        persist_dir = config.CHROMA_PERSIST_DIR
        vs = VectorMemoryStore(
            collection_name="health_check",
            persist_directory=persist_dir,
        )
        result["vector_store_init"] = True
        result["persist_dir"] = persist_dir
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {str(e)[:300]}"
        if "np.float_" in str(e):
            result["hint"] = "NumPy 2.0 несовместим с chromadb<0.5.3. Варианты: pip install numpy==1.26.4 или pip install chromadb>=0.5.3"

    return result
