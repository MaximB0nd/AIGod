from yandex_agent_client import YandexAgentClient 
from character_agent import CharacterAgent

class AgentFactory:

    def __init__(self, agent_client: YandexAgentClient):
        self.agent_client = agent_client
        self.agents: Dict[str, CharacterAgent] = {}

    def get_agent(self, agent) -> CharacterAgent:
        if agent.name not in self.agents:
            self.agents[agent.name] = CharacterAgent(agent, self.agent_client)
        return self.agents[agent.name]

