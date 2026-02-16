import os
from typing import Dict, List, Tuple
from dotenv import load_dotenv
from yandex_ai_studio_sdk import AIStudio
import chromadb
from chromadb.utils import embedding_functions

load_dotenv()

YANDEX_CLOUD_FOLDER = os.getenv("YANDEX_CLOUD_FOLDER")
YANDEX_CLOUD_API_KEY = os.getenv("YANDEX_CLOUD_API_KEY")
TEMPERATURE = 0.5

class YandexAgentClient:

    def __init__(self, folder_id: str = None, api_key: str = None):
        self.folder_id = folder_id or YANDEX_CLOUD_FOLDER
        self.api_key = api_key or YANDEX_CLOUD_API_KEY

        if not self.folder_id or not self.api_key:
            raise ValueError("YANDEX_CLOUD_FOLDER и YANDEX_CLOUD_API_KEY должны быть заданы")

        clean_api_key = self.api_key.replace("Api-Key ", "").strip()

        self.sdk = AIStudio(
            folder_id=self.folder_id,
            auth=clean_api_key
        )

        self.sessions: Dict[str, List[Tuple[str, str]]] = {}
        self._init_memory()

    def _init_memory(self):
        self.chroma_client = chromadb.Client()

        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        self.memory_collection = self.chroma_client.get_or_create_collection(
            name="agents_memory",
            embedding_function=self.embedding_function
        )

    def _store_agent_memory(self, agent, session_id: str, user_text: str, answer: str):

        memory_text = f"""
        Пользователь сказал: {user_text}
        Агент ответил: {answer}
        """

        memory_id = f"{agent.name}_{session_id}_{len(self.sessions.get(session_id, []))}"

        self.memory_collection.add(
            documents=[memory_text],
            metadatas=[{
                "agent": agent.name,
                "session_id": session_id
            }],
            ids=[memory_id]
        )  

    def _get_agent_memory(self, agent, session_id: str, query: str, k: int = 5) -> str:
        try:
            results = self.memory_collection.query(
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
            model = self.sdk.models.completions("yandexgpt").configure(
                temperature=TEMPERATURE
            )

            prompt = self._build_prompt(agent, session_id, text)

            result = model.run(prompt)
            answer = result.text.strip()

            if session_id not in self.sessions:
                self.sessions[session_id] = []

            self.sessions[session_id].append(("Пользователь", text))
            self.sessions[session_id].append((agent.name, answer))
            self._store_agent_memory(agent, session_id, text, answer)

            if len(self.sessions[session_id]) > 20:
                self.sessions[session_id] = self.sessions[session_id][-20:]

            return answer

        except Exception as e:
            print(f"Yandex AIAssistant error: {e}")
            return "Ой-ой, связь пропала! Попробуй позже."


class CharacterAgent:

    def __init__(self, agent, agent_client: YandexAgentClient):
        self.agent = agent
        self.agent_client = agent_client

    def respond(self, session_id: str, user_input: str) -> str:
        return self.agent_client.send_message(
            agent=self.agent,
            session_id=session_id,
            text=user_input,
        )


class AgentFactory:

    def __init__(self, agent_client: YandexAgentClient):
        self.agent_client = agent_client
        self.agents: Dict[str, CharacterAgent] = {}

    def get_agent(self, agent) -> CharacterAgent:
        if agent.name not in self.agents:
            self.agents[agent.name] = CharacterAgent(agent, self.agent_client)
        return self.agents[agent.name]


class ChatService:

    def __init__(self):
        self.agent_client = YandexAgentClient()
        self.agent_factory = AgentFactory(self.agent_client)

    def process_message(self, agent, session_id: str, message: str) -> str:
        character_agent = self.agent_factory.get_agent(agent)
        return character_agent.respond(session_id, message)


class Agent:
    def __init__(self, name: str, prompt: str):
        self.name = name
        self.prompt = prompt