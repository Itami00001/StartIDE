import speech_recognition as sr
import pyttsx3
import threading
import queue
import time
import logging
from pathlib import Path
from typing import Optional, Callable
import tkinter as tk

class AdvancedVoiceManager:
    """Улучшенный голосовой менеджер с распознаванием в реальном времени"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.engine = None
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
        self.alternative_languages = ["ru-RU", "en-US"]
        
        # Параметры распознавания
        self.energy_threshold = 300
        self.pause_threshold = 0.8
        self.phrase_timeout = 5
        self.non_speaking_duration = 0.5
        
        # Кэш для частичных результатов
        self.last_partial_text = ""
        self.confidence_threshold = 0.7
        
        # Инициализация
        self.init_voice_input()
    
    def init_voice_input(self) -> bool:
        """Инициализация микрофона с улучшенными настройками"""
        try:
            # Инициализация распознавания речи
            self.microphone = sr.Microphone()
            
            # Настройка распознавателя для русского языка
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                self.recognizer.energy_threshold = self.energy_threshold
                self.recognizer.pause_threshold = self.pause_threshold
                self.recognizer.phrase_timeout = self.phrase_timeout
                self.recognizer.non_speaking_duration = self.non_speaking_duration
            
            self.logger.info("Улучшенный микрофон инициализирован для русского языка")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации микрофона: {e}")
            return False
    
    def init_text_to_speech(self) -> bool:
        """Инициализация синтезатора речи с русским голосом"""
        try:
            self.engine = pyttsx3.init()
            
            # Настройка русского голоса
            voices = self.engine.getProperty('voices')
            russian_voice = None
            
            for voice in voices:
                if 'russian' in voice.id.lower() or 'ru' in voice.id.lower():
                    russian_voice = voice
                    break
            
            if russian_voice:
                self.engine.setProperty('voice', russian_voice.id)
            elif voices:
                # Если русского нет, используем первый доступный
                self.engine.setProperty('voice', voices[0].id)
            
            # Настройка параметров
            self.engine.setProperty('rate', 150)  # Скорость
            self.engine.setProperty('volume', 0.9)  # Громкость
            
            self.logger.info("Синтезатор речи инициализирован")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации синтезатора речи: {e}")
            return False
    
    def set_text_callback(self, callback: Callable[[str], None]):
        """Установка callback для финального текста"""
        self.text_callback = callback
    
    def set_partial_text_callback(self, callback: Callable[[str], None]):
        """Установка callback для частичного распознавания"""
        self.partial_text_callback = callback
    
    def start_continuous_recording(self, text_widget=None):
        """Начать непрерывную запись с распознаванием в реальном времени"""
        if self.is_recording:
            self.logger.warning("Запись уже идет")
            return False
        
        if not self.microphone:
            self.logger.error("Микрофон не инициализирован")
            return False
        
        # Устанавливаем callback для текстового виджета
        if text_widget:
            def insert_text(text):
                if text and text_widget:
                    # Вставляем текст в текущую позицию
                    current_pos = text_widget.index(tk.INSERT)
                    text_widget.insert(current_pos, text)
                    text_widget.see(tk.INSERT)
            
            self.set_text_callback(insert_text)
        
        self.is_recording = True
        self.is_continuous = True
        self.recording_thread = threading.Thread(target=self._continuous_recognition_loop, daemon=True)
        self.recording_thread.start()
        
        self.logger.info("Начата непрерывная запись с распознаванием в реальном времени")
        return True
    
    def stop_recording(self) -> str:
        """Остановить запись и вернуть финальный результат"""
        if not self.is_recording:
            return ""
        
        self.is_recording = False
        self.is_continuous = False
        
        # Ждем завершения потока
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=1)
        
        # Получаем финальный результат
        try:
            if not self.audio_queue.empty():
                audio_data = self.audio_queue.get_nowait()
                final_text = self._recognize_speech_with_confidence(audio_data)
                self.logger.info(f"Финальный распознанный текст: {final_text}")
                return final_text
        except queue.Empty:
            pass
        
        return self.last_partial_text
    
    def _continuous_recognition_loop(self):
        """Основной цикл непрерывного распознавания"""
        while self.is_recording:
            try:
                with self.microphone as source:
                    self.logger.debug("Слушаем аудио...")
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=self.phrase_timeout)
                    
                    if self.is_recording:  # Проверяем что не остановили во время прослушивания
                        self.audio_queue.put(audio)
                        
                        # Распознаем в отдельном потоке для реального времени
                        threading.Thread(target=self._process_audio_chunk, args=(audio,), daemon=True).start()
                        
            except sr.WaitTimeoutError:
                continue  # Нормально для непрерывного режима
            except Exception as e:
                self.logger.error(f"Ошибка в цикле распознавания: {e}")
                time.sleep(0.1)
    
    def _process_audio_chunk(self, audio_data):
        """Обработка аудио чанка с распознаванием"""
        try:
            # Пробуем разные методы распознавания для лучшего качества
            text = self._recognize_with_multiple_methods(audio_data)
            
            if text and text != self.last_partial_text:
                self.last_partial_text = text
                
                # Вызываем callback для частичного результата
                if self.partial_text_callback:
                    self.partial_text_callback(text)
                
        except Exception as e:
            self.logger.debug(f"Ошибка обработки аудио: {e}")
    
    def _recognize_with_multiple_methods(self, audio_data) -> str:
        """Распознавание несколькими методами для лучшего качества"""
        best_text = ""
        best_confidence = 0
        
        # Метод 1: Google Speech Recognition (основной)
        try:
            text = self.recognizer.recognize_google(audio_data, language=self.language, show_all=True)
            if isinstance(text, dict) and 'alternative' in text:
                for alt in text['alternative']:
                    confidence = alt.get('confidence', 0)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_text = alt['transcript']
            elif isinstance(text, str):
                best_text = text
                best_confidence = 0.8  # Стандартная уверенность
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            self.logger.warning(f"Google Speech недоступен: {e}")
        
        # Метод 2: Sphinx (оффлайн, если Google недоступен)
        if not best_text:
            try:
                text = self.recognizer.recognize_sphinx(audio_data, language='ru-ru')
                if text:
                    best_text = text
                    best_confidence = 0.6
            except:
                pass
        
        # Метод 3: Попробовать английский если русский не сработал
        if not best_text:
            try:
                text = self.recognizer.recognize_google(audio_data, language="en-US")
                if text:
                    best_text = text
                    best_confidence = 0.5
            except:
                pass
        
        return best_text.strip() if best_text else ""
    
    def _recognize_speech_with_confidence(self, audio_data) -> str:
        """Распознавание с проверкой уверенности"""
        try:
            result = self.recognizer.recognize_google(audio_data, language=self.language, show_all=True)
            
            if isinstance(result, dict) and 'alternative' in result:
                # Выбираем лучший вариант по уверенности
                best_alternative = max(result['alternative'], key=lambda x: x.get('confidence', 0))
                confidence = best_alternative.get('confidence', 0)
                text = best_alternative['transcript']
                
                if confidence >= self.confidence_threshold:
                    return text.strip()
                else:
                    self.logger.warning(f"Низкая уверенность распознавания: {confidence}")
                    return text.strip()  # Все равно возвращаем
            
            elif isinstance(result, str):
                return result.strip()
                
        except sr.UnknownValueError:
            self.logger.warning("Речь не распознана")
        except sr.RequestError as e:
            self.logger.error(f"Ошибка сервиса распознавания: {e}")
        
        return ""
    
    def text_to_speech(self, text: str, output_file: str = None) -> bool:
        """Преобразование текста в речь"""
        try:
            if not self.engine:
                if not self.init_text_to_speech():
                    return False
            
            if output_file:
                self.engine.save_to_file(text, output_file)
                self.engine.runAndWait()
            else:
                self.engine.say(text)
                self.engine.runAndWait()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка синтеза речи: {e}")
            return False
    
    def text_to_speech_async(self, text: str, output_file: str = None):
        """Асинхронное преобразование текста в речь"""
        def tts_worker():
            self.text_to_speech(text, output_file)
        
        threading.Thread(target=tts_worker, daemon=True).start()
    
    def adjust_for_environment(self):
        """Автоматическая подстройка под окружение"""
        try:
            if not self.microphone:
                return False
            
            with self.microphone as source:
                # Измеряем уровень шума
                self.recognizer.adjust_for_ambient_noise(source, duration=3)
                self.energy_threshold = self.recognizer.energy_threshold
                
                self.logger.info(f"Настроен порог энергии: {self.energy_threshold}")
                return True
                
        except Exception as e:
            self.logger.error(f"Ошибка настройки окружения: {e}")
            return False
    
    def set_language(self, language_code: str):
        """Установка языка распознавания"""
        self.language = language_code
        self.logger.info(f"Установлен язык: {language_code}")
    
    def set_sensitivity(self, sensitivity: float):
        """Настройка чувствительности (0.0 - 1.0)"""
        # Чем ниже sensitivity, тем ниже energy_threshold
        self.energy_threshold = 100 + (1.0 - sensitivity) * 400
        self.recognizer.energy_threshold = self.energy_threshold
        self.logger.info(f"Установлена чувствительность: {sensitivity}, порог: {self.energy_threshold}")
    
    def get_recognition_stats(self) -> dict:
        """Получение статистики распознавания"""
        return {
            "energy_threshold": self.energy_threshold,
            "pause_threshold": self.pause_threshold,
            "language": self.language,
            "is_recording": self.is_recording,
            "is_continuous": self.is_continuous,
            "last_partial_text": self.last_partial_text
        }
    
    def test_microphone_quality(self) -> dict:
        """Тест качества микрофона"""
        try:
            if not self.microphone:
                return {"available": False, "error": "Микрофон не инициализирован"}
            
            results = {"available": True, "tests": []}
            
            # Тест 1: Тихое окружение
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                ambient_level = self.recognizer.energy_threshold
                results["tests"].append({
                    "name": "Уровень шума окружения",
                    "value": ambient_level,
                    "status": "OK" if ambient_level < 500 else "ШУМНО"
                })
            
            # Тест 2: Распознавание тестовой фразы
            test_phrase = "тест распознавания речи"
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=5)
                
            try:
                recognized = self.recognizer.recognize_google(audio, language=self.language)
                results["tests"].append({
                    "name": "Распознавание тестовой фразы",
                    "expected": test_phrase,
                    "recognized": recognized,
                    "status": "OK" if test_phrase.lower() in recognized.lower() else "ПЛОХО"
                })
            except:
                results["tests"].append({
                    "name": "Распознавание тестовой фразы",
                    "status": "ОШИБКА"
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
            
            if self.engine:
                self.engine.stop()
            
            self.logger.info("Ресурсы AdvancedVoiceManager освобождены")
        except Exception as e:
            self.logger.error(f"Ошибка очистки ресурсов: {e}")


# Утилиты для улучшенного голосового ввода
class AdvancedVoiceUtils:
    @staticmethod
    def get_optimal_settings() -> dict:
        """Получение оптимальных настроек для русского языка"""
        return {
            "language": "ru-RU",
            "energy_threshold": 300,
            "pause_threshold": 0.8,
            "phrase_timeout": 5,
            "confidence_threshold": 0.7,
            "sensitivity": 0.7
        }
    
    @staticmethod
    def check_microphone_quality() -> dict:
        """Проверка качества микрофона"""
        try:
            recognizer = sr.Recognizer()
            microphone = sr.Microphone()
            
            with microphone as source:
                # Измеряем уровень шума
                recognizer.adjust_for_ambient_noise(source, duration=2)
                noise_level = recognizer.energy_threshold
                
                return {
                    "available": True,
                    "noise_level": noise_level,
                    "quality": "Хорошее" if noise_level < 300 else "Среднее" if noise_level < 600 else "Плохое",
                    "recommendation": "Используйте в тихом помещении" if noise_level > 500 else "Условия приемлемые"
                }
        except Exception as e:
            return {"available": False, "error": str(e)}
    
    @staticmethod
    def get_supported_languages() -> list:
        """Получение поддерживаемых языков"""
        return [
            {"code": "ru-RU", "name": "Русский", "quality": "Высокое"},
            {"code": "en-US", "name": "English", "quality": "Высокое"},
            {"code": "de-DE", "name": "Deutsch", "quality": "Среднее"},
            {"code": "fr-FR", "name": "Français", "quality": "Среднее"},
            {"code": "es-ES", "name": "Español", "quality": "Среднее"},
            {"code": "it-IT", "name": "Italiano", "quality": "Среднее"}
        ]
