"""
Пример использования MongoDB в START-beta

Этот файл показывает как работать с новой MongoDB интеграцией.
Запускать только после старта Docker (start-docker.bat)
"""

import os
from pathlib import Path

# Добавляем путь к shared
import sys
sys.path.append(os.path.dirname(__file__))

from shared import MongoDBManager, OllamaManager


def demo_mongodb_features():
    """Демонстрация всех возможностей MongoDB"""
    
    print("=" * 60)
    print("🚀 Демонстрация MongoDB интеграции START-beta")
    print("=" * 60)
    
    # Подключение к MongoDB
    try:
        db = MongoDBManager()
        print("\n✅ Подключение к MongoDB успешно")
    except Exception as e:
        print(f"\n❌ Ошибка подключения: {e}")
        print("Убедитесь что Docker запущен: start-docker.bat")
        return
    
    # Проверка состояния
    stats = db.health_check()
    print(f"\n📊 Статистика БД: {stats}")
    
    # ==================== 1. СОЗДАНИЕ ПРОЕКТА ====================
    print("\n" + "=" * 60)
    print("1️⃣ Создание проекта")
    print("=" * 60)
    
    project_id = db.create_project(
        name="demo_project",
        path="/home/user/projects/demo",
        settings={
            "max_context_lines": 50,
            "convert_to_txt": True,
            "file_extensions": [".py", ".js", ".html"]
        }
    )
    print(f"✅ Проект создан: {project_id}")
    
    # Получение проекта
    project = db.get_project(project_id)
    print(f"📁 Проект: {project['name']}")
    print(f"⚙️  Настройки: {project['settings']}")
    
    # ==================== 2. СОХРАНЕНИЕ ФАЙЛОВ ====================
    print("\n" + "=" * 60)
    print("2️⃣ Сохранение файлов (твоя идея с TXT)")
    print("=" * 60)
    
    # Пример кода Python
    python_code = '''
def hello_world():
    """Пример функции"""
    print("Hello, World!")
    return "Success"

class MyClass:
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value

if __name__ == "__main__":
    result = hello_world()
    print(result)
'''
    
    # Сохраняем с обрезкой по умолчанию (50 строк)
    db.store_file_content(
        project_id=project_id,
        file_path="main.py",
        content=python_code,
        language="python"
    )
    print("✅ Файл main.py сохранен (50 строк по умолчанию)")
    
    # Пример длинного файла (будет обрезан)
    long_code = '\n'.join([f'# Строка {i}' for i in range(1, 101)])
    
    db.store_file_content(
        project_id=project_id,
        file_path="long_file.py",
        content=long_code,
        max_lines=30  # Твоя идея: указать количество строк
    )
    print("✅ Файл long_file.py сохранен (30 строк, указано вручную)")
    
    # ==================== 3. AI КОНТЕКСТ (5-оконная система) ====================
    print("\n" + "=" * 60)
    print("3️⃣ AI Контекст (раздвижное окно из 5)")
    print("=" * 60)
    
    # Добавляем 5 сообщений
    messages = [
        ("user", "Как создать класс в Python?"),
        ("assistant", "Для создания класса используйте ключевое слово class..."),
        ("user", "А как добавить методы?"),
        ("assistant", "Методы добавляются как функции внутри класса..."),
        ("user", "Как наследовать класс?"),
    ]
    
    for role, content in messages:
        context = db.add_message_to_context(project_id, role, content)
        print(f"💬 Добавлено: {role} | Контекст: {len(context)}/5")
    
    print("\n📋 Текущий контекст:")
    for msg in context:
        print(f"   [{msg['position']}] {msg['role']}: {msg['content'][:50]}...")
    
    # Добавляем 6-е сообщение - первое удалится
    print("\n➕ Добавляем 6-е сообщение...")
    db.add_message_to_context(project_id, "assistant", "Наследование делается через class Child(Parent)...")
    
    new_context = db.get_context(project_id)
    print(f"✅ Новый контекст: {len(new_context)}/5 (самое старое удалено)")
    
    print("\n📋 Новый контекст:")
    for msg in new_context:
        print(f"   [{msg['position']}] {msg['role']}: {msg['content'][:50]}...")
    
    # ==================== 4. ПОЛНАЯ ИСТОРИЯ ====================
    print("\n" + "=" * 60)
    print("4️⃣ Полная история диалогов (не удаляется)")
    print("=" * 60)
    
    # Сохраняем полную историю отдельно
    full_messages = [
        {"role": "user", "content": "Вопрос 1", "timestamp": "..."},
        {"role": "assistant", "content": "Ответ 1", "timestamp": "..."},
        # ... все 6 сообщений
    ]
    
    db.save_full_conversation(project_id, "session_001", full_messages)
    print("✅ Полная история сохранена (6 сообщений)")
    
    # Получаем историю
    history = db.get_conversation_history(project_id)
    print(f"📚 Всего сессий в истории: {len(history)}")
    
    # ==================== 5. КЭШ AI ====================
    print("\n" + "=" * 60)
    print("5️⃣ Кэширование ответов AI")
    print("=" * 60)
    
    # Сохраняем ответ в кэш
    prompt = "Как работает класс в Python?"
    response = "Класс - это шаблон для создания объектов..."
    
    db.cache_response(prompt, response, model="llama3.1")
    print("✅ Ответ закэширован")
    
    # Получаем из кэша
    cached = db.get_cached_response(prompt)
    if cached:
        print("🎯 Попадание в кэш!")
        print(f"   Кэшированный ответ: {cached[:50]}...")
    
    # ==================== 6. ДЕРЕВО ФАЙЛОВ ====================
    print("\n" + "=" * 60)
    print("6️⃣ Обновление дерева файлов")
    print("=" * 60)
    
    file_tree = {
        "folders": ["src", "tests", "docs"],
        "files": [
            {"name": "main.py", "path": "main.py", "size": 2048},
            {"name": "utils.py", "path": "src/utils.py", "size": 1024},
            {"name": "test_main.py", "path": "tests/test_main.py", "size": 512}
        ]
    }
    
    db.update_project_file_tree(project_id, file_tree)
    print("✅ Дерево файлов обновлено")
    
    # Получаем обновленный проект
    updated_project = db.get_project(project_id)
    print(f"📁 Папок: {len(updated_project['file_tree']['folders'])}")
    print(f"📄 Файлов: {len(updated_project['file_tree']['files'])}")
    
    # ==================== 7. ВСЕ ПРОЕКТЫ ====================
    print("\n" + "=" * 60)
    print("7️⃣ Список всех проектов")
    print("=" * 60)
    
    all_projects = db.get_all_projects()
    print(f"📊 Всего проектов: {len(all_projects)}")
    for proj in all_projects:
        print(f"   • {proj['name']} ({proj['path']})")
    
    # ==================== ЗАВЕРШЕНИЕ ====================
    print("\n" + "=" * 60)
    print("✅ Демонстрация завершена")
    print("=" * 60)
    
    # Финальная статистика
    final_stats = db.health_check()
    print(f"\n📊 Финальная статистика:")
    for key, value in final_stats.items():
        print(f"   • {key}: {value}")
    
    # Закрытие соединения
    db.close()
    print("\n🔌 Соединение закрыто")
    print("\n💡 Откройте http://localhost:8081 для просмотра в Mongo Express")


if __name__ == "__main__":
    demo_mongodb_features()
