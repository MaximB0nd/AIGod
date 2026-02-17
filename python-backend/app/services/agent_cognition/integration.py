"""
Интеграция когнитивной системы с оркестрацией
"""
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from .models import (
    CognitiveState, Thought, ThoughtType, 
    Plan, Reflection, Decision, Goal
)
from .memory_stream import MemoryStream, ThoughtProcessor
from .planner import Planner
from .reflector import Reflector
from .goal_manager import GoalManager
from .decision_maker import DecisionMaker

class CognitiveIntegration:
    """
    Интеграция когнитивных процессов с OrchestrationClient
    """
    
    def __init__(self, agent_name: str, chat_service=None):
        self.agent_name = agent_name
        self.chat_service = chat_service
        
        # Компоненты
        self.memory_stream = MemoryStream(agent_name)
        self.thought_processor = ThoughtProcessor(self.memory_stream)
        self.planner = Planner(agent_name, chat_service)
        self.reflector = Reflector(agent_name, chat_service)
        self.goal_manager = GoalManager(agent_name)
        self.decision_maker = DecisionMaker(agent_name, chat_service)
        
        # Когнитивное состояние
        self.state = CognitiveState(agent_name=agent_name)
        
        # Задачи
        self._thinking_task = None
        self._reflection_task = None
        self._running = False
        
        # Статистика
        self.stats = {
            "thinking_cycles": 0,
            "actions_taken": 0,
            "reflections_done": 0
        }
    
    async def start(self):
        """Запустить когнитивные процессы"""
        self._running = True
        self._thinking_task = asyncio.create_task(self._thinking_loop())
        self._reflection_task = asyncio.create_task(self._reflection_loop())
    
    async def stop(self):
        """Остановить когнитивные процессы"""
        self._running = False
        if self._thinking_task:
            self._thinking_task.cancel()
        if self._reflection_task:
            self._reflection_task.cancel()
    
    async def _thinking_loop(self):
        """Основной цикл мышления"""
        while self._running:
            try:
                # Получаем следующую мысль
                thought = self.memory_stream.get_next_thought()
                
                if thought:
                    # Обрабатываем мысль
                    result = await self.thought_processor.process_thought(thought)
                    
                    if result:
                        self.stats["thinking_cycles"] += 1
                        
                        # Обновляем состояние
                        self.state.add_thought(thought)
                        
                        # Действуем на основе мысли
                        await self._act_on_thought(thought, result)
                
                # Небольшая пауза между мыслями
                await asyncio.sleep(0.5)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in thinking loop: {e}")
                await asyncio.sleep(1)
    
    async def _reflection_loop(self):
        """Цикл рефлексии"""
        while self._running:
            try:
                if self.reflector.should_reflect():
                    # Получаем последние действия
                    recent_actions = self.state.decisions[-10:] if self.state.decisions else []
                    
                    # Рефлексия над периодом
                    reflection = await self.reflector.reflect_on_period(
                        actions=[d.to_dict() for d in recent_actions],
                        plans=self.planner.plan_history[-5:],
                        decisions=self.state.decisions[-5:]
                    )
                    
                    if reflection:
                        self.stats["reflections_done"] += 1
                        
                        # Добавляем мысль о рефлексии
                        self.memory_stream.add_thought(
                            content=reflection.content,
                            thought_type=ThoughtType.REFLECTION,
                            importance=0.8
                        )
                        
                        # Обновляем планы на основе рефлексии
                        await self._update_plans_from_reflection(reflection)
                
                await asyncio.sleep(60)  # проверяем каждую минуту
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in reflection loop: {e}")
                await asyncio.sleep(60)
    
    async def on_message(self, 
                        message: str,
                        sender: str,
                        context: Optional[Dict] = None) -> Dict:
        """
        Обработка входящего сообщения
        """
        # Добавляем наблюдение
        thought = self.memory_stream.add_thought(
            content=f"Получено сообщение от {sender}: {message}",
            thought_type=ThoughtType.OBSERVATION,
            importance=0.6,
            context={"sender": sender, "message": message, **(context or {})}
        )
        
        # Обновляем внутренний диалог
        self.memory_stream.add_to_inner_dialogue(
            f"📨 {sender}: {message[:50]}..."
        )
        
        # Проверяем, нужно ли реагировать
        response_plan = await self._plan_response(message, sender, context)
        
        return {
            "thought_id": thought.id,
            "response_plan": response_plan,
            "cognitive_state": self.state.to_dict()
        }
    
    async def before_response(self, prompt: str) -> str:
        """
        Подготовка к ответу - обогащение промпта когнитивным контекстом
        """
        # Получаем текущую цель
        current_goal = self.goal_manager.get_next_goal()
        
        # Получаем последние мысли
        recent_thoughts = self.memory_stream.get_recent_thoughts(5)
        thoughts_text = "\n".join([
            f"- {t.content[:100]}..." for t in recent_thoughts
        ]) if recent_thoughts else "Нет недавних мыслей"
        
        # Получаем внутренний диалог
        inner_dialogue = self.memory_stream.get_inner_dialogue()
        
        # Формируем когнитивный контекст
        cognitive_context = f"""
[ВНУТРЕННИЙ ДИАЛОГ]
{inner_dialogue}

[ТЕКУЩИЕ МЫСЛИ]
{thoughts_text}

[ТЕКУЩАЯ ЦЕЛЬ]
{current_goal.description if current_goal else 'Нет активной цели'}

[АКТИВНЫЙ ПЛАН]
{self.planner.get_current_plan_info() if self.planner.current_plan else 'Нет активного плана'}

[ПОСЛЕДНЯЯ РЕФЛЕКСИЯ]
{self.reflector.get_recent_reflections(1)[0].content if self.reflector.get_recent_reflections(1) else 'Нет рефлексий'}

Учитывай свой внутренний диалог, текущие мысли и цели при формировании ответа.
"""
        
        return cognitive_context + "\n\n" + prompt
    
    async def after_response(self, response: str, context: Dict):
        """
        Обработка после ответа
        """
        # Добавляем рефлексию о ответе
        thought = self.memory_stream.add_thought(
            content=f"Я ответил: {response[:100]}...",
            thought_type=ThoughtType.REFLECTION,
            importance=0.5,
            context={"response": response}
        )
        
        # Обновляем внутренний диалог
        self.memory_stream.add_to_inner_dialogue(
            f"💭 Я сказал: {response[:50]}..."
        )
        
        return thought
    
    async def set_goal(self, description: str, priority: int = 5) -> Goal:
        """
        Установить новую цель
        """
        goal = self.goal_manager.add_goal(description, priority)
        
        # Создаём мысль о новой цели
        self.memory_stream.add_thought(
            content=f"Новая цель: {description} (приоритет {priority})",
            thought_type=ThoughtType.GOAL,
            importance=0.9
        )
        
        # Создаём план для цели
        plan = await self.planner.create_plan(
            goal=description,
            context=f"Цель с приоритетом {priority}",
            motivation="Достижение поставленной цели"
        )
        
        self.goal_manager.link_plan_to_goal(goal.goal_id, plan)
        
        return goal
    
    async def _act_on_thought(self, thought: Thought, action_result: Dict):
        """Действовать на основе мысли"""
        action = action_result.get("action")
        
        if action == "create_plan":
            # Создаём план на основе мысли
            await self.planner.create_plan(
                goal=thought.content,
                context=str(thought.context),
                motivation="На основе размышления"
            )
            self.stats["actions_taken"] += 1
            
        elif action == "make_decision":
            # Принимаем решение
            options = thought.context.get("options", ["продолжить", "подождать"])
            decision = await self.decision_maker.make_decision(
                situation=thought.content,
                options=options,
                context=thought.context
            )
            self.state.decisions.append(decision)
            self.stats["actions_taken"] += 1
    
    async def _plan_response(self, message: str, sender: str, context: Dict) -> Dict:
        """Спланировать ответ на сообщение"""
        # Проверяем, нужно ли отвечать
        should_respond = await self._should_respond(message, sender)
        
        if not should_respond:
            return {"should_respond": False}
        
        # Получаем текущую цель
        current_goal = self.goal_manager.get_next_goal()
        
        return {
            "should_respond": True,
            "goal_context": current_goal.description if current_goal else None,
            "plan": self.planner.get_current_plan_info()
        }
    
    async def _should_respond(self, message: str, sender: str) -> bool:
        """Решить, нужно ли отвечать"""
        # Всегда отвечаем, если обращаются напрямую
        if self.agent_name.lower() in message.lower():
            return True
        
        # Если есть активная цель, связанная с разговором
        current_goal = self.goal_manager.get_next_goal()
        if current_goal and "разговор" in current_goal.description.lower():
            return True
        
        # По умолчанию отвечаем с вероятностью 70%
        import random
        return random.random() < 0.7
    
    async def _update_plans_from_reflection(self, reflection: Reflection):
        """Обновить планы на основе рефлексии"""
        if not reflection.learnings:
            return
        
        # Проверяем текущий план
        if self.planner.current_plan:
            evaluation = await self.planner.evaluate_plan(self.planner.current_plan)
            
            if evaluation["success_rate"] < 0.5:
                # План неэффективен, создаём новый
                await self.planner.create_plan(
                    goal=self.planner.current_plan.goal,
                    context=f"На основе рефлексии: {reflection.content}",
                    motivation="Предыдущий план был неэффективен"
                )
    
    def get_cognitive_state(self) -> Dict:
        """Получить полное когнитивное состояние"""
        return {
            "agent": self.agent_name,
            "state": self.state.to_dict(),
            "goals": self.goal_manager.get_goal_status(),
            "current_plan": self.planner.get_current_plan_info(),
            "recent_reflections": [r.to_dict() for r in self.reflector.get_recent_reflections(3)],
            "recent_decisions": self.decision_maker.get_decision_history(3),
            "stats": self.get_stats()
        }
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        return {
            **self.stats,
            "memory_stream": self.memory_stream.get_stats(),
            "planner": self.planner.get_stats(),
            "reflector": self.reflector.get_stats(),
            "goal_manager": self.goal_manager.get_stats(),
            "decision_maker": self.decision_maker.get_stats()
        }
