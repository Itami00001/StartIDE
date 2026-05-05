import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging

class SharedChatManager:
    """Менеджер общего чата между StartIDE и StartOffice"""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.chat_file = self.project_path / ".shared_chat.json"
        self.logger = logging.getLogger(__name__)
        
    def add_message(self, sender: str, message_type: str, content: str, 
                   file_name: str = None, file_content: str = None) -> bool:
        """Добавление сообщения в общий чат"""
        try:
            chat_data = self.load_chat()
            
            message = {
                "timestamp": datetime.now().isoformat(),
                "sender": sender,  # "StartIDE" или "StartOffice"
                "type": message_type,  # "text", "file", "code_analysis"
                "content": content,
                "file_name": file_name,
                "file_content": file_content[:5000] if file_content else None  # Ограничиваем размер
            }
            
            chat_data["messages"].append(message)
            
            # Ограничиваем историю последними 100 сообщениями
            if len(chat_data["messages"]) > 100:
                chat_data["messages"] = chat_data["messages"][-100:]
            
            chat_data["last_updated"] = datetime.now().isoformat()
            
            self.save_chat(chat_data)
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка добавления сообщения в чат: {e}")
            return False
    
    def load_chat(self) -> Dict:
        """Загрузка истории чата"""
        try:
            if self.chat_file.exists():
                with open(self.chat_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {
                    "project": self.project_path.name,
                    "created": datetime.now().isoformat(),
                    "messages": [],
                    "last_updated": datetime.now().isoformat()
                }
        except Exception as e:
            self.logger.error(f"Ошибка загрузки чата: {e}")
            return {"messages": []}
    
    def save_chat(self, chat_data: Dict):
        """Сохранение истории чата"""
        try:
            with open(self.chat_file, 'w', encoding='utf-8') as f:
                json.dump(chat_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения чата: {e}")
    
    def get_messages_since(self, last_timestamp: str = None) -> List[Dict]:
        """Получение сообщений после указанного времени"""
        chat_data = self.load_chat()
        messages = chat_data.get("messages", [])
        
        if last_timestamp:
            return [m for m in messages if m.get("timestamp", "") > last_timestamp]
        return messages
    
    def format_chat_for_ai(self) -> str:
        """Форматирование чата для отправки в AI (в .txt формате)"""
        chat_data = self.load_chat()
        messages = chat_data.get("messages", [])
        
        formatted_text = []
        formatted_text.append("=== ОБЩИЙ ЧАТ ПРОЕКТА ===")
        formatted_text.append(f"Проект: {self.project_path.name}")
        formatted_text.append("")
        
        for msg in messages[-20:]:  # Последние 20 сообщений
            timestamp = msg.get("timestamp", "")[11:19]  # Только время HH:MM:SS
            sender = msg.get("sender", "Unknown")
            msg_type = msg.get("type", "text")
            content = msg.get("content", "")
            file_name = msg.get("file_name", "")
            
            formatted_text.append(f"[{timestamp}] {sender} ({msg_type}):")
            if file_name:
                formatted_text.append(f"  Файл: {file_name}")
            if content:
                formatted_text.append(f"  Сообщение: {content}")
            if msg.get("file_content"):
                file_content = msg.get("file_content")
                formatted_text.append(f"  Содержимое файла:")
                formatted_text.append("  " + "-" * 40)
                # Ограничиваем содержимое для читаемости
                content_lines = file_content.split('\n')[:30]  # Первые 30 строк
                for line in content_lines:
                    formatted_text.append(f"    {line}")
                if len(file_content.split('\n')) > 30:
                    formatted_text.append("    ... (файл обрезан)")
                formatted_text.append("  " + "-" * 40)
            formatted_text.append("")
        
        return "\n".join(formatted_text)
    
    def clear_chat(self):
        """Очистка истории чата"""
        chat_data = {
            "project": self.project_path.name,
            "created": datetime.now().isoformat(),
            "messages": [],
            "last_updated": datetime.now().isoformat()
        }
        self.save_chat(chat_data)
    
    def send_file_for_analysis(self, sender: str, file_path: str, 
                               question: str = "Проанализируй этот файл") -> bool:
        """Отправка файла на анализ в чат"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self.add_message(
                sender=sender,
                message_type="code_analysis",
                content=question,
                file_name=file_path.name,
                file_content=content
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки файла на анализ: {e}")
            return False
