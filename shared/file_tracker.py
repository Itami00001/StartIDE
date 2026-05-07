import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
import fnmatch
import hashlib

class FileTracker:
    """Отслеживание файлов в проектах START-beta"""

    def __init__(self, context_path: str = "context"):
        self.context_path = Path(context_path)
        self.db_path = self.context_path / "start_beta.db"
        self.logger = logging.getLogger(__name__)

        # Расширения файлов по умолчанию для отслеживания
        self.default_extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.md', '.txt', '.json', '.xml', '.yaml', '.yml']

        # Папки для исключения
        self.exclude_folders = {'__pycache__', '.git', '.vscode', 'node_modules', '.idea', 'venv', 'env', 'dist', 'build'}

        # Файлы для исключения
        self.exclude_files = {'.gitignore', '.DS_Store', 'Thumbs.db', '*.pyc', '*.pyo', '*.pyd'}

    def add_file(self, project_id: int, file_path: str, line_ranges: List[Dict[str, int]] = None,
                 description: str = "", tags: List[str] = None) -> bool:
        """Добавление файла в отслеживание"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Проверяем что проект существует
                cursor.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
                if not cursor.fetchone():
                    return False

                # Проверяем что файл существует
                full_path = Path(file_path)
                if not full_path.exists():
                    return False

                # Получаем относительный путь
                project_info = cursor.execute("SELECT path FROM projects WHERE id = ?", (project_id,)).fetchone()
                if project_info:
                    project_path = Path(project_info[0])
                    try:
                        relative_path = str(full_path.relative_to(project_path))
                    except ValueError:
                        relative_path = file_path
                else:
                    relative_path = file_path

                # Проверяем что файл еще не отслеживается
                cursor.execute("SELECT id FROM files_tracking WHERE project_id = ? AND file_path = ?",
                             (project_id, relative_path))
                if cursor.fetchone():
                    return False

                # Получаем хэш файла
                file_hash = self._get_file_hash(full_path)

                # Добавляем файл
                now = datetime.now().isoformat()
                cursor.execute("""
                    INSERT INTO files_tracking
                    (project_id, file_path, description, line_ranges, tags, file_hash, created, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (project_id, relative_path, description, json.dumps(line_ranges or []),
                      json.dumps(tags or []), file_hash, now, now))

                conn.commit()

                # Обновляем контекстные файлы
                self._update_code_snippets(project_id)

                self.logger.info(f"Файл {relative_path} добавлен в отслеживание для проекта {project_id}")
                return True

        except Exception as e:
            self.logger.error(f"Ошибка добавления файла в отслеживание: {e}")
            return False

    def remove_file(self, project_id: int, file_path: str) -> bool:
        """Удаление файла из отслеживания"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    DELETE FROM files_tracking
                    WHERE project_id = ? AND file_path = ?
                """, (project_id, file_path))

                conn.commit()

                if cursor.rowcount > 0:
                    # Обновляем контекстные файлы
                    self._update_code_snippets(project_id)
                    self.logger.info(f"Файл {file_path} удален из отслеживания для проекта {project_id}")
                    return True

                return False

        except Exception as e:
            self.logger.error(f"Ошибка удаления файла из отслеживания: {e}")
            return False

    def get_tracked_files(self, project_id: int) -> List[Dict[str, Any]]:
        """Получение всех отслеживаемых файлов проекта"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM files_tracking
                    WHERE project_id = ?
                    ORDER BY created DESC
                """, (project_id,))

                files = []
                for row in cursor.fetchall():
                    file_info = dict(row)
                    file_info['line_ranges'] = json.loads(file_info['line_ranges'])
                    file_info['tags'] = json.loads(file_info['tags'])
                    files.append(file_info)

                return files

        except Exception as e:
            self.logger.error(f"Ошибка получения отслеживаемых файлов: {e}")
            return []

    def update_file_info(self, project_id: int, file_path: str, line_ranges: List[Dict[str, int]] = None,
                        description: str = None, tags: List[str] = None) -> bool:
        """Обновление информации об отслеживаемом файле"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                updates = []
                params = []

                if line_ranges is not None:
                    updates.append("line_ranges = ?")
                    params.append(json.dumps(line_ranges))

                if description is not None:
                    updates.append("description = ?")
                    params.append(description)

                if tags is not None:
                    updates.append("tags = ?")
                    params.append(json.dumps(tags))

                if updates:
                    updates.append("updated_at = ?")
                    params.append(datetime.now().isoformat())
                    params.extend([project_id, file_path])

                    cursor.execute(f"""
                        UPDATE files_tracking
                        SET {', '.join(updates)}
                        WHERE project_id = ? AND file_path = ?
                    """, params)

                    conn.commit()

                    if cursor.rowcount > 0:
                        # Обновляем контекстные файлы
                        self._update_code_snippets(project_id)
                        return True

                return False

        except Exception as e:
            self.logger.error(f"Ошибка обновления информации о файле: {e}")
            return False

    def auto_discover_files(self, project_id: int, extensions: List[str] = None) -> int:
        """Автоматическое обнаружение файлов в проекте"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Получаем путь проекта
                cursor.execute("SELECT path FROM projects WHERE id = ?", (project_id,))
                project_info = cursor.fetchone()
                if not project_info:
                    return 0

                project_path = Path(project_info[0])
                if not project_path.exists():
                    return 0

                extensions = extensions or self.default_extensions
                discovered_count = 0

                # Рекурсивный поиск файлов
                for file_path in project_path.rglob("*"):
                    if file_path.is_file():
                        # Проверяем расширение
                        if not any(file_path.suffix.lower() in ext.lower() for ext in extensions):
                            continue

                        # Проверяем исключенные папки
                        if any(exclude in file_path.parts for exclude in self.exclude_folders):
                            continue

                        # Проверяем исключенные файлы
                        if any(fnmatch.fnmatch(file_path.name, pattern) for pattern in self.exclude_files):
                            continue

                        # Получаем относительный путь
                        try:
                            relative_path = str(file_path.relative_to(project_path))
                        except ValueError:
                            continue

                        # Проверяем что файл еще не отслеживается
                        cursor.execute("SELECT id FROM files_tracking WHERE project_id = ? AND file_path = ?",
                                     (project_id, relative_path))
                        if not cursor.fetchone():
                            # Добавляем файл
                            file_hash = self._get_file_hash(file_path)
                            now = datetime.now().isoformat()

                            cursor.execute("""
                                INSERT INTO files_tracking
                                (project_id, file_path, description, line_ranges, tags, file_hash, created, updated_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (project_id, relative_path, "", json.dumps([]), json.dumps([]),
                                  file_hash, now, now))

                            discovered_count += 1

                conn.commit()

                if discovered_count > 0:
                    # Обновляем контекстные файлы
                    self._update_code_snippets(project_id)
                    self.logger.info(f"Обнаружено и добавлено {discovered_count} файлов для проекта {project_id}")

                return discovered_count

        except Exception as e:
            self.logger.error(f"Ошибка автоматического обнаружения файлов: {e}")
            return 0

    def get_file_content(self, project_id: int, file_path: str, line_ranges: List[Dict[str, int]] = None) -> str:
        """Получение содержимого файла с учетом диапазонов строк"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Получаем путь проекта
                cursor.execute("SELECT path FROM projects WHERE id = ?", (project_id,))
                project_info = cursor.fetchone()
                if not project_info:
                    return ""

                project_path = Path(project_info[0])
                full_path = project_path / file_path

                if not full_path.exists():
                    return ""

                # Если указаны диапазоны строк
                if line_ranges:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()

                    result = []
                    for range_info in line_ranges:
                        start = range_info.get('start', 1)
                        end = range_info.get('end', len(lines))

                        # Корректируем индексы
                        start = max(1, start)
                        end = min(len(lines), end)

                        if start <= end:
                            result.append(f"=== Строки {start}-{end} ===\n")
                            result.extend(lines[start-1:end])
                            result.append("\n")

                    return ''.join(result)
                else:
                    # Возвращаем весь файл
                    with open(full_path, 'r', encoding='utf-8') as f:
                        return f.read()

        except Exception as e:
            self.logger.error(f"Ошибка получения содержимого файла: {e}")
            return ""

    def check_file_changes(self, project_id: int) -> List[Dict[str, Any]]:
        """Проверка изменений в отслеживаемых файлах"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Получаем путь проекта
                cursor.execute("SELECT path FROM projects WHERE id = ?", (project_id,))
                project_info = cursor.fetchone()
                if not project_info:
                    return []

                project_path = Path(project_info[0])
                changed_files = []

                # Получаем все отслеживаемые файлы
                cursor.execute("""
                    SELECT file_path, file_hash FROM files_tracking
                    WHERE project_id = ?
                """, (project_id,))

                for file_path, stored_hash in cursor.fetchall():
                    full_path = project_path / file_path

                    if full_path.exists():
                        current_hash = self._get_file_hash(full_path)
                        if current_hash != stored_hash:
                            # Обновляем хэш в базе
                            cursor.execute("""
                                UPDATE files_tracking
                                SET file_hash = ?, updated_at = ?
                                WHERE project_id = ? AND file_path = ?
                            """, (current_hash, datetime.now().isoformat(), project_id, file_path))

                            changed_files.append({
                                'file_path': file_path,
                                'status': 'modified',
                                'old_hash': stored_hash,
                                'new_hash': current_hash
                            })
                    else:
                        # Файл удален
                        changed_files.append({
                            'file_path': file_path,
                            'status': 'deleted',
                            'old_hash': stored_hash
                        })

                conn.commit()

                if changed_files:
                    # Обновляем контекстные файлы
                    self._update_code_snippets(project_id)

                return changed_files

        except Exception as e:
            self.logger.error(f"Ошибка проверки изменений файлов: {e}")
            return []

    def search_files(self, project_id: int, query: str, search_content: bool = False) -> List[Dict[str, Any]]:
        """Поиск файлов по имени или содержимому"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Поиск по имени файла
                search_query = f"%{query}%"
                cursor.execute("""
                    SELECT * FROM files_tracking
                    WHERE project_id = ? AND file_path LIKE ?
                    ORDER BY updated_at DESC
                """, (project_id, search_query))

                files = []
                for row in cursor.fetchall():
                    file_info = dict(row)
                    file_info['line_ranges'] = json.loads(file_info['line_ranges'])
                    file_info['tags'] = json.loads(file_info['tags'])
                    files.append(file_info)

                # Если нужно, ищем по содержимому
                if search_content:
                    cursor.execute("SELECT path FROM projects WHERE id = ?", (project_id,))
                    project_info = cursor.fetchone()
                    if project_info:
                        project_path = Path(project_info[0])

                        content_matches = []
                        for file_info in files:
                            full_path = project_path / file_info['file_path']
                            if full_path.exists():
                                try:
                                    with open(full_path, 'r', encoding='utf-8') as f:
                                        content = f.read()
                                        if query.lower() in content.lower():
                                            file_info['content_match'] = True
                                            content_matches.append(file_info)
                                except:
                                    pass

                        if content_matches:
                            files = content_matches

                return files

        except Exception as e:
            self.logger.error(f"Ошибка поиска файлов: {e}")
            return []

    def get_file_stats(self, project_id: int) -> Dict[str, Any]:
        """Получение статистики отслеживаемых файлов"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                stats = {}

                # Общее количество файлов
                cursor.execute("SELECT COUNT(*) FROM files_tracking WHERE project_id = ?", (project_id,))
                stats['total_files'] = cursor.fetchone()[0]

                # По расширениям
                cursor.execute("""
                    SELECT file_path FROM files_tracking WHERE project_id = ?
                """, (project_id,))

                extensions = {}
                for (file_path,) in cursor.fetchall():
                    ext = Path(file_path).suffix.lower()
                    extensions[ext] = extensions.get(ext, 0) + 1

                stats['extensions'] = extensions

                # По тегам
                cursor.execute("SELECT tags FROM files_tracking WHERE project_id = ?", (project_id,))
                all_tags = []
                for (tags_json,) in cursor.fetchall():
                    tags = json.loads(tags_json)
                    all_tags.extend(tags)

                tag_counts = {}
                for tag in all_tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

                stats['tags'] = tag_counts

                # Размер файлов
                cursor.execute("SELECT path FROM projects WHERE id = ?", (project_id,))
                project_info = cursor.fetchone()
                if project_info:
                    project_path = Path(project_info[0])
                    total_size = 0

                    cursor.execute("SELECT file_path FROM files_tracking WHERE project_id = ?", (project_id,))
                    for (file_path,) in cursor.fetchall():
                        full_path = project_path / file_path
                        if full_path.exists():
                            total_size += full_path.stat().st_size

                    stats['total_size'] = total_size

                return stats

        except Exception as e:
            self.logger.error(f"Ошибка получения статистики файлов: {e}")
            return {}

    def _get_file_hash(self, file_path: Path) -> str:
        """Получение хэша файла"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    def _update_code_snippets(self, project_id: int):
        """Обновление файла code_snippets.txt"""
        try:
            project_folder = self.context_path / "projects" / f"project_{project_id}"
            if not project_folder.exists():
                return

            # Получаем информацию о проекте
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name, path FROM projects WHERE id = ?", (project_id,))
                project_info = cursor.fetchone()
                if not project_info:
                    return

                project_name, project_path = project_info

            # Получаем отслеживаемые файлы
            tracked_files = self.get_tracked_files(project_id)

            # Формируем содержимое
            content = f"=== ФРАГМЕНТЫ КОДА ===\n"
            content += f"Проект: {project_name}\n"
            content += f"Путь: {project_path}\n"
            content += f"Обновлено: {datetime.now().isoformat()}\n\n"

            if tracked_files:
                content += f"=== ОТСЛЕЖИВАЕМЫЕ ФАЙЛЫ ({len(tracked_files)}) ===\n\n"

                for file_info in tracked_files:
                    file_path = Path(project_path) / file_info['file_path']
                    relative_path = file_info['file_path']

                    content += f"Файл: {relative_path}\n"

                    if file_info['description']:
                        content += f"Описание: {file_info['description']}\n"

                    if file_info['tags']:
                        content += f"Теги: {', '.join(file_info['tags'])}\n"

                    if file_info['line_ranges']:
                        content += f"Отслеживаемые строки: {file_info['line_ranges']}\n"

                    # Добавляем содержимое файла
                    if file_path.exists():
                        try:
                            file_content = self.get_file_content(project_id, relative_path, file_info['line_ranges'])

                            # Ограничиваем размер содержимого
                            lines = file_content.split('\n')
                            if len(lines) > 50:
                                content += "Содержимое (первые 50 строк):\n"
                                content += '\n'.join(lines[:50]) + "\n...\n"
                            else:
                                content += "Содержимое:\n"
                                content += file_content + "\n"

                        except Exception as e:
                            content += f"Ошибка чтения файла: {e}\n"
                    else:
                        content += "Файл не найден\n"

                    content += "\n" + "="*50 + "\n\n"
            else:
                content += "Нет отслеживаемых файлов\n"

            # Сохраняем файл
            with open(project_folder / "code_snippets.txt", 'w', encoding='utf-8') as f:
                f.write(content)

        except Exception as e:
            self.logger.error(f"Ошибка обновления code_snippets.txt: {e}")

    def export_tracking_data(self, project_id: int, export_path: str) -> bool:
        """Экспорт данных отслеживания в JSON"""
        try:
            files = self.get_tracked_files(project_id)

            # Добавляем содержимое файлов
            for file_info in files:
                file_info['content'] = self.get_file_content(
                    project_id, file_info['file_path'], file_info['line_ranges']
                )

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(files, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Данные отслеживания проекта {project_id} экспортированы в {export_path}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка экспорта данных отслеживания: {e}")
            return False
