from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime, timedelta
import uuid

class ThoughtType(str, Enum):
    """Тип мысли"""
    OBSERVATION = "observation"      # наблюдение
    REFLECTION = "reflection"        # рефлексия
    PLAN = "plan"                    # план
    DECISION = "decision"            # решение
    GOAL = "goal"                    # цель
    QUESTION = "question"            # вопрос
    INSIGHT = "insight"              # инсайт

class PlanStatus(str, Enum):
    """Статус плана"""
    DRAFT = "draft"                  # черновик
    ACTIVE = "active"                 # активен
    COMPLETED = "completed"           # выполнен
    FAILED = "failed"                 # провален
    CANCELLED = "cancelled"           # отменён

class ReflectionType(str, Enum):
    """Тип рефлексии"""
    SELF = "self"                      # о себе
    OTHER = "other"                     # о других
    RELATIONSHIP = "relationship"       # об отношениях
    TASK = "task"                        # о задаче
    LEARNING = "learning"                # о полученном опыте
    MISTAKE = "mistake"                  # об ошибке

@dataclass
class Thought:
    """Мысль агента"""
    id: str
    agent_name: str
    type: ThoughtType
    content: str
    timestamp: datetime
    importance: float = 0.5  # от 0 до 1
    
    # Связи
    parent_thought: Optional[str] = None  # ID родительской мысли
    related_thoughts: List[str] = field(default_factory=list)
    
    # Контекст
    context: Dict[str, Any] = field(default_factory=dict)
    emotional_state: Dict[str, float] = field(default_factory=dict)
    
    # Метаданные
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "agent": self.agent_name,
            "type": self.type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "importance": self.importance,
            "related_thoughts": self.related_thoughts
        }

@dataclass
class PlanStep:
    """Шаг плана"""
    step_id: str
    description: str
    order: int
    status: PlanStatus = PlanStatus.DRAFT
    
    # Ожидаемый результат
    expected_outcome: Optional[str] = None
    
    # Зависимости
    dependencies: List[str] = field(default_factory=list)
    
    # Временные рамки
    estimated_duration: Optional[int] = None  # в секундах
    deadline: Optional[datetime] = None
    
    # Результат выполнения
    actual_outcome: Optional[str] = None
    completed_at: Optional[datetime] = None
    reflection: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "step_id": self.step_id,
            "description": self.description,
            "order": self.order,
            "status": self.status.value,
            "dependencies": self.dependencies
        }

@dataclass
class Plan:
    """План действий агента"""
    plan_id: str
    agent_name: str
    goal: str  # цель плана
    steps: List[PlanStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # Контекст создания
    context: str = ""
    motivation: str = ""  # почему этот план
    
    # Результаты
    result: Optional[str] = None
    reflection: Optional[str] = None
    
    def add_step(self, description: str, order: Optional[int] = None) -> PlanStep:
        """Добавить шаг"""
        step = PlanStep(
            step_id=f"step_{uuid.uuid4().hex[:8]}",
            description=description,
            order=order if order is not None else len(self.steps)
        )
        self.steps.append(step)
        self.updated_at = datetime.now()
        return step
    
    def get_next_step(self) -> Optional[PlanStep]:
        """Получить следующий шаг для выполнения"""
        for step in sorted(self.steps, key=lambda x: x.order):
            if step.status == PlanStatus.DRAFT:
                # Проверяем зависимости
                deps_met = all(
                    any(s.status == PlanStatus.COMPLETED and s.step_id == dep
                        for s in self.steps)
                    for dep in step.dependencies
                )
                if deps_met:
                    return step
        return None
    
    def update_step_status(self, step_id: str, status: PlanStatus, outcome: Optional[str] = None):
        """Обновить статус шага"""
        for step in self.steps:
            if step.step_id == step_id:
                step.status = status
                if outcome:
                    step.actual_outcome = outcome
                if status == PlanStatus.COMPLETED:
                    step.completed_at = datetime.now()
                break
        self.updated_at = datetime.now()
        
        # Проверяем, завершён ли весь план
        if all(s.status == PlanStatus.COMPLETED for s in self.steps):
            self.status = PlanStatus.COMPLETED
        elif any(s.status == PlanStatus.FAILED for s in self.steps):
            self.status = PlanStatus.FAILED
    
    def to_dict(self) -> Dict:
        return {
            "plan_id": self.plan_id,
            "agent": self.agent_name,
            "goal": self.goal,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps],
            "progress": f"{sum(1 for s in self.steps if s.status == PlanStatus.COMPLETED)}/{len(self.steps)}",
            "created_at": self.created_at.isoformat()
        }

