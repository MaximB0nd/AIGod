import sys
from pathlib import Path

print("Текущая директория:", Path.cwd())
print("sys.path:", sys.path)

try:
    from app.services.agents_orchestration import OrchestrationClient
    print("✅ Импорт успешен из", Path(__file__).parent)
except ImportError as e:
    print("❌ Ошибка импорта:", e)
    
    # Проверяем структуру
    root = Path(__file__).parent
    print(f"\nПроверка структуры в {root}:")
    
    app_path = root / 'app'
    if app_path.exists():
        print(f"✅ Папка app найдена")
        services_path = app_path / 'services'
        if services_path.exists():
            print(f"✅ Папка services найдена")
            orch_path = services_path / 'agents_orchestration'
            if orch_path.exists():
                print(f"✅ Папка agents_orchestration найдена")
                print(f"   Содержит: {[f.name for f in orch_path.iterdir()]}")
            else:
                print(f"❌ Папка agents_orchestration не найдена в {services_path}")
        else:
            print(f"❌ Папка services не найдена в {app_path}")
    else:
        print(f"❌ Папка app не найдена в {root}")
