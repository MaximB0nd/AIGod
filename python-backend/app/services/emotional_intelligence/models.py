from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
import math

class EmotionType(str, Enum):
    """Базовые эмоции"""
    JOY = "joy"                 # радость
    SADNESS = "sadness"         # грусть
    ANGER = "anger"             # гнев
    FEAR = "fear"               # страх
    TRUST = "trust"             # доверие
    DISGUST = "disgust"         # отвращение
    ANTICIPATION = "anticipation" # ожидание
    SURPRISE = "surprise"       # удивление
    
    # Составные эмоции
    LOVE = "love"               # любовь (joy + trust)
    GUILT = "guilt"             # вина (sadness + fear)
    SHAME = "shame"             # стыд (sadness + disgust)
    HOPE = "hope"               # надежда (joy + anticipation)
    ANXIETY = "anxiety"         # тревога (fear + anticipation)
    CONTEMPT = "contempt"       # презрение (anger + disgust)
    
    @classmethod
    def from_plutchik(cls, primary: str, secondary: str) -> Optional["EmotionType"]:
        """Получить составную эмоцию по модели Плутчика"""
        combinations = {
            (cls.JOY, cls.TRUST): cls.LOVE,
            (cls.SADNESS, cls.FEAR): cls.GUILT,
            (cls.SADNESS, cls.DISGUST): cls.SHAME,
            (cls.JOY, cls.ANTICIPATION): cls.HOPE,
            (cls.FEAR, cls.ANTICIPATION): cls.ANXIETY,
            (cls.ANGER, cls.DISGUST): cls.CONTEMPT
        }
        return combinations.get((primary, secondary))

@dataclass
class EmotionalState:
    """Эмоциональное состояние сущности"""
    entity: str
    
    # Базовые эмоции (0-1)
    emotions: Dict[EmotionType, float] = field(default_factory=lambda: {
        EmotionType.JOY: 0.0,
        EmotionType.SADNESS: 0.0,
        EmotionType.ANGER: 0.0,
        EmotionType.FEAR: 0.0,
        EmotionType.TRUST: 0.0,
        EmotionType.DISGUST: 0.0,
        EmotionType.ANTICIPATION: 0.0,
        EmotionType.SURPRISE: 0.0
    })
    
    # Мета-параметры
    intensity: float = 0.5       # общая интенсивность эмоций
    volatility: float = 0.3      # изменчивость (0-1)
    resilience: float = 0.5      # устойчивость к негативу (0-1)
    
    # История
    history: List[Dict] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    
    # Контекст
    context: Dict[str, Any] = field(default_factory=dict)
    
    def get_dominant_emotion(self, threshold: float = 0.3) -> Optional[EmotionType]:
        """Получить доминирующую эмоцию"""
        if not self.emotions:
            return None
        
        dominant = max(self.emotions.items(), key=lambda x: x[1])
        return dominant[0] if dominant[1] >= threshold else None
    
    def get_emotional_vector(self) -> Dict[str, float]:
        """Получить вектор эмоций для ML"""
        return {e.value: v for e, v in self.emotions.items()}
    
    def get_mood(self) -> str:
        """Получить общее настроение"""
        joy = self.emotions.get(EmotionType.JOY, 0)
        sadness = self.emotions.get(EmotionType.SADNESS, 0)
        anger = self.emotions.get(EmotionType.ANGER, 0)
        
        if joy > sadness and joy > anger:
            return "позитивное"
        elif sadness > joy and sadness > anger:
            return "грустное"
        elif anger > joy and anger > sadness:
            return "раздражительное"
        else:
            return "нейтральное"
    
    def get_emotional_intelligence_score(self) -> float:
        """Получить общий показатель эмоционального интеллекта"""
        # Чем больше разнообразие эмоций и лучше контроль, тем выше EQ
        emotional_range = len([v for v in self.emotions.values() if v > 0.2]) / len(self.emotions)
        stability = 1 - self.volatility
        positivity = self.emotions.get(EmotionType.JOY, 0)
        
        return (emotional_range * 0.3 + stability * 0.4 + positivity * 0.3)
    
    def update(self, delta: Dict[EmotionType, float], 
               reason: str = "", source: str = "system"):
        """Обновить эмоциональное состояние"""
        old_state = self.get_emotional_vector()
        
        # Применяем изменения с учётом volatility
        for emotion, change in delta.items():
            if emotion in self.emotions:
                # Более высокая volatility = более сильная реакция
                effective_change = change * (1 + self.volatility)
                self.emotions[emotion] = max(0.0, min(1.0, 
                    self.emotions[emotion] + effective_change))
        
        # Обновляем интенсивность
        self.intensity = sum(self.emotions.values()) / len(self.emotions)
        self.last_updated = datetime.now()
        
        # Сохраняем в историю
        self.history.append({
            "timestamp": self.last_updated.isoformat(),
            "old_state": old_state,
            "new_state": self.get_emotional_vector(),
            "delta": {e.value: d for e, d in delta.items()},
            "reason": reason,
            "source": source,
            "intensity": self.intensity
        })
        
        # Ограничиваем историю
        if len(self.history) > 100:
            self.history = self.history[-100:]
    
    def apply_decay(self, factor: float = 0.1):
        """Затухание эмоций со временем"""
        for emotion in self.emotions:
            self.emotions[emotion] *= (1 - factor)
        
        self.intensity *= (1 - factor)
    
    def to_dict(self) -> Dict:
        """Экспорт в словарь для API"""
        return {
            "entity": self.entity,
            "emotions": {e.value: v for e, v in self.emotions.items()},
            "dominant_emotion": self.get_dominant_emotion().value if self.get_dominant_emotion() else None,
            "mood": self.get_mood(),
            "intensity": self.intensity,
            "volatility": self.volatility,
            "resilience": self.resilience,
            "eq_score": self.get_emotional_intelligence_score(),
            "last_updated": self.last_updated.isoformat(),
            "history": self.history[-10:]  # последние 10 событий
        }

