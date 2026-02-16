import os
from typing import Dict, List, Tuple
from dotenv import load_dotenv
from yandex_ai_studio_sdk import AIStudio

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

    def _build_prompt(self, agent, session_id: str, user_text: str) -> str:
        history = self.sessions.get(session_id, [])

        conversation = ""
        for role, message in history:
            conversation += f"{role}: {message}\n"

        conversation += f"Пользователь: {user_text}\n"
        conversation += "Ответ:"

        return f"{agent.prompt}\n\n{conversation}"

    def send_message(self, agent, session_id: str, text: str) -> str:
        try:
            model = self.sdk.models.completions("yandexgpt").configure(
                temperature=TEMPERATURE
            )

            prompt = self._build_prompt(agent, session_id, text)

            result = model.run(prompt)
            answer = result.text.strip()

            # 🔹 Сохраняем историю
            if session_id not in self.sessions:
                self.sessions[session_id] = []

            self.sessions[session_id].append(("Пользователь", text))
            self.sessions[session_id].append((agent.name, answer))

            # 🔹 Ограничиваем историю (последние 20 сообщений)
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
