from typing import List, Optional
from datetime import datetime
from collections import Counter
import random

from ..base_strategy import BaseStrategy
from ..context import ConversationContext
from ..message import Message
from ..message_type import MessageType

class NarratorStrategy(BaseStrategy):
    """
    Стратегия с агентом-рассказчиком:
    - Один агент (нарратор) управляет повествованием
    - Он вызывает других агентов по мере необходимости
    - Нарратор поддерживает связность истории
    """
    
    def __init__(self, context: ConversationContext, 
                 narrator_agent: str,
                 story_topic: str,
                 narrator_interval: int = 3,
                 max_agent_responses: int = 2,
                 randomize_agents: bool = True):
        super().__init__(context)
        self.narrator_agent = narrator_agent
        self.story_topic = story_topic
        self.narrator_interval = narrator_interval
        self.max_agent_responses = max_agent_responses
        self.randomize_agents = randomize_agents
        
        self.ticks_since_last_narration = 0
        self.agent_responses_since_narration = 0
        self.story_progression = []
        self.current_scene = 1
        
        self.context.current_topic = story_topic
    
    async def on_start(self):
        intro_prompt = f"""
        Start a new story about: {self.story_topic}
        
        Set the scene, introduce the setting and initial situation.
        Make it engaging and open-ended so other characters can join.
        """
        
        response = await self.chat_service(
            self.narrator_agent,
            "narrator_session",
            intro_prompt,
            context=self.context
        )
        
        intro_message = Message(
            content=response,
            type=MessageType.NARRATOR,
            sender=self.narrator_agent,
            timestamp=datetime.now(),
            metadata={"action": "story_start", "scene": self.current_scene}
        )
        
        self.context.add_message(intro_message)
        self.story_progression.append(response)
    
    async def tick(self, agents: List[str]) -> Optional[List[Message]]:
        if not agents:
            return None
        
        messages = []
        
        need_narration = (
            self.ticks_since_last_narration >= self.narrator_interval or
            self.agent_responses_since_narration >= self.max_agent_responses
        )
        
        if need_narration:
            narration_msg = await self._narrator_tick()
            messages.append(narration_msg)
            self.ticks_since_last_narration = 0
            self.agent_responses_since_narration = 0
        else:
            agent_msg = await self._agent_tick(agents)
            if agent_msg:
                messages.append(agent_msg)
                self.agent_responses_since_narration += 1
        
        self.ticks_since_last_narration += 1
        return messages if messages else None
    
    async def _narrator_tick(self) -> Message:
        recent_history = self.context.get_recent_messages(5)
        history_text = "\n".join([f"{m.sender}: {m.content}" for m in recent_history])
        
        prompt = f"""
        You are the narrator of a story about: {self.story_topic}
        Current scene: {self.current_scene}
        
        Recent events:
        {history_text}
        
        Advance the story. Consider:
        1. What happens next?
        2. Introduce new elements or conflicts
        3. Set up opportunities for other characters to respond
        4. Maintain narrative coherence
        
        Provide the next narrative segment.
        """
        
        response = await self.chat_service(
            self.narrator_agent,
            "narrator_session",
            prompt,
            context=self.context
        )
        
        self.current_scene += 1
        self.story_progression.append(response)
        
        return Message(
            content=response,
            type=MessageType.NARRATOR,
            sender=self.narrator_agent,
            timestamp=datetime.now(),
            metadata={"action": "narrative_advance", "scene": self.current_scene}
        )
    
    async def _agent_tick(self, agents: List[str]) -> Optional[Message]:
        character_agents = [a for a in agents if a != self.narrator_agent]
        if not character_agents:
            return None
        
        agent = self._select_next_agent(character_agents)
        
        last_message = self.context.get_last_message()
        if not last_message:
            return None
        
        prompt = f"""
        You are {agent}, a character in a story about: {self.story_topic}
        
        Current situation (from the narrator):
        {last_message.content if last_message.type == MessageType.NARRATOR else "The story continues..."}
        
        As your character, respond to the current situation. Consider:
        1. Your character's personality and motivations
        2. How you react to recent events
        3. What you want to achieve
        4. Interact with other characters
        
        Provide your character's response.
        """
        
        response = await self.chat_service(
            agent,
            "narrator_session",
            prompt,
            context=self.context
        )
        
        return Message(
            content=response,
            type=MessageType.AGENT,
            sender=agent,
            timestamp=datetime.now(),
            metadata={"character_response": True, "scene": self.current_scene}
        )
    
    def _select_next_agent(self, agents: List[str]) -> str:
        if self.randomize_agents:
            return random.choice(agents)
        
        sender_counts = Counter([m.sender for m in self.context.history])
        return min(agents, key=lambda a: sender_counts.get(a, 0))
    
    async def handle_user_message(self, message: str) -> List[Message]:
        prompt = f"""
        A reader suggests: {message}
        
        As the narrator, incorporate this suggestion into the story 
        in a natural and interesting way.
        """
        
        response = await self.chat_service(
            self.narrator_agent,
            "narrator_session",
            prompt,
            context=self.context
        )
        
        return [
            Message(
                content=message,
                type=MessageType.USER,
                sender="user",
                timestamp=datetime.now(),
                metadata={"influence_story": True}
            ),
            Message(
                content=response,
                type=MessageType.NARRATOR,
                sender=self.narrator_agent,
                timestamp=datetime.now(),
                metadata={"action": "user_influence", "scene": self.current_scene}
            )
        ]
    
    def get_story_so_far(self) -> str:
        return "\n\n".join(self.story_progression)
