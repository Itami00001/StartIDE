import speech_recognition as sr
import threading
import queue
import logging
from pathlib import Path
from typing import Optional, Callable
import tkinter as tk

class VoiceInputManager:
    """Голосовой ввод для документов в StartOffice"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.is_recording = False
        self.recording_thread = None
        self.audio_queue = queue.Queue()
        self.logger = logging.getLogger(__name__)
        
        # Callback функция для вставки текста
        self.text_callback = None
        
        # Инициализация
        self.init_voice_input()
    
    def init_voice_input(self) -> bool:
        """Инициализация микрофона для ввода текста в документ"""
        try:
            # Инициализация распознавания речи
            self.microphone = sr.Microphone()
            
            # Настройка распознавателя для фонового прослушивания
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            self.logger.info("Микрофон инициализирован для голосового ввода в документы")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации микрофона: {e}")
            return False
    
    def set_text_callback(self, callback: Callable[[str], None]):
        """Установка callback функции для вставки распознанного текста"""
        self.text_callback = callback
    
    def start_document_recording(self, text_widget=None):
        """Начать запись голоса для вставки в документ"""
        if self.is_recording:
            self.logger.warning("Запись уже идет")
            return False
        
        if not self.microphone:
            self.logger.error("Микрофон не инициализирован")
            return False
        
        # Устанавливаем callback для вставки текста
        if text_widget:
            def insert_text(text):
                if text and text_widget:
                    # Вставляем текст в текущую позицию курсора
                    current_pos = text_widget.index(tk.INSERT)
                    text_widget.insert(current_pos, text)
                    text_widget.see(tk.INSERT)
            
            self.text_callback = insert_text
        
        self.is_recording = True
        self.recording_thread = threading.Thread(target=self._record_audio, daemon=True)
        self.recording_thread.start()
        
        self.logger.info("Начата запись голоса для документа")
        return True
    
    def stop_document_recording(self) -> str:
        """Остановить запись и вставить распознанный текст в документ"""
        if not self.is_recording:
            self.logger.warning("Запись не идет")
            return ""
        
        self.is_recording = False
        
        # Ждем завершения потока записи
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=2)
        
        # Получаем аудио из очереди
        try:
            audio_data = self.audio_queue.get_nowait()
            recognized_text = self._recognize_speech(audio_data)
            
            # Вставляем текст через callback
            if recognized_text and self.text_callback:
                self.text_callback(recognized_text)
            
            self.logger.info(f"Распознан текст для документа: {recognized_text}")
            return recognized_text
            
        except queue.Empty:
            self.logger.warning("Нет аудио данных для распознавания")
            return ""
        except Exception as e:
            self.logger.error(f"Ошибка распознавания речи: {e}")
            return ""
    
    def _record_audio(self):
        """Фоновая запись аудио"""
        try:
            with self.microphone as source:
                self.logger.debug("Начало записи аудио для документа...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                self.audio_queue.put(audio)
                self.logger.debug("Аудио для документа записано и добавлено в очередь")
                
        except sr.WaitTimeoutError:
            self.logger.warning("Таймаут записи аудио для документа")
        except Exception as e:
            self.logger.error(f"Ошибка записи аудио для документа: {e}")
    
    def _recognize_speech(self, audio_data) -> str:
        """Распознавание речи из аудио данных"""
        try:
            # Распознавание с использованием Google Speech Recognition
            text = self.recognizer.recognize_google(audio_data, language="ru-RU")
            return text.strip()
            
        except sr.UnknownValueError:
            self.logger.warning("Не удалось распознать речь для документа")
            return ""
        except sr.RequestError as e:
            self.logger.error(f"Ошибка сервиса распознавания: {e}")
            return ""
        except Exception as e:
            self.logger.error(f"Ошибка распознавания речи: {e}")
            return ""
    
    def get_available_microphones(self) -> list:
        """Получение списка доступных микрофонов"""
        try:
            mic_list = sr.Microphone.list_microphone_names()
            return mic_list
        except Exception as e:
            self.logger.error(f"Ошибка получения списка микрофонов: {e}")
            return []
    
    def set_microphone(self, device_id: int = None) -> bool:
        """Установка конкретного микрофона"""
        try:
            if device_id is not None:
                self.microphone = sr.Microphone(device_index=device_id)
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                self.logger.info(f"Установлен микрофон с ID: {device_id}")
                return True
            else:
                # Использовать микрофон по умолчанию
                self.microphone = sr.Microphone()
                with self.microphone as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=1)
                self.logger.info("Установлен микрофон по умолчанию")
                return True
        except Exception as e:
            self.logger.error(f"Ошибка установки микрофона: {e}")
            return False
    
    def test_microphone(self) -> bool:
        """Тест микрофона - запись и распознавание тестовой фразы"""
        try:
            if not self.microphone:
                return False
            
            with self.microphone as source:
                self.logger.info("Тест микрофона для документов - скажите что-нибудь...")
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
                
            text = self.recognizer.recognize_google(audio, language="ru-RU")
            self.logger.info(f"Тест распознавания успешен: {text}")
            return True
            
        except sr.WaitTimeoutError:
            self.logger.warning("Таймаут теста микрофона")
            return False
        except sr.UnknownValueError:
            self.logger.warning("Тест микрофона не удался - речь не распознана")
            return False
        except Exception as e:
            self.logger.error(f"Ошибка теста микрофона: {e}")
            return False
    
    def is_available(self) -> bool:
        """Проверка доступности голосового ввода"""
        try:
            import speech_recognition
            return self.microphone is not None
        except ImportError:
            return False
    
    def get_status(self) -> dict:
        """Получение статуса голосового ввода"""
        return {
            "available": self.is_available(),
            "microphone_initialized": self.microphone is not None,
            "is_recording": self.is_recording,
            "microphones": self.get_available_microphones()
        }
    
    def cleanup(self):
        """Очистка ресурсов"""
        try:
            self.is_recording = False
            if self.recording_thread and self.recording_thread.is_alive():
                self.recording_thread.join(timeout=1)
            self.logger.info("Ресурсы VoiceInputManager освобождены")
        except Exception as e:
            self.logger.error(f"Ошибка очистки ресурсов: {e}")


# Утилиты для голосового ввода
class VoiceInputUtils:
    @staticmethod
    def is_speech_recognition_available() -> bool:
        """Проверка доступности библиотеки распознавания речи"""
        try:
            import speech_recognition
            return True
        except ImportError:
            return False
    
    @staticmethod
    def get_voice_input_requirements() -> list:
        """Получение списка необходимых зависимостей"""
        requirements = []
        
        if not VoiceInputUtils.is_speech_recognition_available():
            requirements.append("speechrecognition>=3.10.0")
        
        # PyAudio нужен для микрофона
        requirements.append("pyaudio>=0.2.11")
        
        return requirements
    
    @staticmethod
    def format_text_for_document(text: str) -> str:
        """Форматирование распознанного текста для вставки в документ"""
        if not text:
            return ""
        
        # Добавляем пробелы если нужно
        text = text.strip()
        
        # Добавляем точку в конце если нет знака препинания
        if text and text[-1] not in '.!?;,:':
            text += '.'
        
        # Делаем первую букву заглавной
        if text and len(text) > 1:
            text = text[0].upper() + text[1:]
        
        return text
    
    @staticmethod
    def create_voice_button(parent_frame, callback, text="🎤 Голосовой ввод"):
        """Создание кнопки голосового ввода"""
        try:
            import tkinter as tk
            from tkinter import ttk
            
            button = ttk.Button(parent_frame, text=text, command=callback)
            return button
        except ImportError:
            return None
