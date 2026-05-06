import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

class DatabaseManager:
    def __init__(self, context_path: str = "context"):
        self.context_path = Path(context_path)
        self.db_path = self.context_path / "start_beta.db"
        self.sql_file = self.context_path / "start_beta.sql"
        self.app_logs_file = self.context_path / "app_logs.txt"
        self.projects_dir = self.context_path / "projects"
        self.conn = None
        self.logger = logging.getLogger(__name__)
        
        # Создаем структуру папок
        self.context_path.mkdir(parents=True, exist_ok=True)
        (self.context_path / "projects").mkdir(parents=True, exist_ok=True)
        
        # Инициализируем базу данных
        self.init_database()
        
        # Выполняем миграции
        self.run_migrations()
    
    def _create_directory_structure(self):
        """Создание структуры папок"""
        try:
            self.context_path.mkdir(exist_ok=True)
            self.projects_dir.mkdir(exist_ok=True)
            self.logger.info("Структура папок создана успешно")
        except Exception as e:
            self.logger.error(f"Ошибка создания структуры папок: {e}")
            raise
    
    def init_database(self):
        """Инициализация sqlite3 базы данных"""
        try:
            # Подключаемся к базе данных
            
            # Если база данных не существует, создаем из SQL файла
            if not self.db_path.exists():
                self.logger.info("Создание базы данных из SQL файла")
                self._create_from_sql()
            else:
                self.logger.info("База данных уже существует")
            
            self.logger.info("База данных успешно инициализирована")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации базы данных: {e}")
            raise
    
    def run_migrations(self):
        """Выполнение миграций базы данных"""
        try:
            from shared.database_migration import DatabaseMigration
            
            migration = DatabaseMigration(str(self.context_path))
            if migration.check_and_migrate():
                self.logger.info("Миграции базы данных выполнены успешно")
            else:
                self.logger.warning("Ошибка при выполнении миграций")
                
        except Exception as e:
            self.logger.error(f"Ошибка выполнения миграций: {e}")
            # Не прерываем работу, если миграции не удались
    
    def _create_tables_manually(self):
        """Создание таблиц вручную (если SQL файл отсутствует)"""
        tables_sql = [
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                path TEXT UNIQUE NOT NULL,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                git_enabled BOOLEAN DEFAULT FALSE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS files_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER REFERENCES projects(id),
                file_path TEXT NOT NULL,
                line_ranges TEXT,
                is_tracking BOOLEAN DEFAULT TRUE,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER REFERENCES projects(id),
                sender TEXT NOT NULL,
                message_type TEXT NOT NULL,
                content TEXT NOT NULL,
                voice_file_path TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS git_commits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER REFERENCES projects(id),
                commit_hash TEXT NOT NULL,
                author TEXT NOT NULL,
                message TEXT NOT NULL,
                date TIMESTAMP NOT NULL,
                tags TEXT,
                files_changed TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS tech_stack (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER REFERENCES projects(id),
                technology TEXT NOT NULL,
                version TEXT,
                detected_by TEXT,
                confidence REAL DEFAULT 1.0,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        for sql in tables_sql:
            self.conn.execute(sql)
        
        # Создаем индексы
        indexes_sql = [
            "CREATE INDEX IF NOT EXISTS idx_projects_path ON projects(path)",
            "CREATE INDEX IF NOT EXISTS idx_files_tracking_project_id ON files_tracking(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_chat_messages_project_id ON chat_messages(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_git_commits_project_id ON git_commits(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_tech_stack_project_id ON tech_stack(project_id)"
        ]
        
        for sql in indexes_sql:
            self.conn.execute(sql)
        
        self.conn.commit()
    
    def get_or_create_project(self, project_path: str) -> int:
        """Получить ID проекта или создать новый"""
        try:
            project_path = str(Path(project_path).resolve())
            project_name = Path(project_path).name
            
            # Проверяем существующий проект
            cursor = self.conn.execute(
                "SELECT id FROM projects WHERE path = ?", 
                (project_path,)
            )
            result = cursor.fetchone()
            
            if result:
                # Обновляем время последнего доступа
                project_id = result['id']
                self.conn.execute(
                    "UPDATE projects SET last_accessed = CURRENT_TIMESTAMP WHERE id = ?",
                    (project_id,)
                )
                self.conn.commit()
                self.logger.info(f"Проект найден: {project_name} (ID: {project_id})")
                return project_id
            else:
                # Создаем новый проект
                cursor = self.conn.execute(
                    """
                    INSERT INTO projects (name, path, created, last_accessed)
                    VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (project_name, project_path)
                )
                project_id = cursor.lastrowid
                self.conn.commit()
                
                # Создаем папку для проекта
                project_folder = self.projects_dir / f"project_{project_id}"
                project_folder.mkdir(exist_ok=True)
                
                self.logger.info(f"Создан новый проект: {project_name} (ID: {project_id})")
                return project_id
                
        except Exception as e:
            self.logger.error(f"Ошибка получения/создания проекта: {e}")
            raise
    
    def get_project_by_id(self, project_id: int) -> Optional[Dict]:
        """Получить информацию о проекте по ID"""
        try:
            cursor = self.conn.execute(
                "SELECT * FROM projects WHERE id = ?", 
                (project_id,)
            )
            result = cursor.fetchone()
            return dict(result) if result else None
        except Exception as e:
            self.logger.error(f"Ошибка получения проекта: {e}")
            return None
    
    def get_all_projects(self) -> List[Dict]:
        """Получить все проекты"""
        try:
            cursor = self.conn.execute(
                "SELECT * FROM projects ORDER BY last_accessed DESC"
            )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self.logger.error(f"Ошибка получения всех проектов: {e}")
            return []
    
    def update_project_context_files(self, project_id: int):
        """Обновление текстовых файлов для AI контекста"""
        try:
            project_info = self.get_project_by_id(project_id)
            if not project_info:
                return
            
            project_folder = self.projects_dir / f"project_{project_id}"
            
            # Обновляем tech_stack.txt
            self._update_tech_stack_file(project_id, project_folder)
            
            # Обновляем code_snippets.txt
            self._update_code_snippets_file(project_id, project_folder)
            
            # Обновляем chat_context.txt
            self._update_chat_context_file(project_id, project_folder)
            
            self.logger.info(f"Контекстные файлы обновлены для проекта {project_id}")
            
        except Exception as e:
            self.logger.error(f"Ошибка обновления контекстных файлов: {e}")
    
    def _update_tech_stack_file(self, project_id: int, project_folder: Path):
        """Обновление файла технологического стека"""
        try:
            cursor = self.conn.execute(
                "SELECT technology, version, detected_by FROM tech_stack WHERE project_id = ?",
                (project_id,)
            )
            tech_items = cursor.fetchall()
            
            content = []
            content.append(f"=== ТЕХНОЛОГИЧЕСКИЙ СТЕК ===")
            content.append(f"Проект: {project_folder.name}")
            content.append(f"Обновлено: {datetime.now().isoformat()}")
            content.append("")
            
            if tech_items:
                content.append("=== ОСНОВНЫЕ ТЕХНОЛОГИИ ===")
                for item in tech_items:
                    version = f" {item['version']}" if item['version'] else ""
                    detected = f" ({item['detected_by']})" if item['detected_by'] else ""
                    content.append(f"{item['technology']}{version}{detected}")
                content.append("")
            else:
                content.append("Технологии не определены")
                content.append("")
            
            with open(project_folder / "tech_stack.txt", 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
                
        except Exception as e:
            self.logger.error(f"Ошибка обновления tech_stack.txt: {e}")
    
    def _update_code_snippets_file(self, project_id: int, project_folder: Path):
        """Обновление файла отрывков кода"""
        try:
            cursor = self.conn.execute(
                """
                SELECT file_path, line_ranges, is_tracking 
                FROM files_tracking 
                WHERE project_id = ? AND is_tracking = TRUE
                """,
                (project_id,)
            )
            tracked_files = cursor.fetchall()
            
            content = []
            content.append(f"=== ОТРЫВКИ КОДА ===")
            content.append(f"Проект: {project_folder.name}")
            content.append(f"Обновлено: {datetime.now().isoformat()}")
            content.append("")
            
            if tracked_files:
                for file_info in tracked_files:
                    file_path = Path(file_info['file_path'])
                    line_ranges = json.loads(file_info['line_ranges']) if file_info['line_ranges'] else []
                    
                    content.append(f"=== ФАЙЛ: {file_path.name} (Папка: {file_path.parent.name}) ===")
                    content.append(f"Строки: {', '.join(line_ranges) if line_ranges else 'Все'}")
                    content.append(f"Отслеживается: {'Да' if file_info['is_tracking'] else 'Нет'}")
                    content.append("-" * 50)
                    
                    # Читаем содержимое файла
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            file_content = f.read()
                        
                        # Извлекаем нужные строки
                        if line_ranges:
                            lines = file_content.split('\n')
                            for range_str in line_ranges:
                                if '-' in range_str:
                                    start, end = map(int, range_str.split('-'))
                                    selected_lines = lines[start-1:end]
                                    content.append('\n'.join(selected_lines))
                        else:
                            # Ограничиваем размер файла
                            if len(file_content) > 2000:
                                content.append(file_content[:2000] + "\n... (обрезано)")
                            else:
                                content.append(file_content)
                        
                        content.append("")
                        
                    except Exception as e:
                        content.append(f"Ошибка чтения файла: {e}")
                        content.append("")
            else:
                content.append("Файлы не отслеживаются")
                content.append("")
            
            with open(project_folder / "code_snippets.txt", 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
                
        except Exception as e:
            self.logger.error(f"Ошибка обновления code_snippets.txt: {e}")
    
    def _update_chat_context_file(self, project_id: int, project_folder: Path):
        """Обновление файла контекста чата"""
        try:
            cursor = self.conn.execute(
                """
                SELECT sender, message_type, content, timestamp 
                FROM chat_messages 
                WHERE project_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 20
                """,
                (project_id,)
            )
            messages = cursor.fetchall()
            
            content = []
            content.append(f"=== КОНТЕКСТ ЧАТА ===")
            content.append(f"Проект: {project_folder.name}")
            content.append(f"Всего сообщений: {len(messages)}")
            content.append("")
            
            content.append("=== ИСТОРИЯ ДИАЛОГА ===")
            for msg in reversed(messages):  # В хронологическом порядке
                timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                sender = msg['sender']
                msg_type = msg['message_type']
                msg_content = msg['content']
                
                if msg_type == 'voice':
                    msg_content = f"[ГОЛОС] {msg_content}"
                
                content.append(f"[{timestamp}] {sender} → AI: {msg_content}")
            
            with open(project_folder / "chat_context.txt", 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))
                
        except Exception as e:
            self.logger.error(f"Ошибка обновления chat_context.txt: {e}")
    
    def add_chat_message(self, project_id: int, sender: str, message_type: str, content: str, voice_file: str = None):
        """Добавление сообщения в чат (в БД и текстовый файл)"""
        try:
            cursor = self.conn.execute(
                """
                INSERT INTO chat_messages (project_id, sender, message_type, content, voice_file_path)
                VALUES (?, ?, ?, ?, ?)
                """,
                (project_id, sender, message_type, content, voice_file)
            )
            message_id = cursor.lastrowid
            self.conn.commit()
            
            # Обновляем контекстный файл
            project_folder = self.projects_dir / f"project_{project_id}"
            self._update_chat_context_file(project_id, project_folder)
            
            self.logger.info(f"Сообщение добавлено в чат (ID: {message_id})")
            return message_id
            
        except Exception as e:
            self.logger.error(f"Ошибка добавления сообщения в чат: {e}")
            raise
    
    def close(self):
        """Закрытие соединения с базой данных"""
        if self.conn:
            self.conn.close()
            self.logger.info("Соединение с базой данных закрыто")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
