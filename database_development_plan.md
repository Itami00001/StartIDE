# План разработки системы баз данных для START-beta

## 📋 Обзор проекта

Создание продуманной SQL базы данных для хранения всей информации о проектах, с голосовым вводом, интеграцией с Git и разделенным логированием.

## 🎯 Цели

1. **SQL база данных** вместо JSON-файлов
2. **Централизованное хранение** в папке `context/`
3. **Избегание дублирования** проектов
4. **Структурированный контекст** с 4 основными файлами
5. **Пользовательский контроль** над отслеживаемыми файлами
6. **Разделенное логирование** (приложение vs проект)
7. **Git интеграция** для версионирования
8. **Голосовой ввод** для взаимодействия с AI
9. **Обратная связь** для пользователя о статусе операций

## 🏗️ Архитектура новой системы

### Структура папок

```
START-beta/
├── context/                          # Главная папка БД
│   ├── start_beta.sql                # SQL база данных
│   ├── app_logs.txt                 # Логирование приложения (общее)
│   └── projects/                    # Папки проектов (для текстовых файлов)
│       ├── my_project_1/            # Уникальная папка проекта
│       │   ├── tech_stack.txt       # 1. Технологии + версии
│       │   ├── code_snippets.txt    # 2. Отрывки кодов
│       │   ├── git_context.txt      # 3. Git информация
│       │   └── chat_context.txt     # 4. История запросов/ответов
│       └── another_project/
│           ├── tech_stack.txt
│           ├── code_snippets.txt
│           ├── git_context.txt
│           └── chat_context.txt
```

## 🗄️ Структура SQL базы данных (Python встроенная)

### Используем встроенный Python `sqlite3`
- **Не требует установки** - встроен в Python
- **Файл .sql** - для SQL скриптов создания таблиц
- **База данных** - создается автоматически при первом запуске

### Таблица `projects`
```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    path TEXT UNIQUE NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',
    git_enabled BOOLEAN DEFAULT FALSE
);
```

### Таблица `files_tracking`
```sql
CREATE TABLE files_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    file_path TEXT NOT NULL,
    line_ranges TEXT,  -- JSON: ["1-50", "100-150"]
    is_tracking BOOLEAN DEFAULT TRUE,
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
    voice_file_path TEXT,  -- путь к аудио файлу если голосовой
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Таблица `git_commits`
```sql
CREATE TABLE git_commits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    commit_hash TEXT NOT NULL,
    author TEXT NOT NULL,
    message TEXT NOT NULL,
    date TIMESTAMP NOT NULL,
    tags TEXT,  -- JSON: ["v1.0.0", "release"]
    files_changed TEXT  -- JSON: ["main.py", "utils.py"]
);
```

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

## 📁 Детальная структура файлов

### 1. `context/app_logs.txt` (только логирование приложений)
```
[2024-05-06 21:56:00] APP_START: StartIDE запущена
[2024-05-06 21:56:15] APP_START: StartOffice запущена
[2024-05-06 21:56:20] DB_INIT: База данных инициализирована
[2024-05-06 21:56:25] VOICE_INIT: Голосовой ввод инициализирован
[2024-05-06 21:56:30] GIT_CHECK: Проверка Git репозитория
[2024-05-06 21:56:35] ERROR: Ошибка подключения к Ollama
```

### 2. `context/projects/{project_id}/tech_stack.txt` (для AI контекста)
```
=== ТЕХНОЛОГИЧЕСКИЙ СТЕК ===
Проект: My Cool App
Обновлено: 2024-05-06T22:10:00

=== ОСНОВНЫЕ ТЕХНОЛОГИИ ===
Python 3.10
Tkinter
Requests 2.31.0
Ollama API

=== GIT ВЕРСИИ ===
v1.0.0 - 2024-05-06T21:56:00 - Начальная версия
v1.0.1 - 2024-05-06T22:10:00 - Добавлен AI модуль
```

### 3. `context/projects/{project_id}/code_snippets.txt` (для AI контекста)
```
=== ОТРЫВКИ КОДА ===
Проект: My Cool App
Обновлено: 2024-05-06T22:15:00

=== ФАЙЛ: main.py (Папка: src) ===
Строки: 1-50
Отслеживается: Да
--------------------------------------------------
import tkinter as tk
from tkinter import ttk
import sys
import os

class StartIDE:
    def __init__(self):
        self.root = tk.Tk()
        self.setup_ui()

=== ФАЙЛ: ollama_manager.py (Папка: shared) ===
Строки: 1-30, 45-60
Отслеживается: Да
--------------------------------------------------
import requests
import json
from pathlib import Path

