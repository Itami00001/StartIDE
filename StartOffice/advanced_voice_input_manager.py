import speech_recognition as sr
import threading
import queue
import time
import logging
from pathlib import Path
from typing import Optional, Callable
import tkinter as tk

class AdvancedVoiceInputManager:
    """Улучшенный голосовой ввод для документов с распознаванием в реальном времени"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.is_recording = False
        self.is_continuous = False
        self.recording_thread = None
        self.audio_queue = queue.Queue()
        self.logger = logging.getLogger(__name__)
        
        # Callback функции
        self.text_callback = None
        self.partial_text_callback = None
        
        # Настройки для русского языка
        self.language = "ru-RU"
        self.energy_threshold = 300
        self.pause_threshold = 0.6  # Более чувствительный для документов
        self.phrase_timeout = 4
        self.confidence_threshold = 0.6  # Более низкий порог для документов
        
        # Кэш и история
        self.last_partial_text = ""
        self.recognition_history = []
        self.max_history = 10
        
        # Инициализация
        self.init_voice_input()
    
    def init_voice_input(self) -> bool:
        """Инициализация микрофона с оптимизированными настройками для документов"""
        try:
            self.microphone = sr.Microphone()
            
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                self.recognizer.energy_threshold = self.energy_threshold
                self.recognizer.pause_threshold = self.pause_threshold
                self.recognizer.phrase_timeout = self.phrase_timeout
            
            self.logger.info("Улучшенный микрофон инициализирован для документов")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации микрофона: {e}")
            return False
    
    def set_text_callback(self, callback: Callable[[str], None]):
        """Установка callback для финального текста"""
        self.text_callback = callback
    
    def set_partial_text_callback(self, callback: Callable[[str], None]):
        """Установка callback для частичного распознавания в реальном времени"""
        self.partial_text_callback = callback
    
    def start_continuous_document_recording(self, text_widget=None):
        """Начать непрерывную запись для документа с реальным временем"""
        if self.is_recording:
            return False
        
        if not self.microphone:
            return False
        
        # Устанавливаем callback для текстового виджета
        if text_widget:
            def insert_partial_text(text):
                if not text or not text_widget:
                    return
                
                text_to_add = text.strip()
                if not text_to_add:
                    return
                
                # Получаем текущий текст в виджете
                current_text = text_widget.get(1.0, tk.END).strip()
                
                if not current_text:
                    # Если документ пустой, добавляем первое слово
                    text_widget.insert(tk.END, text_to_add + " ")
                else:
                    # Проверяем последнее слово для умной замены
                    words = current_text.split()
                    if words:
                        last_word = words[-1]
                        
                        # Если последнее слово короткое или похоже на распознаваемое
                        if len(last_word) <= 2 or (text_to_add.lower().startswith(last_word.lower()) and len(text_to_add) > len(last_word)):
                            # Заменяем последнее слово на более полное
                            words[-1] = text_to_add
                            new_text = " ".join(words) + " "
                            
                            # Обновляем весь текст (проще и надежнее)
                            text_widget.delete(1.0, tk.END)
                            text_widget.insert(1.0, new_text)
                        else:
                            # Добавляем новое слово с пробелом
                            text_widget.insert(tk.END, text_to_add + " ")
                    else:
                        # Добавляем как новое слово
                        text_widget.insert(tk.END, text_to_add + " ")
                
                text_widget.see(tk.END)
            
            self.set_partial_text_callback(insert_partial_text)
        
        self.is_recording = True
        self.is_continuous = True
        self.last_partial_text = ""
        self.recognition_history = []
        
        self.recording_thread = threading.Thread(target=self._continuous_document_loop, daemon=True)
        self.recording_thread.start()
        
        return True
    
    def stop_document_recording(self) -> str:
        """Остановить запись и вернуть финальный результат"""
        if not self.is_recording:
            return ""
        
        self.is_recording = False
        self.is_continuous = False
        
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=1)
        
        # Формируем финальный текст из истории
        final_text = " ".join(self.recognition_history)
        
        # Вызываем callback для финального текста
        if self.text_callback and final_text:
            self.text_callback(final_text)
        
        self.logger.info(f"Финальный текст документа: {final_text[:50]}...")
        return final_text
    
    def _continuous_document_loop(self):
        """Цикл непрерывного распознавания для документов"""
        silence_counter = 0
        max_silence = 3  # Максимальное количество пауз перед остановкой
        
        while self.is_recording:
            try:
                with self.microphone as source:
                    # Уменьшаем timeout для более быстрой реакции
                    audio = self.recognizer.listen(source, timeout=0.5, phrase_time_limit=2)
                    
                    if self.is_recording:
                        # Распознаем в отдельном потоке
                        threading.Thread(target=self._process_document_audio, args=(audio,), daemon=True).start()
                        silence_counter = 0  # Сбрасываем счетчик пауз
                        
            except sr.WaitTimeoutError:
                silence_counter += 1
                if silence_counter > max_silence:
                    # Слишком много пауз - возможно пользователь закончил
                    time.sleep(0.1)
                continue
            except Exception as e:
                self.logger.debug(f"Ошибка в цикле распознавания: {e}")
                time.sleep(0.1)
    
    def _process_document_audio(self, audio_data):
        """Обработка аудио для документов с интеллектуальным объединением"""
        try:
            text = self._recognize_with_optimization(audio_data)
            
            if text:
                # Очищаем текст от лишних пробелов и знаков
                clean_text = self._clean_text(text)
                
                if clean_text and clean_text != self.last_partial_text:
                    self.last_partial_text = clean_text
                    
                    # Добавляем в историю только если это новое слово
                    if clean_text not in self.recognition_history[-3:]:  # Избегаем повторов
                        self.recognition_history.append(clean_text)
                        
                        # Ограничиваем историю
                        if len(self.recognition_history) > self.max_history:
                            self.recognition_history.pop(0)
                    
                    # Вызываем callback для частичного результата
                    if self.partial_text_callback:
                        self.partial_text_callback(clean_text)
                        
        except Exception as e:
            self.logger.debug(f"Ошибка обработки аудио: {e}")
    
    def _recognize_with_optimization(self, audio_data) -> str:
        """Оптимизированное распознавание для документов"""
        best_text = ""
        
        # Приоритет: Google Speech Recognition с русским языком
        try:
            # Пробуем распознать с показом всех вариантов
            result = self.recognizer.recognize_google(audio_data, language=self.language, show_all=True)
            
            if isinstance(result, dict) and 'alternative' in result:
                # Выбираем лучший вариант
                best_alternative = max(result['alternative'], key=lambda x: x.get('confidence', 0))
                best_text = best_alternative['transcript']
            elif isinstance(result, str):
                best_text = result
                
        except sr.UnknownValueError:
            # Пробуем другие методы
            pass
        except sr.RequestError:
            # Если Google недоступен, пробуем Sphinx
            try:
                best_text = self.recognizer.recognize_sphinx(audio_data, language='ru')
            except:
                pass
        
        return best_text.strip() if best_text else ""
    
    def _clean_text(self, text: str) -> str:
        """Очистка и форматирование текста для документов"""
        if not text:
            return ""
        
        # Убираем лишние пробелы
        text = " ".join(text.split())
        
        # Убираем знаки препинания в конце (для отдельных слов)
        if len(text.split()) == 1 and text[-1] in ".,!?;:":
            text = text[:-1]
        
        # Делаем первую букву заглавной если это начало предложения
        if not self.recognition_history or self.recognition_history[-1].endswith(('.','!','?')):
            text = text.capitalize()
        
        return text
    
    def get_recognition_suggestions(self) -> list:
        """Получить предложения по улучшению распознавания"""
        suggestions = []
        
        if self.energy_threshold > 500:
            suggestions.append("Слишком шумно. Попробуйте говорить громче или уменьшите шум.")
        
        if self.pause_threshold > 1.0:
            suggestions.append("Увеличьте чувствительность в настройках.")
        
        if len(self.recognition_history) == 0:
            suggestions.append("Говорите четче и ближе к микрофону.")
        
        return suggestions
    
    def set_language(self, language_code: str):
        """Установка языка распознавания"""
        self.language = language_code
        self.logger.info(f"Установлен язык: {language_code}")
    
    def set_sensitivity(self, level: float):
        """Настройка чувствительности (0.0 - 1.0)"""
        # Для документов используем более низкий порог
        self.energy_threshold = 200 + (1.0 - level) * 300
        self.recognizer.energy_threshold = self.energy_threshold
        self.pause_threshold = 0.4 + (1.0 - level) * 0.4
        self.recognizer.pause_threshold = self.pause_threshold
        
        self.logger.info(f"Чувствительность установлена: {level}, порог: {self.energy_threshold}")
    
    def auto_adjust_sensitivity(self):
        """Автоматическая подстройка чувствительности"""
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                self.energy_threshold = self.recognizer.energy_threshold
                
                # Автоматическая настройка pause_threshold
                if self.energy_threshold < 200:
                    self.pause_threshold = 0.4
                elif self.energy_threshold < 400:
                    self.pause_threshold = 0.6
                else:
                    self.pause_threshold = 0.8
                
                self.recognizer.pause_threshold = self.pause_threshold
                
                self.logger.info(f"Автонастройка: порог={self.energy_threshold}, пауза={self.pause_threshold}")
                
        except Exception as e:
            self.logger.error(f"Ошибка автоподстройки: {e}")
    
    def get_current_text(self) -> str:
        """Получить текущий распознанный текст"""
        return " ".join(self.recognition_history)
    
    def clear_history(self):
        """Очистить историю распознавания"""
        self.recognition_history = []
        self.last_partial_text = ""
    
    def undo_last_word(self):
        """Отменить последнее слово"""
        if self.recognition_history:
            removed_word = self.recognition_history.pop()
            self.last_partial_text = ""
            
            # Вызываем callback для обновления
            if self.text_callback:
                self.text_callback(" ".join(self.recognition_history))
            
            return removed_word
        return ""
    
    def get_status(self) -> dict:
        """Получить статус голосового ввода"""
        return {
            "is_recording": self.is_recording,
            "is_continuous": self.is_continuous,
            "language": self.language,
            "energy_threshold": self.energy_threshold,
            "pause_threshold": self.pause_threshold,
            "words_count": len(self.recognition_history),
            "last_word": self.recognition_history[-1] if self.recognition_history else "",
            "suggestions": self.get_recognition_suggestions()
        }
    
    def test_recognition_quality(self) -> dict:
        """Тест качества распознавания"""
        try:
            if not self.microphone:
                return {"available": False, "error": "Микрофон не инициализирован"}
            
            results = {"available": True, "tests": []}
            
            # Тест распознавания цифр
            test_numbers = ["один", "два", "три"]
            recognized_numbers = []
            
            for number in test_numbers:
                try:
                    with self.microphone as source:
                        self.logger.info(f"Скажите: {number}")
                        audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=2)
                        
                    recognized = self._recognize_with_optimization(audio)
                    recognized_numbers.append(recognized.lower())
                    
                except:
                    recognized_numbers.append("ошибка")
            
            # Оценка качества
            correct_count = sum(1 for i, num in enumerate(test_numbers) 
                             if num in recognized_numbers[i])
            
            quality_score = correct_count / len(test_numbers)
            
            results["tests"].append({
                "name": "Распознавание цифр",
                "expected": test_numbers,
                "recognized": recognized_numbers,
                "score": quality_score,
                "quality": "Отличное" if quality_score >= 0.8 else "Хорошее" if quality_score >= 0.6 else "Плохое"
            })
            
            return results
            
        except Exception as e:
            return {"available": False, "error": str(e)}
    
    def cleanup(self):
        """Очистка ресурсов"""
        try:
            self.is_recording = False
            self.is_continuous = False
            
            if self.recording_thread and self.recording_thread.is_alive():
                self.recording_thread.join(timeout=1)
            
            self.logger.info("Ресурсы AdvancedVoiceInputManager освобождены")
        except Exception as e:
            self.logger.error(f"Ошибка очистки ресурсов: {e}")


# Утилиты для голосового ввода документов
class DocumentVoiceUtils:
    @staticmethod
    def format_text_for_document(text: str) -> str:
        """Форматирование текста для вставки в документ"""
        if not text:
            return ""
        
        # Основные правила форматирования
        text = text.strip()
        
        # Добавляем пробелы между словами если нужно
        words = text.split()
        if len(words) > 1:
            formatted_text = " ".join(words)
        else:
            formatted_text = words[0] if words else ""
        
        # Добавляем точку в конце если это конец предложения
        if formatted_text and len(formatted_text) > 1:
            if formatted_text[-1] not in '.!?;,:':
                # Проверяем, не является ли это последним словом в предложении
                if formatted_text.lower() in ['и', 'в', 'на', 'с', 'по', 'к', 'от', 'для', 'о', 'об']:
                    formatted_text += " "
                else:
                    formatted_text += ". "
        
        return formatted_text
    
    @staticmethod
    def get_document_voice_settings() -> dict:
        """Оптимальные настройки для голосового ввода документов"""
        return {
            "language": "ru-RU",
            "energy_threshold": 250,
            "pause_threshold": 0.6,
            "phrase_timeout": 3,
            "confidence_threshold": 0.6,
            "sensitivity": 0.8,
            "max_silence_pauses": 3
        }
    
    @staticmethod
    def create_voice_toolbar(parent_frame, start_callback, stop_callback, status_callback=None):
        """Создание панели инструментов для голосового ввода"""
        try:
            import tkinter as tk
            from tkinter import ttk
            
            toolbar = ttk.Frame(parent_frame)
            
            # Кнопка записи
            record_btn = ttk.Button(toolbar, text="🎤 Начать запись", command=start_callback)
            record_btn.pack(side=tk.LEFT, padx=2)
            
            # Кнопка остановки
            stop_btn = ttk.Button(toolbar, text="⏹️ Остановить", command=stop_callback)
            stop_btn.pack(side=tk.LEFT, padx=2)
            
            # Статус
            if status_callback:
                status_label = ttk.Label(toolbar, text="Готов к записи")
                status_label.pack(side=tk.LEFT, padx=5)
                
                def update_status(text):
                    status_label.config(text=text)
                
                return toolbar, update_status
            
            return toolbar, None
            
        except ImportError:
            return None, None
