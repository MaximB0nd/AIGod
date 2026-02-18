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
                 max_iterations: int = 5,
                 agents_per_iteration: int = 2,
                 include_system_messages: bool = True):
        super().__init__(context)
        self.initial_prompt = initial_prompt
        self.summary_agent = summary_agent
        self.max_iterations = max_iterations
        self.agents_per_iteration = agents_per_iteration
        self.include_system_messages = include_system_messages
        
        self.current_iteration = 0
        self.iter_responses: Dict[int, List[Message]] = {}
        
        self.context.update_memory("full_context_prompt", initial_prompt)
        self.context.current_topic = initial_prompt[:100] + "..."
    
    async def on_start(self):
        if self.include_system_messages:
            system_msg = Message(
                content=f"Starting full context discussion with prompt: {self.initial_prompt}",
                type=MessageType.SYSTEM,
                sender="system",
                timestamp=datetime.now(),
                metadata={"iteration": 0, "action": "init"}
            )
            self.context.add_message(system_msg)
        
        self.context.update_memory("initial_prompt", self.initial_prompt)
        self.context.update_memory("full_context_iterations", [])
    
    async def tick(self, agents: List[str]) -> Optional[List[Message]]:
        discussion_agents = [a for a in agents if a != self.summary_agent] if self.summary_agent else agents
        if not discussion_agents or self.current_iteration >= self.max_iterations:
            return None
        
        messages = []
        iter_agents = self._select_iteration_agents(discussion_agents)
        iter_context = await self._build_iteration_context()
        
        for agent in iter_agents:
            response = await self._query_agent(agent, iter_context)
            messages.append(response)
            
            if self.current_iteration not in self.iter_responses:
                self.iter_responses[self.current_iteration] = []
            self.iter_responses[self.current_iteration].append(response)
        
        if self.summary_agent and len(messages) > 1:
            summary = await self._summarize_iteration()
            if summary:
                messages.append(summary)
        
        if self.include_system_messages:
            iter_end_msg = Message(
                content="=== Обсуждение продолжается ===",
                type=MessageType.SYSTEM,
                sender="system",
                timestamp=datetime.now(),
                metadata={"iteration_completed": self.current_iteration + 1}
            )
            messages.append(iter_end_msg)
        
        self.current_iteration += 1
        return messages
    
    def _select_iteration_agents(self, agents: List[str]) -> List[str]:
        start_idx = (self.current_iteration * self.agents_per_iteration) % len(agents)
        selected = []
        
        for i in range(self.agents_per_iteration):
            idx = (start_idx + i) % len(agents)
            if agents[idx] not in selected:
                selected.append(agents[idx])
        
        return selected
    
    async def _build_iteration_context(self) -> str:
        context_parts = [f"Initial prompt: {self.initial_prompt}"]
        
        if self.current_iteration > 0:
            context_parts.append(f"\nPrevious discussion:")
            for msg in self.iter_responses.get(self.current_iteration - 1, []):
                context_parts.append(f"{msg.sender}: {msg.content}")
        
        key_points = self.context.get_memory("key_points", [])
        if key_points:
            context_parts.append("\nKey points so far:")
            for i, point in enumerate(key_points[-5:], 1):
                context_parts.append(f"{i}. {point}")
        
        context_parts.append(f"\nCurrent step: {self.current_iteration + 1}/{self.max_iterations}")
        
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
                "iteration": self.current_iteration,
                "agent_type": "participant"
            }
        )
    
    async def _summarize_iteration(self) -> Optional[Message]:
        if not self.summary_agent:
            return None
        
        iter_msgs = self.iter_responses.get(self.current_iteration, [])
        if not iter_msgs:
            return None
        
        discussion_text = "\n".join([
            f"{msg.sender}: {msg.content}" for msg in iter_msgs
        ])
        
        prompt = f"""
        Summarize the key points from this discussion step:
        
        {discussion_text}
        
        Provide:
        1. Main ideas presented
        2. Agreements or consensus
        3. Points of contention
        4. Questions raised
        5. Suggestions for next step
        
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
                "iteration": self.current_iteration,
                "type": "iteration_summary"
            }
        )
    
    def _extract_key_points(self, summary: str):
        key_points = self.context.get_memory("key_points", [])
        key_points.append(f"Step {self.current_iteration}: {summary[:200]}...")
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
        self.context.update_memory("user_input_iteration", self.current_iteration)

        return [user_msg]
    
    def should_stop(self) -> bool:
        return self.current_iteration >= self.max_iterations
    
    def get_iteration_summaries(self) -> Dict[int, str]:
        summaries = {}
        for iter_num, messages in self.iter_responses.items():
            summaries[iter_num] = "\n".join([f"{m.sender}: {m.content}" for m in messages])
        return summaries