@dataclass
class EmotionalProfile:
    """Эмоциональный профиль сущности (черты характера)"""
    entity: str
    
    # Базовые черты
    openness: float = 0.5      # открытость опыту
    conscientiousness: float = 0.5  # добросовестность
    extraversion: float = 0.5   # экстраверсия
    agreeableness: float = 0.5   # доброжелательность
    neuroticism: float = 0.5     # нейротизм
    
    # Эмоциональные триггеры
    triggers: Dict[str, float] = field(default_factory=dict)
    
    # Стиль общения
    communication_style: str = "neutral"  # friendly, aggressive, shy, etc.
    
    def to_dict(self) -> Dict:
        return {
            "entity": self.entity,
            "big_five": {
                "openness": self.openness,
                "conscientiousness": self.conscientiousness,
                "extraversion": self.extraversion,
                "agreeableness": self.agreeableness,
                "neuroticism": self.neuroticism
            },
            "communication_style": self.communication_style
        }

@dataclass
class EmotionAnalysisResult:
    """Результат анализа эмоций в сообщении"""
    message_id: str
    sender: str
    content: str
    timestamp: datetime
    
    # Обнаруженные эмоции
    detected_emotions: Dict[EmotionType, float]
    
    # Основная эмоция
    primary_emotion: EmotionType
    intensity: float
    
    # Тональность
    sentiment: float  # -1 до 1
    
    # Объяснение
    reason: str
    
    # Влияние на собеседников
    emotional_impact: Dict[str, Dict[EmotionType, float]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "message_id": self.message_id,
            "sender": self.sender,
            "timestamp": self.timestamp.isoformat(),
            "detected_emotions": {e.value: v for e, v in self.detected_emotions.items()},
            "primary_emotion": self.primary_emotion.value,
            "intensity": self.intensity,
            "sentiment": self.sentiment,
            "reason": self.reason,
            "emotional_impact": {
                target: {e.value: v for e, v in emotions.items()}
                for target, emotions in self.emotional_impact.items()
            }
        }

@dataclass
class EmotionalContext:
    """Эмоциональный контекст разговора"""
    conversation_id: str
    participants: List[str]
    
    # Общая эмоциональная атмосфера
    atmosphere: str = "neutral"
    emotional_temperature: float = 0.5  # накал страстей
    
    # Тренды
    trends: Dict[str, float] = field(default_factory=dict)
    
    # Ключевые моменты
    key_moments: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "conversation_id": self.conversation_id,
            "participants": self.participants,
            "atmosphere": self.atmosphere,
            "emotional_temperature": self.emotional_temperature,
            "trends": self.trends,
            "key_moments": self.key_moments[-5:]  # последние 5 моментов
        }
