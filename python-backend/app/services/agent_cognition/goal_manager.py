"""
Управление целями агента
"""
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import heapq
import uuid

from .models import Goal, Plan

class GoalManager:
    """
    Менеджер целей агента
    """
    
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.goals: Dict[str, Goal] = {}
        self.goal_queue: List[tuple] = []  # (priority, created_at, goal_id)
        
        # История целей
        self.goal_history: List[Goal] = []
        
        # Статистика
        self.stats = {
            "goals_created": 0,
            "goals_completed": 0,
            "goals_active": 0
        }
    
    def add_goal(self, 
                description: str,
                priority: int = 5,
                deadline: Optional[datetime] = None,
                success_criteria: Optional[List[str]] = None) -> Goal:
        """
        Добавить новую цель
        """
        goal = Goal(
            goal_id=f"goal_{uuid.uuid4().hex[:8]}_{datetime.now().timestamp()}",
            agent_name=self.agent_name,
            description=description,
            priority=priority,
            created_at=datetime.now(),
            deadline=deadline,
            success_criteria=success_criteria or []
        )
        
        self.goals[goal.goal_id] = goal
        heapq.heappush(self.goal_queue, (priority, goal.created_at.timestamp(), goal.goal_id))
        
        self.stats["goals_created"] += 1
        self.stats["goals_active"] += 1
        
        return goal
    
    def get_next_goal(self) -> Optional[Goal]:
        """
        Получить следующую цель для выполнения (наивысший приоритет)
        """
        while self.goal_queue:
            priority, created_ts, goal_id = self.goal_queue[0]
            goal = self.goals.get(goal_id)
            
            if goal and goal.is_active:
                return goal
            else:
                # Удаляем неактивную
                heapq.heappop(self.goal_queue)
        
        return None
    
    def update_goal_progress(self, goal_id: str, progress_delta: float):
        """
        Обновить прогресс цели
        """
        goal = self.goals.get(goal_id)
        if goal and goal.is_active:
            goal.progress = min(1.0, goal.progress + progress_delta)
            
            if goal.progress >= 1.0:
                self.complete_goal(goal_id)
    
    def complete_goal(self, goal_id: str):
        """
        Отметить цель как выполненную
        """
        goal = self.goals.get(goal_id)
        if goal:
            goal.is_active = False
            goal.progress = 1.0
            self.stats["goals_completed"] += 1
            self.stats["goals_active"] -= 1
            self.goal_history.append(goal)
    
    def fail_goal(self, goal_id: str, reason: str):
        """
        Отметить цель как проваленную
        """
        goal = self.goals.get(goal_id)
        if goal:
            goal.is_active = False
            goal.metadata["failure_reason"] = reason
            self.stats["goals_active"] -= 1
            self.goal_history.append(goal)
    
    def link_plan_to_goal(self, goal_id: str, plan: Plan):
        """
        Привязать план к цели
        """
        goal = self.goals.get(goal_id)
        if goal:
            goal.plans.append(plan.plan_id)
    
    def get_active_goals(self) -> List[Goal]:
        """
        Получить все активные цели
        """
        return [g for g in self.goals.values() if g.is_active]
    
    def get_goals_by_priority(self, min_priority: int = 1) -> List[Goal]:
        """
        Получить цели с приоритетом выше указанного
        """
        active = self.get_active_goals()
        return [g for g in active if g.priority <= min_priority]
    
    def get_goal_status(self) -> Dict:
        """
        Получить статус по целям
        """
        active = self.get_active_goals()
        
        return {
            "total_active": len(active),
            "highest_priority": min((g.priority for g in active), default=None),
            "goals": [g.to_dict() for g in active[:5]],  # топ-5
            "completion_rate": self.stats["goals_completed"] / max(1, self.stats["goals_created"])
        }
    
    def evaluate_goals(self) -> List[Dict]:
        """
        Оценить прогресс по целям
        """
        evaluation = []
        for goal in self.get_active_goals():
            # Проверяем дедлайн
            deadline_status = "ok"
            if goal.deadline:
                time_left = (goal.deadline - datetime.now()).total_seconds()
                if time_left < 0:
                    deadline_status = "overdue"
                elif time_left < 3600:  # меньше часа
                    deadline_status = "urgent"
            
            evaluation.append({
                "goal_id": goal.goal_id,
                "description": goal.description,
                "progress": goal.progress,
                "priority": goal.priority,
                "deadline_status": deadline_status,
                "plans_count": len(goal.plans)
            })
        
        return evaluation
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        return {
            **self.stats,
            "goals_in_queue": len(self.goal_queue),
            "total_goals_ever": len(self.goal_history) + len(self.goals)
        }
