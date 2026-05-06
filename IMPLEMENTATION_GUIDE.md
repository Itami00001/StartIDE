# Руководство по использованию Этапов 7 и 8

## 📋 Обзор

Реализованы Этап 7 (Технологический стек) и Этап 8 (Чат и AI интеграция) согласно плану разработки базы данных.

## 🎯 Этап 7: Технологический стек

### Компоненты

#### 1. `shared/tech_stack_detector.py`
Автоопределение технологий из файлов проекта:
- Анализ расширений файлов
- Поиск импортов и зависимостей
- Определение фреймворков и библиотек
- Анализ конфигурационных файлов

#### 2. `shared/git_manager.py` (обновлен)
Git анализ зависимостей:
- Анализ `package.json`, `requirements.txt`
- Определение менеджеров пакетов
- История коммитов для технологий
- Сохранение в базу данных

#### 3. `shared/tech_stack_manager.py`
Управление технологическим стеком:
- Объединение результатов автоопределения
- Ручное редактирование стека
- Обновление `tech_stack.txt`
- Статистика и сводки

### Использование

```python
from shared.tech_stack_manager import TechStackManager

# Инициализация
tech_manager = TechStackManager(project_path, db_manager)

# Полный анализ
tech_stack = tech_manager.analyze_and_save_tech_stack(project_id)

# Ручное добавление технологии
tech_manager.add_manual_tech_item(project_id, "Docker", "20.10")

# Получение сводки
summary = tech_manager.get_tech_stack_summary(project_id)
```

## 🎯 Этап 8: Чат и AI интеграция

### Компоненты

#### 1. `shared/chat_manager.py`
Управление чатом в sqlite3:
- Добавление/получение сообщений
- Поддержка голосовых сообщений
- История диалога
- Статистика чата

#### 2. `StartIDE/voice_manager.py` (обновлен)
Голосовые сообщения в StartIDE:
- Запись голосовых сообщений
- Распознавание речи
- Сохранение аудио файлов
- Text-to-speech для ответов

#### 3. `shared/ai_integration_manager.py`
Интеграция с Ollama API:
- Подготовка контекста для AI
- Отправка сообщений в Ollama
- Анализ кода
- Кэширование контекста

### Использование

```python
from shared.ai_integration_manager import AIIntegrationManager
from StartIDE.voice_manager import VoiceManager

# Инициализация
ai_manager = AIIntegrationManager(db_manager)
voice_manager = VoiceManager()

# Отправка сообщения AI
success, response = ai_manager.send_message_to_ai(
    project_id=1,
    message="Как оптимизировать этот код?",
    message_type="text"
)

# Запись голосового сообщения
voice_file = voice_manager.record_voice_message(
    project_id=1,
    chat_manager=ai_manager.chat_manager
)

# Анализ кода
success, analysis = ai_manager.analyze_code_with_ai(
    project_id=1,
    file_path="main.py",
    code_content=code_content
)
```

## 🗄️ Структура базы данных

### Таблица `tech_stack`
```sql
CREATE TABLE tech_stack (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    technology TEXT NOT NULL,
    version TEXT,
    detected_by TEXT,  -- "auto", "manual", "git"
    confidence REAL DEFAULT 1.0,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Таблица `chat_messages`
```sql
CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    sender TEXT NOT NULL,  -- "StartIDE", "StartOffice", "AI"
    message_type TEXT NOT NULL,  -- "text", "voice", "file_analysis"
    content TEXT NOT NULL,
    voice_file_path TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 📁 Структура файлов контекста

```
context/
├── projects/
│   └── project_{id}/
│       ├── tech_stack.txt     # Технологический стек
│       ├── chat_context.txt   # История чата
│       ├── git_context.txt    # Git информация
│       └── code_snippets.txt  # Отслеживаемые файлы
├── voice_messages/            # Голосовые сообщения
└── voice_responses/           # Голосовые ответы AI
```

## 🔧 Интеграция с StartIDE и StartOffice