@dataclass
class Reflection:
    """Рефлексия агента"""
    reflection_id: str
    agent_name: str
    type: ReflectionType
    content: str
    timestamp: datetime
    
    # На основе чего
    based_on: List[str] = field(default_factory=list)  # ID мыслей/действий
    
    # Выводы
    insights: List[str] = field(default_factory=list)
    learnings: List[str] = field(default_factory=list)
    
    # Влияние на будущее
    impacts: Dict[str, Any] = field(default_factory=dict)
    
    # Оценка
    confidence: float = 0.5  # насколько уверен в рефлексии
    
    def to_dict(self) -> Dict:
        return {
            "reflection_id": self.reflection_id,
            "agent": self.agent_name,
            "type": self.type.value,
            "content": self.content,
            "insights": self.insights,
            "learnings": self.learnings,
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class Goal:
    """Цель агента"""
    goal_id: str
    agent_name: str
    description: str
    priority: int  # 1 - наивысший
    created_at: datetime = field(default_factory=datetime.now)
    
    # Статус
    is_active: bool = True
    deadline: Optional[datetime] = None
    progress: float = 0.0  # 0-1
    
    # Связанные планы
    plans: List[str] = field(default_factory=list)
    
    # Метрики
    success_criteria: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "goal_id": self.goal_id,
            "description": self.description,
            "priority": self.priority,
            "progress": self.progress,
            "is_active": self.is_active,
            "plans_count": len(self.plans)
        }

@dataclass
class Decision:
    """Принятое решение"""
    decision_id: str
    agent_name: str
    situation: str  # ситуация
    options: List[str]  # рассмотренные варианты
    chosen: str  # выбранный вариант
    reason: str  # причина выбора
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Контекст
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Результат (заполняется позже)
    outcome: Optional[str] = None
    reflection: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "decision_id": self.decision_id,
            "agent": self.agent_name,
            "situation": self.situation,
            "chosen": self.chosen,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class CognitiveState:
    """Когнитивное состояние агента"""
    agent_name: str
    
    # Текущие мысли
    current_thoughts: List[Thought] = field(default_factory=list)
    
    # Активные планы
    active_plans: List[Plan] = field(default_factory=list)
    
    # Цели
    goals: List[Goal] = field(default_factory=list)
    
    # История рефлексий
    reflections: List[Reflection] = field(default_factory=list)
    
    # Принятые решения
    decisions: List[Decision] = field(default_factory=list)
    
    # Внутренний диалог
    inner_dialogue: List[str] = field(default_factory=list)
    
    # Метрики
    attention_focus: str = ""  # на чём сфокусирован
    cognitive_load: float = 0.0  # 0-1 когнитивная нагрузка
    
    def add_thought(self, thought: Thought):
        """Добавить мысль"""
        self.current_thoughts.append(thought)
        # Ограничиваем размер
        if len(self.current_thoughts) > 20:
            self.current_thoughts = self.current_thoughts[-20:]
    
    def get_active_goal(self) -> Optional[Goal]:
        """Получить самую приоритетную активную цель"""
        active = [g for g in self.goals if g.is_active]
        if active:
            return min(active, key=lambda g: g.priority)
        return None
    
    def to_dict(self) -> Dict:
        return {
            "agent": self.agent_name,
            "thoughts_count": len(self.current_thoughts),
            "active_plans": len(self.active_plans),
            "goals": [g.to_dict() for g in self.goals],
            "reflections_count": len(self.reflections),
            "attention": self.attention_focus,
            "cognitive_load": self.cognitive_load
        }
