import logging
import os
from typing import Dict, List, Tuple
from dotenv import load_dotenv
from yandex_ai_studio_sdk import AIStudio

load_dotenv()

logger = logging.getLogger("aigod.yandex")

YANDEX_CLOUD_FOLDER = os.getenv("YANDEX_CLOUD_FOLDER")
YANDEX_CLOUD_API_KEY = os.getenv("YANDEX_CLOUD_API_KEY")
TEMPERATURE = 0.5


class YandexAgentClient:

    def __init__(self, folder_id: str = None, api_key: str = None):
        self.folder_id = folder_id or YANDEX_CLOUD_FOLDER
        self.api_key = api_key or YANDEX_CLOUD_API_KEY
        iam_token = os.getenv("YANDEX_IAM_TOKEN", "").strip()

        # IAM токен приоритетнее (работает с yc iam create-token и сервисным аккаунтом)
        if iam_token:
            auth_value = iam_token if iam_token.startswith("Bearer ") else f"Bearer {iam_token}"
        elif self.api_key:
            auth_value = self.api_key.replace("Api-Key ", "").strip()
        else:
            raise ValueError("YANDEX_CLOUD_FOLDER и (YANDEX_CLOUD_API_KEY или YANDEX_IAM_TOKEN) должны быть заданы")

        if not self.folder_id:
            raise ValueError("YANDEX_CLOUD_FOLDER должен быть задан")

        self.sdk = AIStudio(
            folder_id=self.folder_id,
            auth=auth_value
        )

        self.sessions: Dict[str, List[Tuple[str, str]]] = {}
        self._memory_collection = None
        self._init_memory()

    def _init_memory(self):
        """Инициализация ChromaDB для памяти агента. Опционально — при ошибке память отключается."""
        try:
            import chromadb
            from chromadb.utils import embedding_functions

            self.chroma_client = chromadb.Client()
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            self._memory_collection = self.chroma_client.get_or_create_collection(
                name="agents_memory",
                embedding_function=self.embedding_function
            )
        except Exception as e:
            logger.warning("ChromaDB недоступен, память отключена: %s", e)
            self._memory_collection = None

    def _store_agent_memory(self, agent, session_id: str, user_text: str, answer: str):
        if self._memory_collection is None:
            return

        try:
            memory_text = f"""
        Пользователь сказал: {user_text}
        Агент ответил: {answer}
        """

            memory_id = f"{agent.name}_{session_id}_{len(self.sessions.get(session_id, []))}"

            self._memory_collection.add(
                documents=[memory_text],
                metadatas=[{
                    "agent": agent.name,
                    "session_id": session_id
                }],
                ids=[memory_id]
            )
        except Exception as e:
            print("Memory storage error:", e)

    def _get_agent_memory(self, agent, session_id: str, query: str, k: int = 5) -> str:
        if self._memory_collection is None:
            return ""

        try:
            results = self._memory_collection.query(
                query_texts=[query],
                n_results=k,
                where={"agent": agent.name}
            )

            memories = results.get("documents", [[]])[0]

            if not memories:
                return ""

            formatted = "\n".join(memories)
            return f"\nВоспоминания агента:\n{formatted}\n"

        except Exception as e:
            print("Memory retrieval error:", e)
            return ""  

    def _build_prompt(self, agent, session_id: str, user_text: str) -> str:
        history = self.sessions.get(session_id, [])

        conversation = ""
        for role, message in history:
            conversation += f"{role}: {message}\n"

        memories = self._get_agent_memory(agent, session_id, user_text)

        conversation += f"Пользователь: {user_text}\n"
        conversation += "Ответ:"

        return f"""
            {agent.prompt}
            {memories}
            Текущий диалог:
            {conversation}
        """

    def send_message(self, agent, session_id: str, text: str) -> str:
        try:
            from app.services.api_usage_limiter import check_can_call_api, record_api_call, ApiLimitExceededError

            check_can_call_api()

            logger.info("YandexGPT запрос agent=%s session=%s", getattr(agent, 'name', agent), session_id)
            model = self.sdk.models.completions("yandexgpt").configure(
                temperature=TEMPERATURE
            )

            prompt = self._build_prompt(agent, session_id, text)

            result = model.run(prompt)
            record_api_call()
            answer = result.text.strip()

            if session_id not in self.sessions:
                self.sessions[session_id] = []

            self.sessions[session_id].append(("Пользователь", text))
            self.sessions[session_id].append((agent.name, answer))
            self._store_agent_memory(agent, session_id, text, answer)

            if len(self.sessions[session_id]) > 20:
                self.sessions[session_id] = self.sessions[session_id][-20:]

            logger.info("YandexGPT ответ agent=%s len=%d", getattr(agent, 'name', agent), len(answer))
            return answer

        except Exception as e:
            from app.services.api_usage_limiter import ApiLimitExceededError

            if isinstance(e, ApiLimitExceededError):
                logger.warning("YandexGPT лимит исчерпан: %s (сегодня %d из %d)", e.window, e.current, e.limit)
                return "Лимит обращений к AI исчерпан на сегодня. Попробуйте завтра или обратитесь к администратору."
            logger.exception("YandexGPT error: %s", e)
            return "Ой-ой, связь пропала! Попробуй позже."

class Agent:
    def __init__(self, name: str, prompt: str):
        self.name = name
        self.prompt = prompt