class OllamaManager:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.session = requests.Session()
```

### 4. `context/projects/{project_id}/git_context.txt` (для AI контекста)
```
=== GIT КОНТЕКСТ ===
Проект: My Cool App
Ветка: main
Последний коммит: abc123 (2024-05-06T22:10:00)

=== ПОСЛЕДНИЕ КОММИТЫ ===
abc123 - 2024-05-06T22:10:00 - Добавлен AI модуль (Автор: User)
def456 - 2024-05-06T21:56:00 - Начальная версия (Автор: User)

=== ТЕГИ ВЕРСИЙ ===
v1.0.0 -> abc123 - 2024-05-06T22:10:00
v0.9.0 -> def456 - 2024-05-06T21:56:00

=== ИЗМЕНЕННЫЕ ФАЙЛЫ ===
main.py, ollama_manager.py, project_context.py
```

### 5. `context/projects/{project_id}/chat_context.txt` (для AI контекста)
```
=== КОНТЕКСТ ЧАТА ===
Проект: My Cool App
Всего сообщений: 15

=== ИСТОРИЯ ДИАЛОГА ===
[2024-05-06 21:56:30] StartIDE → AI: Как оптимизировать этот код?
[2024-05-06 21:56:35] AI → StartIDE: Рекомендую использовать кэширование...
[2024-05-06 21:56:40] StartOffice → AI: [ГОЛОС] Покажи структуру проекта
[2024-05-06 21:56:45] AI → StartOffice: Проект содержит 3 основных модуля...
```

## 🔧 Компоненты для реализации

### 1. `shared/database_manager.py` (Python sqlite3 + текстовые файлы)
```python
import sqlite3
import json
from pathlib import Path
from datetime import datetime

class DatabaseManager:
    def __init__(self, context_path: str):
        self.context_path = Path(context_path)
        self.db_path = self.context_path / "start_beta.db"  # База данных
        self.sql_file = self.context_path / "start_beta.sql"  # SQL скрипты
        self.app_logs_file = self.context_path / "app_logs.txt"
        self.conn = None
        
    def init_database(self):
        """Инициализация sqlite3 и структуры папок"""
        
    def get_or_create_project(self, project_path: str) -> int:
        """Получить ID проекта или создать новый"""
        
    def update_project_context_files(self, project_id: int):
        """Обновление текстовых файлов для AI контекста"""
        
    def add_chat_message(self, project_id: int, sender: str, message_type: str, content: str, voice_file: str = None):
        """Добавление сообщения в чат (в БД и текстовый файл)"""
```

### 2. `shared/git_manager.py` (Git интеграция)
```python
import subprocess
import json
from pathlib import Path

class GitManager:
    def __init__(self, project_path: str, db_manager: DatabaseManager):
        self.project_path = Path(project_path)
        self.db_manager = db_manager
        self.is_git_repo = False
        
    def check_git_repository(self) -> bool:
        """Проверка наличия Git репозитория"""
        
    def get_commits(self, limit: int = 10) -> List[Dict]:
        """Получение последних коммитов"""
        
    def get_tags(self) -> List[str]:
        """Получение тегов версий"""
        
    def get_current_branch(self) -> str:
        """Получение текущей ветки"""
        
    def update_git_context(self, project_id: int):
        """Обновление git_context.txt для AI"""
```

### 3. `StartIDE/voice_manager.py` (Голосовой ввод для AI чата)
```python
import speech_recognition as sr
import tempfile
import threading
from pathlib import Path

class VoiceManager:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.is_recording = False
        
    def init_voice_input(self) -> bool:
        """Инициализация микрофона для AI чата"""
        
    def start_recording(self, callback_func):
        """Начать запись голоса для AI"""
        
    def stop_recording(self) -> str:
        """Остановить запись и распознать речь для AI"""
        
    def text_to_speech(self, text: str, output_file: str = None):
        """Преобразование AI ответа в речь"""
```

### 4. `StartOffice/voice_input_manager.py` (Голосовой ввод для документов)
```python
import speech_recognition as sr
import tempfile
import threading
from pathlib import Path

class VoiceInputManager:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.is_recording = False
        
    def init_voice_input(self) -> bool:
        """Инициализация микрофона для ввода текста в документ"""
        
    def start_document_recording(self, text_widget):
        """Начать запись голоса для вставки в документ"""
        
    def stop_document_recording(self) -> str:
        """Остановить запись и вставить распознанный текст в документ"""
