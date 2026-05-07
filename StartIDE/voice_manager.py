import speech_recognition as sr
import pyttsx3
import tempfile
import threading
import queue
import logging
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime

class VoiceManager:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.engine = None
        self.is_recording = False
        self.recording_thread = None
        self.audio_queue = queue.Queue()
        self.logger = logging.getLogger(__name__)

        # Callback функция для обработки распознанного текста
        self.text_callback = None

        # Инициализация
        self.init_voice_input()

    def init_voice_input(self) -> bool:
        """Инициализация микрофона для AI чата"""
        try:
            # Инициализация распознавания речи
            self.microphone = sr.Microphone()

            # Настройка распознавателя для фонового прослушивания
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)

            self.logger.info("Микрофон инициализирован для голосового ввода")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка инициализации микрофона: {e}")
            return False

    def init_text_to_speech(self) -> bool:
        """Инициализация синтезатора речи"""
        try:
            self.engine = pyttsx3.init()

            # Настройка голоса
            voices = self.engine.getProperty('voices')
            if voices:
                # Выбираем русский голос если доступен
                for voice in voices:
                    if 'russian' in voice.id.lower() or 'ru' in voice.id.lower():
                        self.engine.setProperty('voice', voice.id)
                        break

            # Настройка скорости и громкости
            self.engine.setProperty('rate', 150)  # Скорость речи
            self.engine.setProperty('volume', 0.9)  # Громкость

            self.logger.info("Синтезатор речи инициализирован")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка инициализации синтезатора речи: {e}")
            return False

    def set_text_callback(self, callback: Callable[[str], None]):
        """Установка callback функции для обработки распознанного текста"""
        self.text_callback = callback

    def start_recording(self, callback_func: Optional[Callable[[str], None]] = None):
        """Начать запись голоса для AI"""
        if self.is_recording:
            self.logger.warning("Запись уже идет")
            return

        if not self.microphone:
            self.logger.error("Микрофон не инициализирован")
            return

        # Устанавливаем callback
        if callback_func:
            self.text_callback = callback_func

        self.is_recording = True
        self.recording_thread = threading.Thread(target=self._record_audio, daemon=True)
        self.recording_thread.start()

        self.logger.info("Начата запись голоса")

    def stop_recording(self) -> str:
        """Остановить запись и распознать речь для AI"""
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

            if recognized_text and self.text_callback:
                self.text_callback(recognized_text)

            self.logger.info(f"Распознан текст: {recognized_text}")
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
                self.logger.debug("Начало записи аудио...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                self.audio_queue.put(audio)
                self.logger.debug("Аудио записано и добавлено в очередь")

        except sr.WaitTimeoutError:
            self.logger.warning("Таймаут записи аудио")
        except Exception as e:
            self.logger.error(f"Ошибка записи аудио: {e}")

    def _recognize_speech(self, audio_data) -> str:
        """Распознавание речи из аудио данных"""
        try:
            # Распознавание с использованием Google Speech Recognition
            text = self.recognizer.recognize_google(audio_data, language="ru-RU")
            return text.strip()

        except sr.UnknownValueError:
            self.logger.warning("Не удалось распознать речь")
            return ""
        except sr.RequestError as e:
            self.logger.error(f"Ошибка сервиса распознавания: {e}")
            return ""
        except Exception as e:
            self.logger.error(f"Ошибка распознавания речи: {e}")
            return ""

    def text_to_speech(self, text: str, output_file: str = None) -> bool:
        """Преобразование AI ответа в речь"""
        try:
            if not self.engine:
                if not self.init_text_to_speech():
                    return False

            if output_file:
                # Сохранение в файл
                self.engine.save_to_file(text, output_file)
                self.engine.runAndWait()
                self.logger.info(f"Речь сохранена в файл: {output_file}")
            else:
                # Воспроизведение
                self.engine.say(text)
                self.engine.runAndWait()
                self.logger.info("Речь воспроизведена")

            return True

        except Exception as e:
            self.logger.error(f"Ошибка синтеза речи: {e}")
            return False

    def text_to_speech_async(self, text: str, output_file: str = None):
        """Асинхронное преобразование текста в речь"""
        def tts_worker():
            self.text_to_speech(text, output_file)

        thread = threading.Thread(target=tts_worker, daemon=True)
        thread.start()

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
                self.logger.info("Тест микрофона - скажите что-нибудь...")
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

    def record_voice_message(self, project_id: int, chat_manager, output_dir: str = None) -> str:
        """Запись голосового сообщения для чата"""
        try:
            if not self.microphone:
                self.logger.error("Микрофон не инициализирован")
                return None

            # Создаем временную директорию для голосовых файлов
            if output_dir is None:
                output_dir = Path("context/voice_messages")
            else:
                output_dir = Path(output_dir)

            output_dir.mkdir(parents=True, exist_ok=True)

            # Записываем аудио
            with self.microphone as source:
                self.logger.info("Запись голосового сообщения...")
                audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=30)

            # Сохраняем аудио файл
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_file = output_dir / f"voice_msg_{project_id}_{timestamp}.wav"

            # Сохранение аудио в файл
            with audio_file.open("wb") as f:
                f.write(audio.get_wav_data())

            # Распознаем текст
            recognized_text = self._recognize_speech(audio)

            if recognized_text:
                # Добавляем сообщение в чат
                chat_manager.add_message(
                    project_id=project_id,
                    sender="StartIDE",
                    message_type="voice",
                    content=recognized_text,
                    voice_file_path=str(audio_file)
                )

                self.logger.info(f"Голосовое сообщение сохранено: {audio_file}")
                return str(audio_file)
            else:
                # Удаляем файл если распознавание не удалось
                if audio_file.exists():
                    audio_file.unlink()
                self.logger.warning("Не удалось распознать голосовое сообщение")
                return None

        except Exception as e:
            self.logger.error(f"Ошибка записи голосового сообщения: {e}")
            return None

    def play_voice_response(self, text: str, project_id: int, output_dir: str = None) -> str:
        """Преобразование AI ответа в речь и сохранение"""
        try:
            if not self.engine:
                if not self.init_text_to_speech():
                    return None

            # Создаем директорию для голосовых ответов
            if output_dir is None:
                output_dir = Path("context/voice_responses")
            else:
                output_dir = Path(output_dir)

            output_dir.mkdir(parents=True, exist_ok=True)

            # Создаем файл для ответа
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            response_file = output_dir / f"ai_response_{project_id}_{timestamp}.wav"

            # Генерируем речь
            self.text_to_speech(text, str(response_file))

            self.logger.info(f"Голосовой ответ сохранен: {response_file}")
            return str(response_file)

        except Exception as e:
            self.logger.error(f"Ошибка генерации голосового ответа: {e}")
            return None

    def cleanup(self):
        """Очистка ресурсов"""
        try:
            if self.engine:
                self.engine.stop()
            self.logger.info("Ресурсы VoiceManager освобождены")
        except Exception as e:
            self.logger.error(f"Ошибка очистки ресурсов: {e}")


# Утилиты для работы с голосом
class VoiceUtils:
    @staticmethod
    def is_speech_recognition_available() -> bool:
        """Проверка доступности библиотеки распознавания речи"""
        try:
            import speech_recognition
            return True
        except ImportError:
            return False

    @staticmethod
    def is_text_to_speech_available() -> bool:
        """Проверка доступности библиотеки синтеза речи"""
        try:
            import pyttsx3
            return True
        except ImportError:
            return False

    @staticmethod
    def get_voice_requirements() -> list:
        """Получение списка необходимых зависимостей"""
        requirements = []

        if not VoiceUtils.is_speech_recognition_available():
            requirements.append("speechrecognition>=3.10.0")

        if not VoiceUtils.is_text_to_speech_available():
            requirements.append("pyttsx3>=2.90")

        if not requirements:
            requirements.append("pyaudio>=0.2.11")  # Для микрофона

        return requirements
