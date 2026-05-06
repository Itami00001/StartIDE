-- SQL скрипты для создания таблиц START-beta
-- База данных: context/start_beta.db

-- Таблица проектов
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    path TEXT UNIQUE NOT NULL,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',
    git_enabled BOOLEAN DEFAULT FALSE
);

-- Таблица отслеживания файлов
CREATE TABLE IF NOT EXISTS files_tracking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    file_path TEXT NOT NULL,
    line_ranges TEXT,  -- JSON: ["1-50", "100-150"]
    is_tracking BOOLEAN DEFAULT TRUE,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица сообщений чата
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    sender TEXT NOT NULL,  -- "StartIDE", "StartOffice", "AI"
    message_type TEXT NOT NULL,  -- "text", "voice", "file_analysis"
    content TEXT NOT NULL,
    voice_file_path TEXT,  -- путь к аудио файлу если голосовой
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица Git коммитов
CREATE TABLE IF NOT EXISTS git_commits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    commit_hash TEXT NOT NULL,
    author TEXT NOT NULL,
    message TEXT NOT NULL,
    date TIMESTAMP NOT NULL,
    tags TEXT,  -- JSON: ["v1.0.0", "release"]
    files_changed TEXT  -- JSON: ["main.py", "utils.py"]
);

-- Таблица технологического стека
CREATE TABLE IF NOT EXISTS tech_stack (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    technology TEXT NOT NULL,
    version TEXT,
    detected_by TEXT,  -- "auto", "manual", "git"
    confidence REAL DEFAULT 1.0,
    created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для оптимизации
CREATE INDEX IF NOT EXISTS idx_projects_path ON projects(path);
CREATE INDEX IF NOT EXISTS idx_files_tracking_project_id ON files_tracking(project_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_project_id ON chat_messages(project_id);
CREATE INDEX IF NOT EXISTS idx_git_commits_project_id ON git_commits(project_id);
CREATE INDEX IF NOT EXISTS idx_tech_stack_project_id ON tech_stack(project_id);
