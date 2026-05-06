import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from .chat_manager import ChatManager
from .ollama_manager import OllamaManager
from .tech_stack_manager import TechStackManager

class AIIntegrationManager:
    def __init__(self, db_manager, ollama_base_url: str = "http://localhost:11434", 
                 ollama_model: str = "llama3.1"):
        self.db_manager = db_manager
        self.chat_manager = ChatManager(db_manager)
        self.ollama_manager = OllamaManager(ollama_base_url, ollama_model)
        self.logger = logging.getLogger(__name__)
        
        # Кэш для контекста проекта
        self.context_cache = {}
    
    def send_message_to_ai(self, project_id: int, message: str, message_type: str = "text",
                          voice_file_path: str = None) -> Tuple[bool, str]:
        """Отправка сообщения AI и получение ответа"""
        try:
            # Добавляем сообщение пользователя в чат
            self.chat_manager.add_message(
                project_id=project_id,
                sender="StartIDE" if message_type != "voice" else "StartIDE",
                message_type=message_type,
                content=message,
                voice_file_path=voice_file_path
            )
            
            # Получаем контекст для AI
            ai_context = self._prepare_ai_context(project_id)
            
            # Формируем полный промпт
            full_prompt = self._build_prompt(ai_context, message)
            
            # Отправляем в Ollama
            response = self.ollama_manager.session.post(
                f"{self.ollama_manager.base_url}/api/generate",
                json={
                    "model": self.ollama_manager.model,
                    "prompt": full_prompt,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                ai_response = response.json().get('response', 'Нет ответа')
                
                # Добавляем ответ AI в чат
                self.chat_manager.add_message(
                    project_id=project_id,
                    sender="AI",
                    message_type="text",
                    content=ai_response
                )
                
                self.logger.info(f"Получен ответ AI для проекта {project_id}")
                return True, ai_response
            else:
                error_msg = f"Ошибка Ollama: {response.status_code}"
                self.logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Ошибка отправки сообщения AI: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def _prepare_ai_context(self, project_id: int) -> str:
        """Подготовка контекста для AI"""
        try:
            # Проверяем кэш
            if project_id in self.context_cache:
                cache_time = self.context_cache[project_id]['timestamp']
                # Кэш действителен 5 минут
                if (datetime.now() - cache_time).seconds < 300:
                    return self.context_cache[project_id]['context']
            
            # Собираем контекст из разных источников
            context_parts = []
            
            # 1. Информация о проекте
            project_info = self._get_project_info(project_id)
            if project_info:
                context_parts.append(project_info)
            
            # 2. Технологический стек
            tech_stack = self._get_tech_stack_context(project_id)
            if tech_stack:
                context_parts.append(tech_stack)
            
            # 3. История чата
            chat_context = self.chat_manager.get_ai_context(project_id)
            if chat_context:
                context_parts.append(chat_context)
            
            # 4. Git контекст
            git_context = self._get_git_context(project_id)
            if git_context:
                context_parts.append(git_context)
            
            # 5. Отслеживаемые файлы
            files_context = self._get_files_context(project_id)
            if files_context:
                context_parts.append(files_context)
            
            full_context = "\n\n".join(context_parts)
            
            # Сохраняем в кэш
            self.context_cache[project_id] = {
                'context': full_context,
                'timestamp': datetime.now()
            }
            
            return full_context
            
        except Exception as e:
            self.logger.error(f"Ошибка подготовки контекста AI: {e}")
            return "Контекст проекта недоступен"
    
    def _get_project_info(self, project_id: int) -> str:
        """Получение базовой информации о проекте"""
        try:
            cursor = self.db_manager.conn.execute(
                "SELECT name, path, status, created FROM projects WHERE id = ?",
                (project_id,)
            )
            result = cursor.fetchone()
            
            if result:
                return f"=== ПРОЕКТ ===\nНазвание: {result[0]}\nПуть: {result[1]}\nСтатус: {result[2]}\nСоздан: {result[3]}"
            
            return ""
            
        except Exception as e:
            self.logger.error(f"Ошибка получения информации о проекте: {e}")
            return ""
    
    def _get_tech_stack_context(self, project_id: int) -> str:
        """Получение контекста технологического стека"""
        try:
            cursor = self.db_manager.conn.execute(
                """
                SELECT technology, version, confidence
                FROM tech_stack 
                WHERE project_id = ? 
                ORDER BY confidence DESC
                LIMIT 10
                """,
                (project_id,)
            )
            
            tech_items = cursor.fetchall()
            if tech_items:
                context = "=== ТЕХНОЛОГИЧЕСКИЙ СТЕК ===\n"
                for tech, version, confidence in tech_items:
                    version_str = f" ({version})" if version else ""
                    context += f"- {tech}{version_str}\n"
                return context
            
            return ""
            
        except Exception as e:
            self.logger.error(f"Ошибка получения технологического стека: {e}")
            return ""
    
    def _get_git_context(self, project_id: int) -> str:
        """Получение Git контекста"""
        try:
            project_folder = self.db_manager.projects_dir / f"project_{project_id}"
            git_context_file = project_folder / "git_context.txt"
            
            if git_context_file.exists():
                with open(git_context_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Ограничиваем размер контекста
                    if len(content) > 2000:
                        content = content[:2000] + "\n... (обрезано)"
                    return content
            
            return ""
            
        except Exception as e:
            self.logger.error(f"Ошибка получения Git контекста: {e}")
            return ""
    
    def _get_files_context(self, project_id: int) -> str:
        """Получение контекста отслеживаемых файлов"""
        try:
            cursor = self.db_manager.conn.execute(
                """
                SELECT file_path, line_ranges
                FROM files_tracking 
                WHERE project_id = ? AND is_tracking = TRUE
                LIMIT 5
                """,
                (project_id,)
            )
            
            files = cursor.fetchall()
            if files:
                context = "=== ОТСЛЕЖИВАЕМЫЕ ФАЙЛЫ ===\n"
                for file_path, line_ranges in files:
                    ranges = f" (строки: {line_ranges})" if line_ranges else ""
                    context += f"- {file_path}{ranges}\n"
                return context
            
            return ""
            
        except Exception as e:
            self.logger.error(f"Ошибка получения контекста файлов: {e}")
            return ""
    
    def _build_prompt(self, context: str, user_message: str) -> str:
        """Построение полного промпта для AI"""
        prompt_parts = []
        
        # Системная инструкция
        prompt_parts.append("Ты - AI ассистент для разработки программного обеспечения.")
        prompt_parts.append("Отвечай на русском языке. Будь кратким и точным.")
        prompt_parts.append("Используй предоставленный контекст проекта для формирования ответа.")
        prompt_parts.append("")
        
        # Контекст проекта
        if context:
            prompt_parts.append("=== КОНТЕКСТ ПРОЕКТА ===")
            prompt_parts.append(context)
            prompt_parts.append("")
        
        # Вопрос пользователя
        prompt_parts.append("=== ВОПРОС ПОЛЬЗОВАТЕЛЯ ===")
        prompt_parts.append(user_message)
        prompt_parts.append("")
        
        # Запрос ответа
        prompt_parts.append("=== ОТВЕТ ===")
        
        return "\n".join(prompt_parts)
    
    def analyze_code_with_ai(self, project_id: int, file_path: str, code_content: str) -> Tuple[bool, str]:
        """Анализ кода с помощью AI"""
        try:
            # Добавляем сообщение об анализе файла
            self.chat_manager.add_message(
                project_id=project_id,
                sender="StartIDE",
                message_type="file_analysis",
                content=f"Анализ файла: {file_path}"
            )
            
            # Готовим контекст для анализа
            context_parts = []
            
            # Базовый контекст проекта
            base_context = self._prepare_ai_context(project_id)
            if base_context:
                context_parts.append(base_context)
            
            # Контекст файла
            file_context = f"=== АНАЛИЗИРУЕМЫЙ ФАЙЛ ===\nПуть: {file_path}\n\n=== КОД ===\n{code_content}"
            context_parts.append(file_context)
            
            full_context = "\n\n".join(context_parts)
            
            # Промпт для анализа кода
            prompt = f"""{full_context}

=== ЗАДАЧА ===
Проанализируй предоставленный код и дай краткую рекомендацию по улучшению.
Обрати внимание на:
1. Потенциальные ошибки
2. Оптимизацию производительности
3. Стиль кода
4. Безопасность

=== ОТВЕТ ==="""
            
            # Отправляем в Ollama
            response = self.ollama_manager.session.post(
                f"{self.ollama_manager.base_url}/api/generate",
                json={
                    "model": self.ollama_manager.model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                ai_response = response.json().get('response', 'Нет ответа')
                
                # Добавляем ответ AI в чат
                self.chat_manager.add_message(
                    project_id=project_id,
                    sender="AI",
                    message_type="file_analysis",
                    content=f"Анализ файла {file_path}:\n\n{ai_response}"
                )
                
                self.logger.info(f"Выполнен анализ файла {file_path}")
                return True, ai_response
            else:
                error_msg = f"Ошибка анализа кода: {response.status_code}"
                self.logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Ошибка анализа кода: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def get_project_summary_for_ai(self, project_id: int) -> str:
        """Получение сводки проекта для AI"""
        try:
            summary_parts = []
            
            # Основная информация
            project_info = self._get_project_info(project_id)
            if project_info:
                summary_parts.append(project_info)
            
            # Технологический стек
            tech_stack = self._get_tech_stack_context(project_id)
            if tech_stack:
                summary_parts.append(tech_stack)
            
            # Статистика чата
            chat_stats = self.chat_manager.get_chat_statistics(project_id)
            if chat_stats:
                stats_text = f"=== СТАТИСТИКА ВЗАИМОДЕЙСТВИЯ ===\n"
                stats_text += f"Всего сообщений: {chat_stats.get('total_messages', 0)}\n"
                if 'last_message' in chat_stats:
                    stats_text += f"Последнее сообщение: {chat_stats['last_message']['content']}"
                summary_parts.append(stats_text)
            
            return "\n\n".join(summary_parts)
            
        except Exception as e:
            self.logger.error(f"Ошибка получения сводки проекта: {e}")
            return "Ошибка получения данных проекта"
    
    def clear_context_cache(self, project_id: int = None):
        """Очистка кэша контекста"""
        if project_id:
            self.context_cache.pop(project_id, None)
            self.logger.info(f"Очищен кэш контекста для проекта {project_id}")
        else:
            self.context_cache.clear()
            self.logger.info("Очищен весь кэш контекста")
    
    def test_ai_connection(self) -> Tuple[bool, str]:
        """Тест подключения к AI"""
        try:
            if self.ollama_manager.test_connection():
                return True, "Подключение к Ollama успешно"
            else:
                return False, "Не удалось подключиться к Ollama"
        except Exception as e:
            return False, f"Ошибка тестирования подключения: {e}"
