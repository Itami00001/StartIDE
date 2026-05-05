"""
Общие модули для StartIDE и Start Office
"""

from .ollama_manager import OllamaManager
from .project_context import ProjectContext
from .mongodb_manager import MongoDBManager
from .shared_chat_manager import SharedChatManager

__all__ = ['OllamaManager', 'ProjectContext', 'MongoDBManager', 'SharedChatManager']
