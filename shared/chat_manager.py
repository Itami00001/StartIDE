import sqlite3
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

class ChatManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)

    def add_message(self, project_id: int, sender: str, message_type: str, content: str,
                    voice_file_path: str = None) -> int:
        """Добавление сообщения в чат"""
        try:
            cursor = self.db_manager.conn.execute(
                """
                INSERT INTO chat_messages
                (project_id, sender, message_type, content, voice_file_path)
                VALUES (?, ?, ?, ?, ?)
                """,
                (project_id, sender, message_type, content, voice_file_path)
            )

            message_id = cursor.lastrowid
            self.db_manager.conn.commit()

            # Обновляем chat_context.txt файл
            self._update_chat_context_file(project_id)

            self.logger.info(f"Добавлено сообщение от {sender} для проекта {project_id}")
            return message_id

        except Exception as e:
            self.logger.error(f"Ошибка добавления сообщения: {e}")
            return -1

    def get_messages(self, project_id: int, limit: int = 50,
                     message_type: str = None) -> List[Dict]:
        """Получение сообщений из чата"""
        try:
            query = """
                SELECT id, sender, message_type, content, voice_file_path, timestamp
                FROM chat_messages
                WHERE project_id = ?
            """
            params = [project_id]

            if message_type:
                query += " AND message_type = ?"
                params.append(message_type)

            # Сортируем по id DESC чтобы взять последние N сообщений, затем перевернём в хронологический
            query += " ORDER BY id DESC LIMIT ?"
            params.append(limit)

            cursor = self.db_manager.conn.execute(query, params)
            messages = []

            for row in cursor.fetchall():
                messages.append({
                    'id': row[0],
                    'sender': row[1],
                    'message_type': row[2],
                    'content': row[3],
                    'voice_file_path': row[4],
                    'timestamp': row[5]
                })

            # Переворачиваем: старые сообщения сначала, новые в конце
            messages.reverse()
            return messages

        except Exception as e:
            self.logger.error(f"Ошибка получения сообщений: {e}")
            return []

    def get_conversation_history(self, project_id: int, limit: int = 20) -> str:
        """Получение истории диалога в текстовом формате"""
        try:
            messages = self.get_messages(project_id, limit)

            if not messages:
                return "История диалога пуста"

            history_lines = []
            history_lines.append(f"=== ИСТОРИЯ ДИАЛОГА ===")
            history_lines.append(f"Проект ID: {project_id}")
            history_lines.append(f"Всего сообщений: {len(messages)}")
            history_lines.append("")

            for msg in messages:
                timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                message_type = f"[{msg['message_type'].upper()}]" if msg['message_type'] != 'text' else ""

                line = f"[{timestamp}] {msg['sender']} → AI: {message_type} {msg['content']}"
                history_lines.append(line)

            return '\n'.join(history_lines)

        except Exception as e:
            self.logger.error(f"Ошибка получения истории диалога: {e}")
            return "Ошибка получения истории"

    def get_ai_context(self, project_id: int) -> str:
        """Получение контекста для AI (форматированная история)"""
        try:
            messages = self.get_messages(project_id, limit=30)

            if not messages:
                return "Нет предыдущих сообщений"

            context_lines = []
            context_lines.append("=== КОНТЕКСТ ЧАТА ===")
            context_lines.append(f"Проект ID: {project_id}")
            context_lines.append(f"Всего сообщений: {len(messages)}")
            context_lines.append("")

            for msg in messages:
                # Форматируем для AI
                if msg['sender'] in ['StartIDE', 'StartOffice']:
                    role = "Пользователь"
                else:
                    role = "AI"

                message_type = ""
                if msg['message_type'] == 'voice':
                    message_type = "[ГОЛОС] "
                elif msg['message_type'] == 'file_analysis':
                    message_type = "[АНАЛИЗ ФАЙЛА] "

                line = f"{role}: {message_type}{msg['content']}"
                context_lines.append(line)

            return '\n'.join(context_lines)

        except Exception as e:
            self.logger.error(f"Ошибка получения AI контекста: {e}")
            return "Ошибка получения контекста"

    def _update_chat_context_file(self, project_id: int):
        """Обновление chat_context.txt файла"""
        try:
            project_folder = self.db_manager.projects_dir / f"project_{project_id}"
            project_folder.mkdir(parents=True, exist_ok=True)

            # Получаем информацию о проекте
            cursor = self.db_manager.conn.execute(
                "SELECT name, path FROM projects WHERE id = ?",
                (project_id,)
            )
            project_info = cursor.fetchone()

            # Получаем последние сообщения
            messages = self.get_messages(project_id, limit=20)

            content = []
            content.append("=== КОНТЕКСТ ЧАТА ===")

            if project_info:
                content.append(f"Проект: {project_info[0]}")
            else:
                content.append(f"Проект ID: {project_id}")

            content.append(f"Всего сообщений: {len(messages)}")
            content.append(f"Обновлено: {datetime.now().isoformat()}")
            content.append("")

            if messages:
                content.append("=== ИСТОРИЯ ДИАЛОГА ===")
                for msg in messages:
                    timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%Y-%m-%d %H:%M:%S')

                    message_type = ""
                    if msg['message_type'] == 'voice':
                        message_type = "[ГОЛОС] "
                    elif msg['message_type'] == 'file_analysis':
                        message_type = "[АНАЛИЗ ФАЙЛА] "

                    line = f"[{timestamp}] {msg['sender']} → AI: {message_type}{msg['content']}"
                    content.append(line)
                content.append("")

            # Статистика по типам сообщений
            cursor = self.db_manager.conn.execute(
                """
                SELECT message_type, COUNT(*) as count
                FROM chat_messages
                WHERE project_id = ?
                GROUP BY message_type
                """,
                (project_id,)
            )

            stats = cursor.fetchall()
            if stats:
                content.append("=== СТАТИСТИКА СООБЩЕНИЙ ===")
                for msg_type, count in stats:
                    content.append(f"{msg_type}: {count}")
                content.append("")

            with open(project_folder / "chat_context.txt", 'w', encoding='utf-8') as f:
                f.write('\n'.join(content))

        except Exception as e:
            self.logger.error(f"Ошибка обновления chat_context.txt: {e}")

    def clear_chat_history(self, project_id: int) -> bool:
        """Очистка истории чата"""
        try:
            self.db_manager.conn.execute(
                "DELETE FROM chat_messages WHERE project_id = ?",
                (project_id,)
            )
            self.db_manager.conn.commit()

            # Обновляем файл
            self._update_chat_context_file(project_id)

            self.logger.info(f"Очищена история чата для проекта {project_id}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка очистки истории чата: {e}")
            return False

    def delete_message(self, message_id: int) -> bool:
        """Удаление конкретного сообщения"""
        try:
            # Получаем project_id для обновления файла
            cursor = self.db_manager.conn.execute(
                "SELECT project_id FROM chat_messages WHERE id = ?",
                (message_id,)
            )
            result = cursor.fetchone()

            if not result:
                return False

            project_id = result[0]

            # Удаляем сообщение
            self.db_manager.conn.execute(
                "DELETE FROM chat_messages WHERE id = ?",
                (message_id,)
            )
            self.db_manager.conn.commit()

            # Обновляем файл
            self._update_chat_context_file(project_id)

            self.logger.info(f"Удалено сообщение {message_id}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка удаления сообщения: {e}")
            return False

    def get_chat_statistics(self, project_id: int) -> Dict:
        """Получение статистики чата"""
        try:
            stats = {}

            # Общее количество сообщений
            cursor = self.db_manager.conn.execute(
                "SELECT COUNT(*) FROM chat_messages WHERE project_id = ?",
                (project_id,)
            )
            stats['total_messages'] = cursor.fetchone()[0]

            # Сообщения по отправителям
            cursor = self.db_manager.conn.execute(
                """
                SELECT sender, COUNT(*) as count
                FROM chat_messages
                WHERE project_id = ?
                GROUP BY sender
                """,
                (project_id,)
            )
            stats['by_sender'] = dict(cursor.fetchall())

            # Сообщения по типам
            cursor = self.db_manager.conn.execute(
                """
                SELECT message_type, COUNT(*) as count
                FROM chat_messages
                WHERE project_id = ?
                GROUP BY message_type
                """,
                (project_id,)
            )
            stats['by_type'] = dict(cursor.fetchall())

            # Последнее сообщение
            cursor = self.db_manager.conn.execute(
                """
                SELECT sender, content, timestamp
                FROM chat_messages
                WHERE project_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (project_id,)
            )
            last_msg = cursor.fetchone()
            if last_msg:
                stats['last_message'] = {
                    'sender': last_msg[0],
                    'content': last_msg[1][:100] + "..." if len(last_msg[1]) > 100 else last_msg[1],
                    'timestamp': last_msg[2]
                }

            return stats

        except Exception as e:
            self.logger.error(f"Ошибка получения статистики чата: {e}")
            return {}

    def search_messages(self, project_id: int, query: str, limit: int = 20) -> List[Dict]:
        """Поиск сообщений"""
        try:
            cursor = self.db_manager.conn.execute(
                """
                SELECT id, sender, message_type, content, timestamp
                FROM chat_messages
                WHERE project_id = ? AND content LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (project_id, f"%{query}%", limit)
            )

            results = []
            for row in cursor.fetchall():
                results.append({
                    'id': row[0],
                    'sender': row[1],
                    'message_type': row[2],
                    'content': row[3],
                    'timestamp': row[4]
                })

            return results

        except Exception as e:
            self.logger.error(f"Ошибка поиска сообщений: {e}")
            return []

    def clear_chat(self, project_id: int) -> bool:
        """Псевдоним для clear_chat_history"""
        return self.clear_chat_history(project_id)

    def export_chat_history(self, project_id: int, format_type: str = 'json') -> str:
        """Экспорт истории чата"""
        try:
            messages = self.get_messages(project_id, limit=1000)

            if format_type == 'json':
                return json.dumps(messages, indent=2, ensure_ascii=False, default=str)

            elif format_type == 'txt':
                lines = []
                lines.append("=== ЭКСПОРТ ИСТОРИИ ЧАТА ===")
                lines.append(f"Проект ID: {project_id}")
                lines.append(f"Дата экспорта: {datetime.now().isoformat()}")
                lines.append(f"Количество сообщений: {len(messages)}")
                lines.append("")

                for msg in messages:
                    timestamp = datetime.fromisoformat(msg['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                    lines.append(f"[{timestamp}] {msg['sender']} ({msg['message_type']}): {msg['content']}")

                return '\n'.join(lines)

            else:
                return "Неподдерживаемый формат экспорта"

        except Exception as e:
            self.logger.error(f"Ошибка экспорта истории чата: {e}")
            return f"Ошибка экспорта: {e}"
