#!/usr/bin/env python
"""
Скрипт для запуска примеров оркестрации
"""
import asyncio
import sys
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

# Импортируем пример
from app.services.agents_orchestration.examples.usage import main

if __name__ == "__main__":
    print("🚀 Запуск оркестрации из корня проекта")
    asyncio.run(main())