```

### 5. `shared/project_tracker.py` (Улучшенный)
```python
class ProjectTracker:
    def __init__(self, project_path: str, db_manager: DatabaseManager):
        self.project_path = project_path
        self.db_manager = db_manager
        self.project_id = None
        self.git_manager = GitManager(project_path, db_manager)
        
    def start_tracking(self):
        """Начать отслеживание проекта с Git"""
        
    def track_file(self, file_path: str, line_ranges: List[str]):
        """Добавить файл для отслеживания в БД"""
        
    def detect_technologies(self) -> List[Dict]:
        """Автоопределение технологий проекта"""
        
    def update_all_context_files(self):
        """Обновление всех 4 текстовых файлов для AI"""
```

### 6. `shared/app_logger.py` (Разделенное логирование)
```python
class AppLogger:
    def __init__(self, context_path: str):
        self.app_logs_file = Path(context_path) / "app_logs.txt"
        
    def log_app_start(self, app_name: str):
        """Лог запуска приложения (только в app_logs.txt)"""
        
    def log_project_open(self, project_path: str, project_id: int):
        """Лог открытия проекта (только в app_logs.txt)"""
        
    def log_voice_action(self, action: str, details: str = ""):
        """Лог голосовых действий (только в app_logs.txt)"""
        
    def log_git_action(self, action: str, details: str = ""):
        """Лог Git действий (только в app_logs.txt)"""
        
    def log_error(self, error: str, context: str = ""):
        """Лог ошибок (только в app_logs.txt)"""
```

## 🎨 UI изменения в StartIDE

### Новая панель "Отслеживание файлов"
```
┌─────────────────────────────────────┐
│ 📁 Отслеживание файлов              │
├─────────────────────────────────────┤
│ ☑ main.py (строки: 1-50)           │
│ ☑ ollama_manager.py (строки: 1-30) │
│ ☐ utils.py (не выбрано)             │
│                                     │
│ [+ Добавить файл]  [Настройки]      │
├─────────────────────────────────────┤
│ 🎤 Голосовой ввод                   │
│ [🎙️ Начать запись] [⏹️ Остановить] │
└─────────────────────────────────────┘
```

### Статус-бар с индикаторами
```
[✓] Проект загружен    [🔄] AI обрабатывает...    [📝] 3 файла отслеживаются    [🎤] Голос готов
```

## 🎨 UI изменения в StartOffice

### Улучшенная информация о проекте
```
┌─────────────────────────────────────┐
│ 📊 Обзор проекта                    │
├─────────────────────────────────────┤
│ Технологии: Python, Tkinter        │
│ Git: main (v1.0.0)                 │
│ Отслеживается файлов: 3            │
│ Последнее обновление: 5 мин назад   │
│                                     │
│ [📁 Управление файлами] [🤖 AI чат] │
│ [🎤 Голосовой ввод] [🌿 Git инфо]   │
└─────────────────────────────────────┘
```

## 🔄 Интеграция с существующим кодом

### Модификация StartIDE/main.py
```python
# Импорт голосового менеджера
from StartIDE.voice_manager import VoiceManager

class StartIDE:
    def __init__(self):
        # ... существующий код ...
        self.db_manager = DatabaseManager("context")
        self.app_logger = AppLogger("context")
        self.project_tracker = None
        self.voice_manager = VoiceManager()  # Голосовой ввод для AI чата
        
    def open_project(self, project_path: str):
        self.app_logger.log_project_open(project_path)
        self.project_tracker = ProjectTracker(project_path, self.db_manager)
        self.project_tracker.start_tracking()
        
    def setup_file_tracking_ui(self):
        """Создание панели отслеживания файлов"""
        
    def setup_voice_ui(self):
        """Создание голосового ввода для AI чата"""
        self.voice_manager.init_voice_input()
```

### Модификация StartOffice/main.py
```python
# Импорт голосового менеджера для документов
from StartOffice.voice_input_manager import VoiceInputManager

class StartOffice:
    def __init__(self):
        # ... существующий код ...
        self.db_manager = DatabaseManager("context")
        self.app_logger = AppLogger("context")
        self.voice_input_manager = VoiceInputManager()  # Голосовой ввод для документов
        
    def load_project_details(self, project_id: int):
        """Загрузка деталей проекта из SQLite"""
        
    def setup_git_info_ui(self):
        """Создание Git информационной панели"""
        
    def setup_voice_input_ui(self):
        """Создание голосового ввода для документов"""
        self.voice_input_manager.init_voice_input()
