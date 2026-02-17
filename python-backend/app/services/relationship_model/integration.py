"""
Интеграция системы отношений с модулем оркестрации агентов
"""
from typing import Optional, List, Dict, Any
from datetime import datetime

from .manager import RelationshipManager
from .analyzer import RelationshipAnalyzer
from .models import AnalysisResult

class OrchestrationIntegration:
    """
    Интеграция системы отношений с OrchestrationClient
    """
    
    def __init__(self, 
                 relationship_manager: RelationshipManager,
                 auto_analyze: bool = True):
        
        self.manager = relationship_manager
        self.auto_analyze = auto_analyze
        
        # Статистика интеграции
        self.stats = {
            "messages_processed": 0,
            "relationships_updated": 0
        }
    
    def register_agents(self, agent_names: List[str]):
        """Зарегистрировать агентов в системе отношений"""
        self.manager.register_participants(agent_names)
    
    async def on_agent_message(self, 
                               message: str,
                               sender: str,
                               participants: List[str],
                               message_id: Optional[str] = None) -> Optional[Dict]:
        """
        Обработчик сообщения от агента
        """
        self.stats["messages_processed"] += 1
        
        if not self.auto_analyze or not self.manager.analyzer:
            return None
        
        # Анализируем сообщение
        result = await self.manager.process_message(
            message=message,
            sender=sender,
            participants=participants,
            message_id=message_id
        )
        
        if result:
            self.stats["relationships_updated"] += len(result.impacts)
            
            # Возвращаем информацию об изменениях
            return {
                "message_id": result.message_id,
                "impacts": result.impacts,
                "reason": result.reason,
                "updates": [
                    {
                        "from": sender,
                        "to": target,
                        "delta": impact * self.manager.analyzer.influence_coefficient,
                        "new_value": self.manager.get_relationship_value(sender, target)
                    }
                    for target, impact in result.impacts.items()
                ]
            }
        
        return None
    
    async def on_user_message(self,
                              message: str,
                              participants: List[str],
                              user_name: str = "user") -> Optional[Dict]:
        """
        Обработчик сообщения от пользователя
        """
        # Пользователь тоже влияет на отношения
        return await self.on_agent_message(
            message=message,
            sender=user_name,
            participants=participants
        )
    
    def get_agent_relationships(self, agent_name: str) -> Dict:
        """Получить отношения агента"""
        return self.manager.get_relationship_summary(agent_name)
    
    def get_all_relationships(self) -> Dict:
        """Получить все отношения"""
        return self.manager.get_full_state()
    
    def enhance_prompt_with_relationships(self, 
                                          agent_name: str,
                                          original_prompt: str) -> str:
        """
        Обогатить промпт информацией об отношениях
        """
        rels = self.manager.get_entity_relationships(agent_name)
        
        if not rels:
            return original_prompt
        
        # Формируем описание отношений
        rel_text = []
        for other, value in rels.items():
            if other != agent_name:
                rel_type = self.manager.get_relationship_type(agent_name, other)
                emoji = self._get_relationship_emoji(value)
                rel_text.append(f"{emoji} {other}: {rel_type} ({value:.2f})")
        
        if not rel_text:
            return original_prompt
        
        relationship_context = "\n".join([
            "\n[Твои отношения с другими:]",
            *rel_text,
            "\nУчитывай эти отношения в своём ответе.",
            "Если отношения хорошие - будь дружелюбнее.",
            "Если отношения плохие - будь сдержаннее.",
            ""
        ])
        
        return relationship_context + original_prompt
    
    def _get_relationship_emoji(self, value: float) -> str:
        """Получить эмодзи для значения отношений"""
        if value >= 0.7:
            return "❤️"
        elif value >= 0.4:
            return "😊"
        elif value >= 0.1:
            return "🙂"
        elif value >= -0.1:
            return "😐"
        elif value >= -0.4:
            return "😕"
        elif value >= -0.7:
            return "😠"
        else:
            return "💔"
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        return {
            **self.stats,
            "analyzer_stats": self.manager.analyzer.get_stats() if self.manager.analyzer else None,
            "network_stats": self.manager.get_network_stats()
        }