### StartIDE (основное приложение)
```python
# В main.py
from shared.ai_integration_manager import AIIntegrationManager
from StartIDE.voice_manager import VoiceManager

class StartIDE:
    def __init__(self):
        self.ai_manager = AIIntegrationManager(self.db_manager)
        self.voice_manager = VoiceManager()
        
    def send_to_ai(self, message):
        success, response = self.ai_manager.send_message_to_ai(
            self.current_project_id,
            message
        )
        return response
```

### StartOffice (документация)
```python
# В main.py
from shared.tech_stack_manager import TechStackManager

class StartOffice:
    def __init__(self):
        self.tech_manager = TechStackManager(self.project_path, self.db_manager)
        
    def load_project_tech_stack(self, project_id):
        return self.tech_manager.get_tech_stack_from_db(project_id)
```

## 🎨 UI изменения

### StartIDE - Панель AI чата
```
┌─────────────────────────────────────┐
│ 🤖 AI Ассистент                     │
├─────────────────────────────────────┤
│ [История диалога]                   │
│ 👤: Как оптимизировать этот код?    │
│ 🤖: Рекомендую использовать...     │
│                                     │
│ [🎙️ Голосовое сообщение]            │
│ [📄 Анализ файла]                   │
└─────────────────────────────────────┘
```

### StartOffice - Технологический стек
```
┌─────────────────────────────────────┐
│ 🛠️ Технологический стек             │
├─────────────────────────────────────┤
│ Python 3.10 (0.9) - auto           │
│ Tkinter (0.8) - auto                │
│ Requests 2.31.0 (0.9) - auto        │
│                                     │
│ [+ Добавить технологию]             │
│ [🔄 Обновить анализ]                 │
└─────────────────────────────────────┘
```

## 📝 Примеры использования

### 1. Автоопределение технологического стека
```python
# Анализ проекта
tech_stack = tech_manager.analyze_and_save_tech_stack(project_id)

# Результат в tech_stack.txt:
=== ТЕХНОЛОГИЧЕСКИЙ СТЕК ===
Проект: MyProject
Обновлено: 2024-05-07T01:45:00

=== ОСНОВНЫЕ ТЕХНОЛОГИИ ===
Python 3.10
Tkinter
Requests 2.31.0
```

### 2. Голосовой чат с AI
```python
# Запись голосового сообщения
voice_file = voice_manager.record_voice_message(
    project_id=1,
    chat_manager=chat_manager
)

# Автоматический ответ AI
success, response = ai_manager.send_message_to_ai(
    project_id=1,
    message="Покажи структуру проекта",
    message_type="voice"
)

# Голосовой ответ
voice_response = voice_manager.play_voice_response(
    response,
    project_id=1
)
```

### 3. Анализ кода
```python
# Анализ файла
success, analysis = ai_manager.analyze_code_with_ai(
    project_id=1,
    file_path="main.py",
    code_content=code
)

# Результат:
"""
Анализ файла main.py:
✅ Код хорошо структурирован
⚠️ Рекомендуется добавить обработку исключений
💡 Можно оптимизировать импорты
"""
```

## 🚀 Следующие шаги

1. **Тестирование** - Проверить все компоненты
2. **UI интеграция** - Добавить панели интерфейса
3. **Оптимизация** - Настроить производительность
4. **Документация** - Подготовить пользовательскую документацию

## 📦 Зависимости

```txt
requests>=2.31.0
pathlib2>=2.3.7
speechrecognition>=3.10.0
pyttsx3>=2.90
pyaudio>=0.2.11
gitpython>=3.1.0
psutil>=5.9.0
packaging>=21.0
```

## ⚠️ Важные замечания

1. **Ollama** должен быть запущен на `http://localhost:11434`
2. **Микрофон** требует настройки прав доступа
3. **Git репозиторий** для полного функционала
4. **SQLite база** создается автоматически

## ✅ Проверка работоспособности

```python
# Тест подключения к Ollama
success, message = ai_manager.test_ai_connection()

# Тест микрофона
mic_works = voice_manager.test_microphone()

# Тест Git
git_available = git_manager.check_git_repository()
```

Этапы 7 и 8 успешно реализованы и готовы к интеграции в основное приложение!
