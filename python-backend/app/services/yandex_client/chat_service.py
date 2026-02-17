from app.services.yandex_client.yandex_agent_client import YandexAgentClient
from app.services.yandex_client.agent_factory import AgentFactory

class ChatService:

    def __init__(self):
        self.agent_client = YandexAgentClient()
        self.agent_factory = AgentFactory(self.agent_client)

    def process_message(self, agent, session_id: str, message: str) -> str:
        character_agent = self.agent_factory.get_agent(agent)
        return character_agent.respond(session_id, message)