```

## 📋 План реализации

### Этап 1: Python sqlite3 база данных (1-2 дня)
- [ ] Создать `shared/database_manager.py` с Python sqlite3
- [ ] Реализовать все SQL таблицы (не требует установки SQLite)
- [ ] Создать структуру папок context/
- [ ] Создать start_beta.sql файл со скриптами
- [ ] Миграция существующих JSON данных

### Этап 2: Git интеграция (1 день)
- [ ] Создать `shared/git_manager.py`
- [ ] Реализовать проверку Git репозитория
- [ ] Получение коммитов, тегов, веток
- [ ] Обновление git_context.txt

### Этап 3: Голосовой ввод StartIDE (1-2 дня)
- [ ] Создать `StartIDE/voice_manager.py` для AI чата
- [ ] Инициализация микрофона и распознавания
- [ ] Интеграция с UI (кнопки записи для AI)
- [ ] Text-to-speech для AI ответов

### Этап 4: Голосовой ввод StartOffice (1 день)
- [ ] Создать `StartOffice/voice_input_manager.py` для документов
- [ ] Инициализация микрофона для ввода текста
- [ ] Интеграция с текстовыми виджетами
- [ ] Вставка распознанного текста в документы

### Этап 5: Разделенное логирование (1 день)
- [ ] Создать `shared/app_logger.py`
- [ ] Разделить логирование приложений и проектов
- [ ] Только app_logs.txt для системных логов
- [ ] Отфильтрованные данные для AI

### Этап 6: Управление проектами (1 день)
- [ ] Реализовать `get_or_create_project` с sqlite3
- [ ] Избегание дублирования проектов
- [ ] Интеграция с StartIDE и StartOffice
- [ ] Обновление всех 4 контекстных файлов

### Этап 7: Отслеживание файлов (1-2 дня)
- [ ] Обновить `shared/project_tracker.py`
- [ ] UI для выбора файлов и строк
- [ ] Сохранение в sqlite3 и текстовые файлы
- [ ] Автообновление сниппетов

### Этап 8: Технологический стек (1 день)
- [ ] Автоопределение технологий из файлов
- [ ] Git анализ зависимостей
- [ ] Ручное редактирование стека
- [ ] Обновление tech_stack.txt

### Этап 9: Чат и AI интеграция (1 день)
- [ ] Миграция чата в sqlite3
- [ ] Поддержка голосовых сообщений в StartIDE
- [ ] Обновление chat_context.txt
- [ ] Интеграция с Ollama

### Этап 10: UI улучшения (1-2 дня)
- [ ] Панель отслеживания в StartIDE
- [ ] Голосовые кнопки в StartIDE (AI чат)
- [ ] Голосовые кнопки в StartOffice (документы)
- [ ] Git информация в StartOffice
- [ ] Статус-бары и индикаторы

### Этап 11: Тестирование и миграция (1 день)
- [ ] Тестирование всех компонентов
- [ ] Миграция существующих проектов
- [ ] Обработка ошибок и исключений
- [ ] Документация и инструкции

## 📦 Новые зависимости

### requirements.txt дополнения:
```
speechrecognition>=3.10.0
pyaudio>=0.2.11
pyttsx3>=2.90
gitpython>=3.1.0
```

## ⚠️ Важные моменты

### Разделение данных
- **app_logs.txt** - только системные логи (не для AI)
- **Контекстные файлы** - только отфильтрованные данные для AI
- **SQLite** - основное хранилище, текстовые файлы - для AI

### Безопасность и производительность
- Асинхронная запись в БД
- Кэширование Git данных
- Проверка прав доступа к микрофону
- Резервное копирование БД

### Обратная связь
- Индикаторы записи голоса
- Прогресс-бары для Git операций
- Уведомления об ошибках
- Статус подключения к Ollama

## 🎯 Результат

После реализации получим:
- ✅ SQLite база данных вместо JSON
- ✅ Git интеграция с версионированием
- ✅ Голосовой ввод для AI взаимодействия
- ✅ Разделенное логирование (приложение vs проект)
- ✅ Централизованная БД в папке `context/`
- ✅ Уникальные папки для каждого проекта
- ✅ Структурированный контекст (4 файла)
- ✅ Пользовательский контроль над отслеживанием
- ✅ Понятная обратная связь для пользователя

## 📝 Следующие шаги

1. Оценить и поправить план
2. Начать реализацию с Этапа 1
3. Постепенно интегрировать с существующим кодом
4. Тестировать каждый этап
5. Мигрировать существующие проекты

Готов к началу работы после твоей оценки и поправок!
