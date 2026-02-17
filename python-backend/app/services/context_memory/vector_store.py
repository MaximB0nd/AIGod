"""
Векторное хранилище для памяти с использованием ChromaDB
"""
import os
import json
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import uuid

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    print("ChromaDB not installed. Install with: pip install chromadb")

from .models import MemoryItem, MemoryType

class VectorMemoryStore:
    """
    Хранилище векторной памяти на базе ChromaDB
    """
    
    def __init__(self, 
                 collection_name: str = "agent_memory",
                 persist_directory: Optional[str] = None,
                 embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        
        if not CHROMA_AVAILABLE:
            raise ImportError("ChromaDB is required for vector memory store")
        
        # Инициализация клиента
        if persist_directory:
            self.client = chromadb.PersistentClient(path=persist_directory)
        else:
            self.client = chromadb.Client()
        
        # Функция эмбеддингов
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model
        )
        
        # Получаем или создаём коллекцию
        try:
            self.collection = self.client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
        
        # Кэш для метаданных
        self.metadata_cache = {}
        
        # Статистика
        self.stats = {
            "total_vectors": 0,
            "queries": 0,
            "adds": 0,
            "deletes": 0
        }
    
    def add_memory(self, memory: MemoryItem) -> str:
        """
        Добавить элемент памяти в векторное хранилище
        """
        # Создаём текст для эмбеддинга
        text_for_embedding = f"{memory.content} {' '.join(memory.tags)}"
        
        # Метаданные
        metadata = {
            "type": memory.type.value,
            "importance": memory.importance.value,
            "timestamp": memory.timestamp.isoformat(),
            "participants": json.dumps(memory.participants),
            "tags": json.dumps(memory.tags),
            "has_embedding": "true"
        }
        
        # Добавляем в коллекцию
        self.collection.add(
            documents=[text_for_embedding],
            metadatas=[metadata],
            ids=[memory.id]
        )
        
        self.stats["adds"] += 1
        self.stats["total_vectors"] = self.collection.count()
        
        return memory.id
    
    def add_memories(self, memories: List[MemoryItem]) -> List[str]:
        """
        Добавить несколько элементов памяти
        """
        ids = []
        documents = []
        metadatas = []
        
        for memory in memories:
            ids.append(memory.id)
            documents.append(f"{memory.content} {' '.join(memory.tags)}")
            metadatas.append({
                "type": memory.type.value,
                "importance": memory.importance.value,
                "timestamp": memory.timestamp.isoformat(),
                "participants": json.dumps(memory.participants),
                "tags": json.dumps(memory.tags),
                "has_embedding": "true"
            })
        
        if ids:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            self.stats["adds"] += len(ids)
            self.stats["total_vectors"] = self.collection.count()
        
        return ids
    
    def search_memory(self, 
                     query: str,
                     n_results: int = 5,
                     memory_type: Optional[MemoryType] = None,
                     min_importance: Optional[str] = None,
                     time_range: Optional[Tuple[datetime, datetime]] = None) -> List[Dict]:
        """
        Поиск в памяти по запросу
        """
        self.stats["queries"] += 1
        
        # Формируем where условие
        where = {}
        if memory_type:
            where["type"] = memory_type.value
        
        if min_importance:
            importance_order = ["trivial", "low", "medium", "high", "critical"]
            where["importance"] = {"$in": importance_order[importance_order.index(min_importance):]}
        
        # Выполняем поиск
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where if where else None
        )
        
        # Форматируем результаты
        formatted = []
        for i in range(len(results['ids'][0])):
            formatted.append({
                "id": results['ids'][0][i],
                "content": results['documents'][0][i],
                "metadata": results['metadatas'][0][i],
                "distance": results['distances'][0][i] if 'distances' in results else None
            })
        
        return formatted
    
    def get_relevant_context(self, 
                            query: str,
                            max_tokens: int = 1000,
                            importance_threshold: str = "medium") -> List[MemoryItem]:
        """
        Получить релевантный контекст для промпта
        """
        results = self.search_memory(
            query=query,
            n_results=10,
            min_importance=importance_threshold
        )
        
        # Преобразуем в MemoryItem (упрощённо)
        memories = []
        for r in results:
            memory = MemoryItem(
                id=r["id"],
                content=r["content"],
                type=MemoryType(r["metadata"]["type"]),
                importance=ImportanceLevel(r["metadata"]["importance"]),
                timestamp=datetime.fromisoformat(r["metadata"]["timestamp"]),
                tags=json.loads(r["metadata"]["tags"]),
                participants=json.loads(r["metadata"]["participants"])
            )
            memories.append(memory)
            
            # Грубая оценка токенов (по словам)
            tokens = len(memory.content.split())
            max_tokens -= tokens
            if max_tokens <= 0:
                break
        
        return memories
    
    def delete_memory(self, memory_id: str):
        """Удалить элемент памяти"""
        self.collection.delete(ids=[memory_id])
        self.stats["deletes"] += 1
        self.stats["total_vectors"] = self.collection.count()
    
    def delete_old_memories(self, days: int = 30):
        """Удалить старые воспоминания"""
        # В ChromaDB нет прямого удаления по времени,
        # поэтому получаем все и фильтруем
        all_items = self.collection.get()
        
        cutoff = datetime.now().timestamp() - (days * 24 * 3600)
        to_delete = []
        
        for i, metadata in enumerate(all_items['metadatas']):
            timestamp = datetime.fromisoformat(metadata['timestamp']).timestamp()
            if timestamp < cutoff:
                to_delete.append(all_items['ids'][i])
        
        if to_delete:
            self.collection.delete(ids=to_delete)
            self.stats["deletes"] += len(to_delete)
            self.stats["total_vectors"] = self.collection.count()
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        return {
            **self.stats,
            "collection_size": self.collection.count(),
            "persist_directory": self.persist_directory
        }
    
    def clear(self):
        """Очистить хранилище"""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function
        )
        self.stats = {k: 0 for k in self.stats}
