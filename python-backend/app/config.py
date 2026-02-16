import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # OpenAI
    YANDEX_GPT_API_KEY = os.getenv("YANDEX_GPT_API_KEY", "") 
    YANDEX_GPT_MODEL = os.getenv("YANDEX_GPT_MODEL", "gpt-3.5-turbo") # change to YandexGPT
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
    
    # Database
    SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "agents.db")
    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    
    # Agent settings
    MAX_MEMORIES_PER_AGENT = int(os.getenv("MAX_MEMORIES_PER_AGENT", "50"))
    MEMORY_SUMMARY_THRESHOLD = int(os.getenv("MEMORY_SUMMARY_THRESHOLD", "20"))
    
config = Config()
