# START-beta

Две связанные AI-утилиты для разработки:

- **StartIDE** — редактор кода с AI-ассистентом
- **StartOffice** — офисный менеджер проектов с AI

Оба приложения используют локальную нейросеть через **Ollama** и общую **SQLite**-базу данных.

---

## ⚡ Быстрый запуск

### 1. Установить зависимости

```
pip install -r requirements.txt
```

### 2. Установить и запустить Ollama

Скачай с https://ollama.com, затем:

```
ollama serve
ollama pull llama3.1
```

> Ollama должен быть запущен на `http://localhost:11434`

### 3. Запустить приложения

Из папки `START-beta/`:

**StartIDE:**
```
python StartIDE/main.py
```

**Start Office:**
```
python StartOffice/main.py
```

---

## Горячие клавиши (StartIDE)

| Клавиша | Действие |
|---|---|
| `Ctrl+S` | Сохранить файл |
| `Ctrl+Z` | Отменить |
| `Ctrl+Y` | Повторить |
| `Ctrl+A` | Выделить всё |
| `Ctrl+C` | Копировать |
| `Ctrl+V` | Вставить |
| `Win+M` / `Ctrl+M` | Включить/выключить микрофон |
| `Ctrl+Q` | Выйти |

---

## Возможности

### StartIDE
- Редактор кода с undo/redo
- Проводник файлов и папок
- AI-чат с историей диалога (SQLite)
- Анализ технологического стека проекта
- Git-интеграция (статус, ветка, коммиты)
- Голосовой ввод (требует `speechrecognition`, `pyaudio`)

### Start Office
- Список проектов из общей базы данных
- AI-ассистент для вопросов о `.txt` файлах и контексте
- Редактор документов с AI-помощью
- Общий чат с историей
- Просмотр структуры проекта

---

## Структура проекта

```
START-beta/
├── StartIDE/               # Редактор кода
│   └── main.py
├── StartOffice/            # Офисный менеджер
│   └── main.py
├── shared/                 # Общие модули
│   ├── database_manager.py
│   ├── ollama_manager.py
│   ├── chat_manager.py
│   ├── tech_stack_detector.py
│   └── ...
├── context/                # База данных и логи (создаётся автоматически)
│   └── start_beta.db
└── requirements.txt
```

---

## Требования

- Python 3.9+
- Ollama (локально)
- Tkinter (входит в стандартную Python-установку)

### Зависимости (`requirements.txt`):
```
requests
speechrecognition
pyttsx3
pyaudio
gitpython
psutil
packaging
```

> `pyaudio` на Windows может потребовать [предсобранного wheel](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio) или `pipwin install pyaudio`

---

## Возможные проблемы

**Ollama не отвечает** — запустите `ollama serve` и убедитесь что порт 11434 свободен.

**Ошибка `pyaudio`** — голосовой ввод опционален, приложение запустится и без него.

**Проекты не видны в Start Office** — откройте проект через `Файл → Открыть проект` в любом из приложений; он появится в списке.
