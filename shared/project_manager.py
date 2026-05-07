import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
import os

class ProjectManager:
    """Управление проектами в системе START-beta"""

    def __init__(self, context_path: str = "context"):
        self.context_path = Path(context_path)
        self.db_path = self.context_path / "start_beta.db"
        self.logger = logging.getLogger(__name__)

        # Убедимся что база данных существует
        self._ensure_database()

    def _ensure_database(self):
        """Проверка и создание базы данных при необходимости"""
        if not self.db_path.exists():
            from shared.database_manager import DatabaseManager
            db_manager = DatabaseManager(str(self.context_path))
            db_manager.close()

    def create_project(self, name: str, path: str, description: str = "", tech_stack: List[str] = None) -> Optional[int]:
        """Создание нового проекта"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Проверяем что путь существует
                project_path = Path(path)
                if not project_path.exists():
                    raise ValueError(f"Путь {path} не существует")

                # Проверяем что проект еще не существует
                cursor.execute("SELECT id FROM projects WHERE path = ?", (path,))
                if cursor.fetchone():
                    raise ValueError(f"Проект по пути {path} уже существует")

                # Создаем проект
                now = datetime.now().isoformat()
                cursor.execute("""
                    INSERT INTO projects (name, path, description, tech_stack, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, path, description, json.dumps(tech_stack or []), now))

                project_id = cursor.lastrowid
                conn.commit()

                # Создаем папку проекта в context
                project_folder = self.context_path / "projects" / f"project_{project_id}"
                project_folder.mkdir(parents=True, exist_ok=True)

                # Создаем контекстные файлы
                self._create_project_context_files(project_id, name, path, tech_stack or [])

                self.logger.info(f"Проект '{name}' создан с ID: {project_id}")
                return project_id

        except Exception as e:
            self.logger.error(f"Ошибка создания проекта: {e}")
            raise

    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о проекте"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM projects WHERE id = ?
                """, (project_id,))

                row = cursor.fetchone()
                if row:
                    project = dict(row)
                    project['tech_stack'] = json.loads(project['tech_stack'])
                    return project

                return None

        except Exception as e:
            self.logger.error(f"Ошибка получения проекта {project_id}: {e}")
            return None

    def get_all_projects(self) -> List[Dict[str, Any]]:
        """Получение всех проектов"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM projects ORDER BY updated_at DESC
                """)

                projects = []
                for row in cursor.fetchall():
                    project = dict(row)
                    project['tech_stack'] = json.loads(project['tech_stack'])
                    projects.append(project)

                return projects

        except Exception as e:
            self.logger.error(f"Ошибка получения проектов: {e}")
            return []

    def update_project(self, project_id: int, name: str = None, description: str = None,
                      tech_stack: List[str] = None) -> bool:
        """Обновление метаданных проекта"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Получаем текущие данные
                cursor.execute("SELECT name, description, tech_stack FROM projects WHERE id = ?", (project_id,))
                current = cursor.fetchone()
                if not current:
                    return False

                updates = []
                params = []

                if name is not None and name != current[0]:
                    updates.append("name = ?")
                    params.append(name)

                if description is not None and description != current[1]:
                    updates.append("description = ?")
                    params.append(description)

                if tech_stack is not None and tech_stack != json.loads(current[2]):
                    updates.append("tech_stack = ?")
                    params.append(json.dumps(tech_stack))

                if updates:
                    updates.append("updated_at = ?")
                    params.append(datetime.now().isoformat())
                    params.append(project_id)

                    cursor.execute(f"""
                        UPDATE projects SET {', '.join(updates)} WHERE id = ?
                    """, params)

                    conn.commit()

                    # Обновляем контекстные файлы
                    project = self.get_project(project_id)
                    if project:
                        self._update_project_context_files(project_id, project)

                    self.logger.info(f"Проект {project_id} обновлен")
                    return True

                return False

        except Exception as e:
            self.logger.error(f"Ошибка обновления проекта {project_id}: {e}")
            return False

    def delete_project(self, project_id: int) -> bool:
        """Удаление проекта"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Удаляем связанные записи
                cursor.execute("DELETE FROM files_tracking WHERE project_id = ?", (project_id,))
                cursor.execute("DELETE FROM chat_messages WHERE project_id = ?", (project_id,))
                cursor.execute("DELETE FROM git_commits WHERE project_id = ?", (project_id,))

                # Удаляем проект
                cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))

                conn.commit()

                # Удаляем папку с контекстными файлами
                project_folder = self.context_path / "projects" / f"project_{project_id}"
                if project_folder.exists():
                    import shutil
                    shutil.rmtree(project_folder)

                self.logger.info(f"Проект {project_id} удален")
                return True

        except Exception as e:
            self.logger.error(f"Ошибка удаления проекта {project_id}: {e}")
            return False

    def rename_project(self, project_id: int, new_name: str) -> bool:
        """Переименование проекта"""
        return self.update_project(project_id, name=new_name)

    def get_project_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        """Получение проекта по пути"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM projects WHERE path = ?
                """, (path,))

                row = cursor.fetchone()
                if row:
                    project = dict(row)
                    project['tech_stack'] = json.loads(project['tech_stack'])
                    return project

                return None

        except Exception as e:
            self.logger.error(f"Ошибка получения проекта по пути {path}: {e}")
            return None

    def search_projects(self, query: str) -> List[Dict[str, Any]]:
        """Поиск проектов по имени или описанию"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                search_query = f"%{query}%"
                cursor.execute("""
                    SELECT * FROM projects
                    WHERE name LIKE ? OR description LIKE ?
                    ORDER BY updated_at DESC
                """, (search_query, search_query))

                projects = []
                for row in cursor.fetchall():
                    project = dict(row)
                    project['tech_stack'] = json.loads(project['tech_stack'])
                    projects.append(project)

                return projects

        except Exception as e:
            self.logger.error(f"Ошибка поиска проектов: {e}")
            return []

    def get_project_stats(self, project_id: int) -> Dict[str, Any]:
        """Получение статистики проекта"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                stats = {}

                # Количество отслеживаемых файлов
                cursor.execute("SELECT COUNT(*) FROM files_tracking WHERE project_id = ?", (project_id,))
                stats['tracked_files'] = cursor.fetchone()[0]

                # Количество сообщений в чате
                cursor.execute("SELECT COUNT(*) FROM chat_messages WHERE project_id = ?", (project_id,))
                stats['chat_messages'] = cursor.fetchone()[0]

                # Количество Git коммитов
                cursor.execute("SELECT COUNT(*) FROM git_commits WHERE project_id = ?", (project_id,))
                stats['git_commits'] = cursor.fetchone()[0]

                # Размер контекстных файлов
                project_folder = self.context_path / "projects" / f"project_{project_id}"
                if project_folder.exists():
                    total_size = 0
                    for file_path in project_folder.glob("*.txt"):
                        total_size += file_path.stat().st_size
                    stats['context_size'] = total_size
                else:
                    stats['context_size'] = 0

                return stats

        except Exception as e:
            self.logger.error(f"Ошибка получения статистики проекта {project_id}: {e}")
            return {}

    def _create_project_context_files(self, project_id: int, name: str, path: str, tech_stack: List[str]):
        """Создание контекстных файлов для нового проекта"""
        project_folder = self.context_path / "projects" / f"project_{project_id}"
        project_folder.mkdir(parents=True, exist_ok=True)

        # tech_stack.txt
        tech_content = f"=== ТЕХНОЛОГИЧЕСКИЙ СТЕК ===\n"
        tech_content += f"Проект: {name}\n"
        tech_content += f"Путь: {path}\n"
        tech_content += f"Создан: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        tech_content += f"=== ОСНОВНЫЕ ТЕХНОЛОГИИ ===\n"
        for tech in tech_stack:
            tech_content += f"{tech}\n"

        with open(project_folder / "tech_stack.txt", 'w', encoding='utf-8') as f:
            f.write(tech_content)

        # code_snippets.txt (пустой)
        with open(project_folder / "code_snippets.txt", 'w', encoding='utf-8') as f:
            f.write("=== ФРАГМЕНТЫ КОДА ===\n")
            f.write(f"Проект: {name}\n")
            f.write(f"Обновлено: {datetime.now().isoformat()}\n\n")
            f.write("Отслеживаемые файлы будут добавлены здесь...\n")

        # git_context.txt (пустой)
        with open(project_folder / "git_context.txt", 'w', encoding='utf-8') as f:
            f.write("=== GIT КОНТЕКСТ ===\n")
            f.write(f"Проект: {name}\n")
            f.write(f"Путь: {path}\n")
            f.write(f"Обновлено: {datetime.now().isoformat()}\n\n")
            f.write("Git информация будет добавлена при наличии репозитория...\n")

        # chat_context.txt (пустой)
        with open(project_folder / "chat_context.txt", 'w', encoding='utf-8') as f:
            f.write("=== КОНТЕКСТ ЧАТА ===\n")
            f.write(f"Проект: {name}\n")
            f.write(f"Обновлено: {datetime.now().isoformat()}\n\n")
            f.write("История чата будет добавлена здесь...\n")

    def _update_project_context_files(self, project_id: int, project: Dict[str, Any]):
        """Обновление контекстных файлов при изменении проекта"""
        project_folder = self.context_path / "projects" / f"project_{project_id}"

        if not project_folder.exists():
            return

        # Обновляем tech_stack.txt
        tech_file = project_folder / "tech_stack.txt"
        if tech_file.exists():
            try:
                with open(tech_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Обновляем имя и технологии
                lines = content.split('\n')
                new_lines = []

                for line in lines:
                    if line.startswith("Проект:"):
                        new_lines.append(f"Проект: {project['name']}")
                    elif line.startswith("=== ОСНОВНЫЕ ТЕХНОЛОГИИ ==="):
                        new_lines.append(line)
                        for tech in project['tech_stack']:
                            new_lines.append(f"{tech}")
                    elif line.strip() and not line.startswith("Проект:") and not line.startswith("==="):
                        continue  # Пропускаем старые технологии
                    else:
                        new_lines.append(line)

                with open(tech_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_lines))

            except Exception as e:
                self.logger.error(f"Ошибка обновления tech_stack.txt: {e}")

    def export_project(self, project_id: int, export_path: str) -> bool:
        """Экспорт проекта в JSON"""
        try:
            project = self.get_project(project_id)
            if not project:
                return False

            # Добавляем статистику
            project['stats'] = self.get_project_stats(project_id)

            # Добавляем контекстные файлы
            project_folder = self.context_path / "projects" / f"project_{project_id}"
            project['context_files'] = {}

            if project_folder.exists():
                for file_path in project_folder.glob("*.txt"):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        project['context_files'][file_path.name] = f.read()

            # Сохраняем в JSON
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(project, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Проект {project_id} экспортирован в {export_path}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка экспорта проекта {project_id}: {e}")
            return False

    def import_project(self, import_path: str) -> Optional[int]:
        """Импорт проекта из JSON"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            # Создаем проект
            project_id = self.create_project(
                name=project_data['name'],
                path=project_data['path'],
                description=project_data.get('description', ''),
                tech_stack=project_data.get('tech_stack', [])
            )

            if project_id:
                # Восстанавливаем контекстные файлы
                project_folder = self.context_path / "projects" / f"project_{project_id}"

                if 'context_files' in project_data:
                    for filename, content in project_data['context_files'].items():
                        with open(project_folder / filename, 'w', encoding='utf-8') as f:
                            f.write(content)

            self.logger.info(f"Проект импортирован с ID: {project_id}")
            return project_id

        except Exception as e:
            self.logger.error(f"Ошибка импорта проекта: {e}")
            return None
