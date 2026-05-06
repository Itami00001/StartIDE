import sqlite3
import logging
from pathlib import Path

class DatabaseMigration:
    """Миграция базы данных START-beta"""
    
    def __init__(self, context_path: str = "context"):
        self.context_path = Path(context_path)
        self.db_path = self.context_path / "start_beta.db"
        self.logger = logging.getLogger(__name__)
    
    def migrate_to_v2(self):
        """Миграция к версии 2 - добавление недостающих колонок"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Проверяем текущую версию
                cursor.execute("PRAGMA table_info(projects)")
                columns = [row[1] for row in cursor.fetchall()]
                
                migrations_needed = []
                
                # Проверяем и добавляем недостающие колонки в projects
                if 'description' not in columns:
                    cursor.execute("ALTER TABLE projects ADD COLUMN description TEXT DEFAULT ''")
                    migrations_needed.append("projects.description")
                
                if 'tech_stack' not in columns:
                    cursor.execute("ALTER TABLE projects ADD COLUMN tech_stack TEXT DEFAULT '[]'")
                    migrations_needed.append("projects.tech_stack")
                
                if 'updated_at' not in columns:
                    cursor.execute("ALTER TABLE projects ADD COLUMN updated_at TIMESTAMP")
                    migrations_needed.append("projects.updated_at")
                
                # Проверяем files_tracking
                cursor.execute("PRAGMA table_info(files_tracking)")
                file_columns = [row[1] for row in cursor.fetchall()]
                
                if 'description' not in file_columns:
                    cursor.execute("ALTER TABLE files_tracking ADD COLUMN description TEXT DEFAULT ''")
                    migrations_needed.append("files_tracking.description")
                
                if 'tags' not in file_columns:
                    cursor.execute("ALTER TABLE files_tracking ADD COLUMN tags TEXT DEFAULT '[]'")
                    migrations_needed.append("files_tracking.tags")
                
                if 'file_hash' not in file_columns:
                    cursor.execute("ALTER TABLE files_tracking ADD COLUMN file_hash TEXT")
                    migrations_needed.append("files_tracking.file_hash")
                
                if 'updated_at' not in file_columns:
                    cursor.execute("ALTER TABLE files_tracking ADD COLUMN updated_at TIMESTAMP")
                    migrations_needed.append("files_tracking.updated_at")
                
                # Обновляем существующие записи
                if migrations_needed:
                    # Обновляем updated_at для существующих проектов
                    cursor.execute("UPDATE projects SET updated_at = created WHERE updated_at IS NULL")
                    cursor.execute("UPDATE files_tracking SET updated_at = created WHERE updated_at IS NULL")
                    
                    conn.commit()
                    self.logger.info(f"Выполнены миграции: {migrations_needed}")
                else:
                    self.logger.info("Миграции не требуются")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Ошибка миграции: {e}")
            return False
    
    def check_and_migrate(self):
        """Проверить и выполнить миграции при необходимости"""
        if not self.db_path.exists():
            self.logger.info("База данных не существует, миграции не требуются")
            return True
        
        try:
            # Проверяем версию схемы
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(projects)")
                columns = [row[1] for row in cursor.fetchall()]
                
                # Если нет нужных колонок, выполняем миграцию
                if 'updated_at' not in columns:
                    self.logger.info("Требуется миграция базы данных")
                    return self.migrate_to_v2()
                else:
                    self.logger.info("База данных актуальна")
                    return True
                    
        except Exception as e:
            self.logger.error(f"Ошибка проверки миграций: {e}")
            return False
    
    def get_schema_version(self):
        """Получить версию схемы"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(projects)")
                columns = [row[1] for row in cursor.fetchall()]
                
                # Определяем версию по наличию ключевых колонок
                if 'updated_at' in columns and 'tech_stack' in columns:
                    return 2
                else:
                    return 1
                    
        except Exception:
            return 0
