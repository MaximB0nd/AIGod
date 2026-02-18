import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Yandex GPT (LLM агенты)
    YANDEX_CLOUD_FOLDER = os.getenv("YANDEX_CLOUD_FOLDER", "")
    YANDEX_CLOUD_API_KEY = os.getenv("YANDEX_CLOUD_API_KEY", "")
    YANDEX_GPT_API_KEY = os.getenv("YANDEX_GPT_API_KEY", "")  # legacy
    YANDEX_GPT_MODEL = os.getenv("YANDEX_GPT_MODEL", "yandexgpt")
    
    # Database
    SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "agents.db")
    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    
    # API usage limit (0 = без ограничений, защита от перерасхода)
    API_MESSAGE_LIMIT_PER_DAY = int(os.getenv("API_MESSAGE_LIMIT_PER_DAY", "100"))

    # Agent settings
    MAX_MEMORIES_PER_AGENT = int(os.getenv("MAX_MEMORIES_PER_AGENT", "50"))
    MEMORY_SUMMARY_THRESHOLD = int(os.getenv("MEMORY_SUMMARY_THRESHOLD", "20"))

    # JWT Auth
    SECRET_KEY = os.getenv("SECRET_KEY", "aigod-hackathon-change-me-in-production-1234567890")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


config = Config()
