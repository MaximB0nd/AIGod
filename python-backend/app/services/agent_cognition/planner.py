"""
Система планирования действий агента
"""
import asyncio
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime, timedelta
import uuid

from .models import Plan, PlanStep, PlanStatus, Goal

class Planner:
    """
    Планировщик действий агента
    """
    
    def __init__(self, agent_name: str, chat_service=None):
        self.agent_name = agent_name
        self.chat_service = chat_service
        
        # Активные планы
        self.active_plans: Dict[str, Plan] = {}
        
        # История планов
        self.plan_history: List[Plan] = []
        
        # Текущий выполняемый план
        self.current_plan: Optional[Plan] = None
        
        # Статистика
        self.stats = {
            "plans_created": 0,
            "plans_completed": 0,
            "plans_failed": 0,
            "steps_executed": 0
        }
    
    async def create_plan(self, 
                         goal: str,
                         context: str = "",
                         motivation: str = "",
                         use_ai: bool = True) -> Plan:
        """
        Создать план для достижения цели
        """
        plan = Plan(
            plan_id=f"plan_{uuid.uuid4().hex[:8]}_{datetime.now().timestamp()}",
            agent_name=self.agent_name,
            goal=goal,
            context=context,
            motivation=motivation,
            status=PlanStatus.ACTIVE
        )
        
        if use_ai and self.chat_service:
            # Используем AI для генерации шагов
            steps = await self._generate_plan_steps(goal, context)
            for i, step_desc in enumerate(steps):
                plan.add_step(step_desc, i)
        else:
            # Минимальный план
            plan.add_step(f"Выполнить: {goal}", 0)
        
        self.active_plans[plan.plan_id] = plan
        self.plan_history.append(plan)
        self.stats["plans_created"] += 1
        
        # Устанавливаем как текущий, если нет активного
        if not self.current_plan:
            self.current_plan = plan
        
        return plan
    
    async def _generate_plan_steps(self, goal: str, context: str) -> List[str]:
        """Сгенерировать шаги плана с помощью AI"""
        if not self.chat_service:
            return [f"Шаг 1: {goal}"]
        
        prompt = f"""
        Ты планировщик. Создай пошаговый план для достижения цели.
        
        Цель: {goal}
        Контекст: {context}
        
        Сгенерируй 3-5 конкретных, выполнимых шагов.
        Каждый шаг должен быть одной строкой.
        Ответь только списком шагов, без нумерации.
        """
        
        try:
            response = await self.chat_service(
                agent_name="planner",
                session_id=f"plan_{self.agent_name}",
                prompt=prompt
            )
            
            # Парсим ответ
            steps = [line.strip() for line in response.split('\n') 
                    if line.strip() and not line.startswith(('1.', '2.', '-'))]
            
            return steps[:5]  # максимум 5 шагов
            
        except Exception as e:
            print(f"Error generating plan steps: {e}")
            return [f"Шаг 1: {goal}"]
    
    async def execute_next_step(self, plan: Optional[Plan] = None) -> Optional[Dict]:
        """
        Выполнить следующий шаг плана
        """
        if plan is None:
            plan = self.current_plan
        
        if not plan or plan.status != PlanStatus.ACTIVE:
            return None
        
        next_step = plan.get_next_step()
        if not next_step:
            return None
        
        # Выполняем шаг
        result = await self._execute_step(next_step, plan)
        
        # Обновляем статус
        if result.get("success", False):
            plan.update_step_status(
                next_step.step_id, 
                PlanStatus.COMPLETED,
                result.get("outcome")
            )
            self.stats["steps_executed"] += 1
        else:
            plan.update_step_status(
                next_step.step_id,
                PlanStatus.FAILED,
                result.get("error")
            )
        
        return {
            "plan_id": plan.plan_id,
            "step": next_step.to_dict(),
            "result": result,
            "plan_progress": f"{sum(1 for s in plan.steps if s.status == PlanStatus.COMPLETED)}/{len(plan.steps)}"
        }
    
    async def _execute_step(self, step: PlanStep, plan: Plan) -> Dict:
        """
        Выполнить конкретный шаг
        """
        # Здесь будет логика выполнения шага
        # В базовой реализации просто возвращаем успех
        
        return {
            "success": True,
            "outcome": f"Шаг '{step.description}' выполнен",
            "timestamp": datetime.now().isoformat()
        }
    
    async def evaluate_plan(self, plan: Plan) -> Dict:
        """
        Оценить выполнение плана
        """
        completed = [s for s in plan.steps if s.status == PlanStatus.COMPLETED]
        failed = [s for s in plan.steps if s.status == PlanStatus.FAILED]
        
        evaluation = {
            "plan_id": plan.plan_id,
            "goal": plan.goal,
            "total_steps": len(plan.steps),
            "completed": len(completed),
            "failed": len(failed),
            "success_rate": len(completed) / len(plan.steps) if plan.steps else 0,
            "status": plan.status.value
        }
        
        if failed:
            evaluation["failure_points"] = [s.description for s in failed]
        
        return evaluation
    
    def get_current_plan_info(self) -> Optional[Dict]:
        """
        Получить информацию о текущем плане
        """
        if not self.current_plan:
            return None
        
        return {
            "goal": self.current_plan.goal,
            "status": self.current_plan.status.value,
            "next_step": self.current_plan.get_next_step().to_dict() 
                        if self.current_plan.get_next_step() else None,
            "progress": f"{sum(1 for s in self.current_plan.steps if s.status == PlanStatus.COMPLETED)}/{len(self.current_plan.steps)}"
        }
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        return {
            **self.stats,
            "active_plans": len(self.active_plans),
            "has_current_plan": self.current_plan is not None
        }
