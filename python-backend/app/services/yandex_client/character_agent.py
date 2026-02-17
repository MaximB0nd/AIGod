from app.services.yandex_client.yandex_agent_client import YandexAgentClient


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

