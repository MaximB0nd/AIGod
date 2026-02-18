from typing import List, Optional, Dict
from datetime import datetime

from ..base_strategy import BaseStrategy
from ..context import ConversationContext
from ..message import Message
from ..message_type import MessageType

class FullContextStrategy(BaseStrategy):
    """
    Стратегия полного контекста:
    - Начинается с общего промпта для всех агентов
    - Каждый агент получает суммарный промпт из ответов других агентов
    - Контекст постоянно обновляется и суммируется
    """
    
    def __init__(self, context: ConversationContext,
                 initial_prompt: str,
                 summary_agent: Optional[str] = None,
                 max_rounds: int = 5,
                 agents_per_round: int = 2,
                 include_system_messages: bool = True):
        super().__init__(context)
        self.initial_prompt = initial_prompt
        self.summary_agent = summary_agent
        self.max_rounds = max_rounds
        self.agents_per_round = agents_per_round
        self.include_system_messages = include_system_messages
        
        self.current_round = 0
        self.round_responses: Dict[int, List[Message]] = {}
        
        self.context.update_memory("full_context_prompt", initial_prompt)
        self.context.current_topic = initial_prompt[:100] + "..."
    
    async def on_start(self):
        if self.include_system_messages:
            system_msg = Message(
                content=f"Starting full context discussion with prompt: {self.initial_prompt}",
                type=MessageType.SYSTEM,
                sender="system",
                timestamp=datetime.now(),
                metadata={"round": 0, "action": "init"}
            )
            self.context.add_message(system_msg)
        
        self.context.update_memory("initial_prompt", self.initial_prompt)
        self.context.update_memory("full_context_rounds", [])
    
    async def tick(self, agents: List[str]) -> Optional[List[Message]]:
        if not agents or self.current_round >= self.max_rounds:
            return None
        
        messages = []
        round_agents = self._select_round_agents(agents)
        round_context = await self._build_round_context()
        
        for agent in round_agents:
            response = await self._query_agent(agent, round_context)
            messages.append(response)
            
            if self.current_round not in self.round_responses:
                self.round_responses[self.current_round] = []
            self.round_responses[self.current_round].append(response)
        
        if self.summary_agent and len(messages) > 1:
            summary = await self._summarize_round()
            if summary:
                messages.append(summary)
        
        if self.include_system_messages:
            round_end_msg = Message(
                content=f"=== Round {self.current_round + 1} completed ===",
                type=MessageType.SYSTEM,
                sender="system",
                timestamp=datetime.now(),
                metadata={"round_completed": self.current_round + 1}
            )
            messages.append(round_end_msg)
        
        self.current_round += 1
        return messages
    
    def _select_round_agents(self, agents: List[str]) -> List[str]:
        start_idx = (self.current_round * self.agents_per_round) % len(agents)
        selected = []
        
        for i in range(self.agents_per_round):
            idx = (start_idx + i) % len(agents)
            if agents[idx] not in selected:
                selected.append(agents[idx])
        
        return selected
    
    async def _build_round_context(self) -> str:
        context_parts = [f"Initial prompt: {self.initial_prompt}"]
        
        if self.current_round > 0:
            context_parts.append(f"\nPrevious round discussion:")
            for msg in self.round_responses.get(self.current_round - 1, []):
                context_parts.append(f"{msg.sender}: {msg.content}")
        
        key_points = self.context.get_memory("key_points", [])
        if key_points:
            context_parts.append("\nKey points so far:")
            for i, point in enumerate(key_points[-5:], 1):
                context_parts.append(f"{i}. {point}")
        
        context_parts.append(f"\nCurrent round: {self.current_round + 1}/{self.max_rounds}")
        
        return "\n".join(context_parts)
    
    async def _query_agent(self, agent: str, context: str) -> Message:
        prompt = f"""
        You are participating in a group discussion.
        
        Context:
        {context}
        
        Based on the current context and your expertise, provide your perspective.
        Be concise but thorough. Focus on adding value to the discussion.
        """
        
        response = await self.chat_service(
            agent,
            "full_context_session",
            prompt,
            context=self.context
        )
        
        return Message(
            content=response,
            type=MessageType.AGENT,
            sender=agent,
            timestamp=datetime.now(),
            metadata={
                "round": self.current_round,
                "agent_type": "participant"
            }
        )
    
    async def _summarize_round(self) -> Optional[Message]:
        if not self.summary_agent:
            return None
        
        round_msgs = self.round_responses.get(self.current_round, [])
        if not round_msgs:
            return None
        
        discussion_text = "\n".join([
            f"{msg.sender}: {msg.content}" for msg in round_msgs
        ])
        
        prompt = f"""
        Summarize the key points from this round of discussion:
        
        {discussion_text}
        
        Provide:
        1. Main ideas presented
        2. Agreements or consensus
        3. Points of contention
        4. Questions raised
        5. Suggestions for next round
        
        Keep the summary concise but comprehensive.
        """
        
        response = await self.chat_service(
            self.summary_agent,
            "full_context_session",
            prompt,
            context=self.context
        )
        
        self._extract_key_points(response)
        
        return Message(
            content=response,
            type=MessageType.SUMMARIZED,
            sender=self.summary_agent,
            timestamp=datetime.now(),
            metadata={
                "round": self.current_round,
                "type": "round_summary"
            }
        )
    
    def _extract_key_points(self, summary: str):
        key_points = self.context.get_memory("key_points", [])
        key_points.append(f"Round {self.current_round}: {summary[:200]}...")
        self.context.update_memory("key_points", key_points)
    
    async def handle_user_message(self, message: str) -> List[Message]:
        user_msg = Message(
            content=message,
            type=MessageType.USER,
            sender="user",
            timestamp=datetime.now(),
            metadata={"influence_context": True}
        )
        
        self.context.current_user_message = message
        self.context.update_memory("_user_message", message)
        self.context.update_memory("user_input", message)
        self.context.update_memory("user_input_round", self.current_round)

        return [user_msg]
    
    def should_stop(self) -> bool:
        return self.current_round >= self.max_rounds
    
    def get_round_summaries(self) -> Dict[int, str]:
        summaries = {}
        for round_num, messages in self.round_responses.items():
            summaries[round_num] = "\n".join([f"{m.sender}: {m.content}" for m in messages])
        return summaries
