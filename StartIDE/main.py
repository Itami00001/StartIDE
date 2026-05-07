import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import sys
import os
from pathlib import Path
import threading
import logging
from typing import Dict

# Добавляем путь к shared модулям
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.ollama_manager import OllamaManager
from shared.project_context import ProjectContext
from shared.chat_manager import ChatManager
from shared.database_manager import DatabaseManager
from shared.git_manager import GitManager
from shared.app_logger import AppLogger
from shared.project_manager import ProjectManager
from shared.file_tracker import FileTracker

# Опциональный импорт голосового менеджера
try:
    from StartIDE.voice_manager import VoiceManager
    from StartIDE.advanced_voice_manager import AdvancedVoiceManager
    from StartIDE.project_manager_window import ProjectManagerWindow
    VOICE_AVAILABLE = True
    ADVANCED_VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False
    ADVANCED_VOICE_AVAILABLE = False
    VoiceManager = None
    AdvancedVoiceManager = None

class StartIDE:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("StartIDE")
        self.root.geometry("1200x800")

        # Цветовая палитра темы
        self.colors = {
            "lavender":   "#AB92BF",
            "plum":       "#655A7C",
            "cream":      "#FDF1E2",
            "cream_soft": "#FFF8EF",
            "ink":        "#25212D",
            "muted":      "#766E83",
            "white":      "#FFFFFF",
            "accent":     "#C9B6D9",
            "success":    "#4E8B66",
            "warning":    "#C58B3B",
            "danger":     "#B85B5B",
            "panel_bg":   "#2D2640",
            "panel_fg":   "#EDE8F5",
        }

        # Переменные проекта
        self.project_path = None
        self.ollama_manager = None
        self.project_context = None
        self.shared_chat_manager = None
        self.last_chat_timestamp = None

        # Новая система баз данных
        self.db_manager = None
        self.git_manager = None
        self.current_project_id = None
        self.chat_manager = None

        # Голосовой менеджер для AI чата
        self.voice_manager = None
        self.advanced_voice_manager = None

        # Управление проектами и файлами
        self.project_manager = None
        self.file_tracker = None

        # Разделенное логирование
        self.app_logger = None

        # Настройка логирования
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Инициализация новой системы баз данных
        self.init_database()

        # Создание интерфейса
        self.setup_ui()

        # Горячие клавиши — после создания всех виджетов
        self.setup_hotkeys()

        # Попытка подключения к Ollama
        self.init_ollama()

        # Минимальный размер окна
        self.root.minsize(1100, 700)

    def setup_ui(self):
        """Создание интерфейса"""
        self.apply_theme()
        # Главное меню
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Файл меню
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Новый проект", command=self.new_project)
        file_menu.add_command(label="Открыть проект", command=self.open_project)
        file_menu.add_separator()
        file_menu.add_command(label="Сохранить файл", command=self.save_current_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Сохранить как...", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.quit_app)

        # Проект меню
        project_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Проект", menu=project_menu)
        project_menu.add_command(label="📋 Управление проектами", command=self.open_project_manager)
        project_menu.add_command(label="📁 Управление файлами", command=self.open_file_manager)
        project_menu.add_separator()
        project_menu.add_command(label="🔍 Автообнаружение файлов", command=self.auto_discover_files)
        project_menu.add_command(label="📊 Статистика проекта", command=self.show_project_stats)
        project_menu.add_separator()
        project_menu.add_command(label="🔬 Анализ стека технологий", command=self.extract_and_save_tech_stack)

        # Виджет меню
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Вид", menu=view_menu)
        view_menu.add_command(label="Показать/Скрыть Нейро", command=self.toggle_neuro_panel)

        # Основная панель
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)

        # Левая панель (проводник файлов + отслеживание)
        self.left_frame = ttk.Frame(main_paned, width=300)
        main_paned.add(self.left_frame, weight=1)

        # Центральная панель (редактор)
        self.center_frame = ttk.Frame(main_paned)
        main_paned.add(self.center_frame, weight=3)

        # Правая панель (Нейро)
        self.right_frame = ttk.Frame(main_paned, width=300)
        main_paned.add(self.right_frame, weight=1)

        self.setup_file_explorer()
        self.setup_editor()
        self.setup_neuro_panel()

        # Улучшенный статус-бар с индикаторами
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        # Основной статус
        self.status_bar = ttk.Label(status_frame, text="Готов к работе", style="Status.TLabel")
        self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Индикатор проекта
        self.project_status_label = ttk.Label(status_frame, text="📁 Нет проекта", foreground="gray")
        self.project_status_label.pack(side=tk.LEFT, padx=5)

        # Индикатор Git
        self.git_status_indicator = ttk.Label(status_frame, text="🌿 -", foreground="gray")
        self.git_status_indicator.pack(side=tk.LEFT, padx=5)

        # Индикатор AI
        self.ai_status_indicator = ttk.Label(status_frame, text="🤖 -", foreground="gray")
        self.ai_status_indicator.pack(side=tk.LEFT, padx=5)

        # Индикатор голосового ввода
        self.voice_status_indicator = ttk.Label(status_frame, text="🎤 -", foreground="gray")
        self.voice_status_indicator.pack(side=tk.LEFT, padx=5)

        # Применяем тему после создания всех виджетов
        self.root.after(50, self.apply_theme)

    def setup_file_explorer(self):
        """Настройка проводника файлов с панелью отслеживания"""
        # Создаем вертикальную панель для разделения
        left_paned = ttk.PanedWindow(self.left_frame, orient=tk.VERTICAL)
        left_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Верхняя панель - проводник файлов
        file_frame = ttk.Frame(left_paned)
        left_paned.add(file_frame, weight=2)

        # Нижняя панель - отслеживание
        tracking_frame = ttk.Frame(left_paned)
        left_paned.add(tracking_frame, weight=1)

        # Настройка проводника файлов
        ttk.Label(file_frame, text="📁 Проводник", font=("Segoe UI", 11, "bold")).pack(pady=6)

        self.file_tree = ttk.Treeview(file_frame, columns=("size", "type"), show="tree")
        self.file_tree.heading("#0", text="Файлы")
        self.file_tree.column("#0", width=200)
        self.file_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Контекстное меню
        self.file_tree.bind("<Button-3>", self.show_file_context_menu)
        self.file_tree.bind("<Double-1>", self.open_file_in_editor)

        # Кнопки управления файлами
        file_button_frame = ttk.Frame(file_frame)
        file_button_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(file_button_frame, text="📄 Файл", command=self.create_file, style="Accent.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(file_button_frame, text="📁 Папка", command=self.create_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(file_button_frame, text="🔄", command=self.refresh_file_tree).pack(side=tk.LEFT, padx=2)

        # Настройка панели отслеживания
        self.setup_tracking_panel(tracking_frame)

    def setup_tracking_panel(self, parent_frame):
        """Настройка панели отслеживания проекта"""
        # Заголовок
        ttk.Label(parent_frame, text="🔍 Отслеживание", font=("Segoe UI", 11, "bold")).pack(pady=6)

        # Создаем notebook для вкладок
        self.tracking_notebook = ttk.Notebook(parent_frame)
        self.tracking_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Вкладка отслеживания файлов
        files_tab = ttk.Frame(self.tracking_notebook)
        self.tracking_notebook.add(files_tab, text="📄 Файлы")

        # Список отслеживаемых файлов
        self.tracking_listbox = tk.Listbox(files_tab, font=("Segoe UI", 9), relief=tk.FLAT, borderwidth=0)
        self.tracking_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Кнопки управления отслеживанием
        tracking_button_frame = ttk.Frame(files_tab)
        tracking_button_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(tracking_button_frame, text="➕ Добавить", command=self.add_file_to_tracking).pack(side=tk.LEFT, padx=2)
        ttk.Button(tracking_button_frame, text="➖ Удалить", command=self.remove_file_from_tracking).pack(side=tk.LEFT, padx=2)
        ttk.Button(tracking_button_frame, text="🔄 Обновить", command=self.refresh_tracking_list).pack(side=tk.LEFT, padx=2)

        # Вкладка статистики
        stats_tab = ttk.Frame(self.tracking_notebook)
        self.tracking_notebook.add(stats_tab, text="📊 Статистика")

        # Текстовое поле для статистики
        self.stats_text = scrolledtext.ScrolledText(stats_tab, height=8, font=("Segoe UI", 9), relief=tk.FLAT)
        self.stats_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.stats_text.config(state=tk.DISABLED)

        # Вкладка Git
        git_tab = ttk.Frame(self.tracking_notebook)
        self.tracking_notebook.add(git_tab, text="🌿 Git")

        # Текстовое поле для Git информации
        self.git_text = scrolledtext.ScrolledText(git_tab, height=8, font=("Segoe UI", 9), relief=tk.FLAT)
        self.git_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.git_text.config(state=tk.DISABLED)

        # Кнопка обновления Git
        ttk.Button(git_tab, text="🔄 Обновить Git", command=self.update_git_info).pack(pady=5)

    def setup_editor(self):
        """Настройка редактора кода"""
        # Заголовок
        ttk.Label(self.center_frame, text="Редактор кода", font=("Arial", 10, "bold")).pack(pady=5)

        # Текстовый редактор
        self.editor_frame = ttk.Frame(self.center_frame)
        self.editor_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Создаем Notebook для редактора и чата
        self.center_notebook = ttk.Notebook(self.editor_frame)
        self.center_notebook.pack(fill=tk.BOTH, expand=True)

        # Вкладка редактора
        self.editor_tab = ttk.Frame(self.center_notebook)
        self.center_notebook.add(self.editor_tab, text="📝 Редактор")

        # Вкладка общего чата
        self.chat_tab = ttk.Frame(self.center_notebook)
        self.center_notebook.add(self.chat_tab, text="💬 Общий чат")

        self.setup_editor_tab()
        self.setup_chat_tab()

        # Информация о файле
        self.file_info_label = ttk.Label(self.center_frame, text="Файл не открыт")
        self.file_info_label.pack(fill=tk.X, padx=5, pady=2)

        # Переменные для отслеживания изменений
        self.current_file = None
        self.file_modified = False
        self.original_content = ""

    def setup_editor_tab(self):
        """Настройка вкладки редактора"""
        # Панель инструментов редактора
        toolbar_frame = ttk.Frame(self.editor_tab)
        toolbar_frame.pack(fill=tk.X, pady=(0, 5))

        self.save_button = ttk.Button(toolbar_frame, text="💾 Сохранить", command=self.save_current_file, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=2)

        self.send_file_button = ttk.Button(toolbar_frame, text="📤 Отправить файл", command=self.send_current_file_to_chat)
        self.send_file_button.pack(side=tk.LEFT, padx=2)

        ttk.Button(toolbar_frame, text="📊 Отчёт по файлам", command=self.generate_report_from_files,
                   style="Accent.TButton").pack(side=tk.LEFT, padx=2)

        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)

        self.file_path_label = ttk.Label(toolbar_frame, text="Файл не открыт", foreground="gray")
        self.file_path_label.pack(side=tk.LEFT, padx=5)

        # Текстовое поле с прокруткой
        text_container = ttk.Frame(self.editor_tab)
        text_container.pack(fill=tk.BOTH, expand=True)

        self.editor_text = tk.Text(
            text_container,
            wrap=tk.NONE,
            font=("Consolas", 11),
            undo=True,
            relief=tk.FLAT,
            padx=12, pady=10,
            tabs="4c",
        )
        scrollbar_y = ttk.Scrollbar(text_container, orient=tk.VERTICAL, command=self.editor_text.yview)
        scrollbar_x = ttk.Scrollbar(text_container, orient=tk.HORIZONTAL, command=self.editor_text.xview)

        self.editor_text.grid(row=0, column=0, sticky="nsew")
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        scrollbar_x.grid(row=1, column=0, sticky="ew")

        text_container.grid_rowconfigure(0, weight=1)
        text_container.grid_columnconfigure(0, weight=1)

        self.editor_text.config(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

        # Отслеживание изменений
        self.editor_text.bind('<KeyRelease>', self.on_text_changed)
        self.editor_text.bind('<Button-1>', self.on_text_changed)
        # Ctrl+A — выделить всё (переопределяем класс-биндинг Text)
        self.editor_text.bind('<Control-a>', lambda e: self._select_all_in(self.editor_text))
        self.editor_text.bind('<Control-A>', lambda e: self._select_all_in(self.editor_text))
        # Ctrl+Y — redo (в Text нет нативного, добавляем)
        self.editor_text.bind('<Control-y>', lambda e: self._redo_in(self.editor_text))
        self.editor_text.bind('<Control-Y>', lambda e: self._redo_in(self.editor_text))

    def setup_chat_tab(self):
        """Настройка вкладки общего чата"""
        # Заголовок
        ttk.Label(self.chat_tab, text="💬 Общий чат проекта", font=("Segoe UI", 13, "bold")).pack(pady=10)

        # Кнопки управления чатом
        chat_controls = ttk.Frame(self.chat_tab)
        chat_controls.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(chat_controls, text="🔄 Обновить чат", command=self.refresh_chat).pack(side=tk.LEFT, padx=2)
        ttk.Button(chat_controls, text="🗑️ Очистить чат", command=self.clear_chat).pack(side=tk.LEFT, padx=2)
        ttk.Button(chat_controls, text="📤 Отправить файл в чат", command=self.send_current_file_to_chat).pack(side=tk.LEFT, padx=2)

        # Поле для сообщения
        msg_frame = ttk.LabelFrame(self.chat_tab, text="Сообщение")
        msg_frame.pack(fill=tk.X, padx=10, pady=5)

        self.chat_message = tk.Text(msg_frame, height=3, wrap=tk.WORD,
            relief=tk.FLAT, padx=8, pady=6, font=("Segoe UI", 10))
        self.chat_message.pack(fill=tk.X, padx=5, pady=5)
        self.chat_message.bind('<Control-a>', lambda e: self._select_all_in(self.chat_message))
        self.chat_message.bind('<Control-A>', lambda e: self._select_all_in(self.chat_message))
        self.chat_message.bind('<Return>', lambda e: (self.send_chat_message(), "break")[1])

        ttk.Button(msg_frame, text="📨 Отправить сообщение", command=self.send_chat_message, style="Accent.TButton").pack(pady=5)

        # История чата
        chat_history_frame = ttk.LabelFrame(self.chat_tab, text="История чата")
        chat_history_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.chat_history = scrolledtext.ScrolledText(chat_history_frame, height=20, wrap=tk.WORD,
            state=tk.DISABLED, relief=tk.FLAT, padx=10, pady=8, font=("Segoe UI", 10))
        self.chat_history.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Автообновление чата каждые 5 секунд
        self.schedule_chat_refresh()

    def setup_neuro_panel(self):
        """Настройка панели Нейро"""
        # Заголовок
        ttk.Label(self.right_frame, text="🧠 Нейро", font=("Segoe UI", 13, "bold")).pack(pady=8)

        # Статус подключения
        self.neuro_status_label = ttk.Label(self.right_frame, text="Статус: Не подключено", foreground="red")
        self.neuro_status_label.pack(pady=5)

        # Чат с нейросетью
        ttk.Label(self.right_frame, text="Вопрос к нейросети:").pack(pady=5)

        self.neuro_question = tk.Text(self.right_frame, height=3, wrap=tk.WORD,
            relief=tk.FLAT, padx=8, pady=6, font=("Segoe UI", 10))
        self.neuro_question.pack(fill=tk.X, padx=5, pady=2)
        self.neuro_question.bind('<Control-a>', lambda e: self._select_all_in(self.neuro_question))
        self.neuro_question.bind('<Control-A>', lambda e: self._select_all_in(self.neuro_question))
        self.neuro_question.bind('<Return>', lambda e: (self.ask_neuro(), "break")[1])

        # Кнопки для ввода вопроса
        question_buttons_frame = ttk.Frame(self.right_frame)
        question_buttons_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Button(question_buttons_frame, text="📝 Отправить вопрос", command=self.ask_neuro, style="Accent.TButton").pack(side=tk.LEFT, padx=2)

        # Кнопка голосового ввода (улучшенная версия)
        if ADVANCED_VOICE_AVAILABLE:
            self.voice_button = ttk.Button(question_buttons_frame, text="🎤 Голос (реальное время)", command=self.toggle_advanced_voice_input)
            self.voice_button.pack(side=tk.LEFT, padx=2)
            self.is_recording_voice = False
            self.voice_status_label = ttk.Label(question_buttons_frame, text="", foreground="blue")
            self.voice_status_label.pack(side=tk.LEFT, padx=5)
        elif VOICE_AVAILABLE:
            self.voice_button = ttk.Button(question_buttons_frame, text="🎤 Голосовой ввод", command=self.toggle_voice_input)
            self.voice_button.pack(side=tk.LEFT, padx=2)
            self.is_recording_voice = False
        else:
            ttk.Button(question_buttons_frame, text="🎤 Голос (недоступен)", state=tk.DISABLED).pack(side=tk.LEFT, padx=2)

        # Ответ нейросети
        ttk.Label(self.right_frame, text="Ответ:").pack(pady=5)

        self.neuro_response = tk.Text(self.right_frame, height=15, wrap=tk.WORD,
            state=tk.DISABLED, relief=tk.FLAT, padx=8, pady=6, font=("Segoe UI", 10))
        self.neuro_response.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)

        # Кнопка обновления контекста
        ttk.Button(self.right_frame, text="Обновить контекст", command=self.update_neuro_context).pack(pady=5)

    def init_ollama(self):
        """Инициализация подключения к Ollama"""
        def check_connection():
            self.ollama_manager = OllamaManager()
            if self.ollama_manager.test_connection():
                self.neuro_status_label.config(text="Статус: Подключено", foreground="green")
                self.logger.info("Подключение к Ollama установлено")
            else:
                self.neuro_status_label.config(text="Статус: Ошибка подключения", foreground="red")
                self.logger.error("Не удалось подключиться к Ollama")

        threading.Thread(target=check_connection, daemon=True).start()

    def apply_theme(self):
        """Единая тема StartIDE — светлый редактор, тёмные боковые панели"""
        c = self.colors
        self.root.configure(bg=c["cream"])

        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        bf  = ("Segoe UI", 10)
        bfb = ("Segoe UI", 10, "bold")
        mf  = ("Segoe UI", 11, "bold")

        style.configure(".",                  font=bf,  background=c["cream"],   foreground=c["ink"])
        style.configure("TFrame",             background=c["cream"])
        style.configure("Dark.TFrame",        background=c["panel_bg"])
        style.configure("TLabel",             background=c["cream"],   foreground=c["ink"])
        style.configure("Dark.TLabel",        background=c["panel_bg"],foreground=c["panel_fg"])
        style.configure("Muted.TLabel",       background=c["cream"],   foreground=c["muted"])
        style.configure("Status.TLabel",      background=c["plum"],    foreground=c["cream"],    padding=(8,4))
        style.configure("TLabelFrame",        background=c["cream"],   foreground=c["plum"],     relief="solid")
        style.configure("TLabelFrame.Label",  background=c["cream"],   foreground=c["plum"],     font=bfb)
        style.configure("Dark.TLabelFrame",   background=c["panel_bg"],foreground=c["accent"],   relief="solid")
        style.configure("Dark.TLabelFrame.Label", background=c["panel_bg"], foreground=c["accent"], font=bfb)
        style.configure("TNotebook",          background=c["cream"],   borderwidth=0)
        style.configure("TNotebook.Tab",      background=c["accent"],  foreground=c["ink"],      padding=(12,7), font=bfb)
        style.map("TNotebook.Tab",
                  background=[("selected", c["plum"]),  ("active", c["lavender"])],
                  foreground=[("selected", c["cream"])])
        style.configure("TButton",            background=c["lavender"],foreground=c["ink"],      padding=(10,6), font=bfb, bordercolor=c["plum"], focusthickness=0)
        style.map("TButton",
                  background=[("active", c["accent"]),("pressed", c["plum"]),("disabled","#D7D0DD")],
                  foreground=[("pressed", c["cream"]),("disabled", c["muted"])])
        style.configure("Accent.TButton",     background=c["plum"],    foreground=c["cream"],    padding=(10,6))
        style.map("Accent.TButton",
                  background=[("active", c["lavender"]),("pressed", c["ink"])])
        style.configure("TEntry",            fieldbackground=c["white"],foreground=c["ink"],     bordercolor=c["accent"], padding=5)
        style.configure("Treeview",          background=c["white"],   fieldbackground=c["white"],foreground=c["ink"],     rowheight=24)
        style.configure("Treeview.Heading",  background=c["plum"],    foreground=c["cream"],    font=bfb)
        style.map("Treeview",
                  background=[("selected", c["lavender"])],
                  foreground=[("selected", c["ink"])])
        style.configure("TPanedwindow",       background=c["cream"])

        # Tkinter-виджеты (не ttk) — редактор и текстовые поля
        for widget_name in ("editor_text", "neuro_question", "neuro_response",
                            "chat_message", "chat_history", "stats_text", "git_text"):
            w = getattr(self, widget_name, None)
            if w:
                if widget_name == "editor_text":
                    w.configure(bg=c["white"], fg=c["ink"], insertbackground=c["plum"],
                                selectbackground=c["lavender"], font=("Consolas", 11))
                elif widget_name in ("neuro_question", "neuro_response"):
                    w.configure(bg=c["panel_bg"], fg=c["panel_fg"], insertbackground=c["accent"],
                                selectbackground=c["plum"], font=("Segoe UI", 10))
                else:
                    w.configure(bg=c["cream_soft"], fg=c["ink"], insertbackground=c["plum"],
                                selectbackground=c["lavender"], font=("Segoe UI", 10))

        # Listbox для отслеживания
        if hasattr(self, "tracking_listbox"):
            self.tracking_listbox.configure(
                bg=c["panel_bg"], fg=c["panel_fg"],
                selectbackground=c["lavender"], selectforeground=c["ink"],
                relief="flat", borderwidth=0
            )
        if hasattr(self, "file_tree"):
            self.file_tree.configure()

    def _style_text(self, widget, dark=False):
        """Применить стиль к tk.Text / scrolledtext виджету"""
        c = self.colors
        if dark:
            widget.configure(bg=c["panel_bg"], fg=c["panel_fg"],
                             insertbackground=c["accent"],
                             selectbackground=c["plum"], selectforeground=c["cream"])
        else:
            widget.configure(bg=c["cream_soft"], fg=c["ink"],
                             insertbackground=c["plum"],
                             selectbackground=c["lavender"], selectforeground=c["ink"])

    def init_database(self):
        """Инициализация новой системы баз данных"""
        try:
            # Инициализация логгера
            self.app_logger = AppLogger("context")
            self.app_logger.log_app_start("StartIDE")

            # Инициализация базы данных
            self.db_manager = DatabaseManager("context")
            self.app_logger.log_database_action("init", "База данных инициализирована")
            self.logger.info("База данных инициализирована")

            # Инициализация chat_manager
            from shared.chat_manager import ChatManager
            self.chat_manager = ChatManager(self.db_manager)

            # Инициализация менеджеров проектов и файлов
            self.project_manager = ProjectManager("context")
            self.file_tracker = FileTracker("context")
            self.app_logger.log_database_action("init", "Менеджеры проектов и файлов инициализированы")

            # Инициализация голосового менеджера (опционально)
            if ADVANCED_VOICE_AVAILABLE:
                try:
                    self.advanced_voice_manager = AdvancedVoiceManager()
                    if self.advanced_voice_manager.init_voice_input():
                        self.app_logger.log_voice_action("init", "Улучшенный голосовой ввод инициализирован")
                        self.logger.info("Улучшенный голосовой ввод инициализирован")
                    else:
                        self.app_logger.log_warning("Не удалось инициализировать улучшенный голосовой ввод")
                        self.logger.warning("Не удалось инициализировать улучшенный голосовой ввод")
                except Exception as e:
                    self.app_logger.log_error(f"Ошибка улучшенного голосового ввода: {e}")
                    self.advanced_voice_manager = None
                    self.app_logger.log_warning("Голосовой ввод недоступен (требуется установка speechrecognition)")
                    self.logger.warning("Голосовой ввод недоступен")

            # Инициализация голосового менеджера (старый метод)
            try:
                from StartIDE.voice_manager import VoiceManager
                self.voice_manager = VoiceManager()
                self.app_logger.log_voice_action("init", "Голосовой менеджер инициализирован")
            except ImportError:
                self.voice_manager = None
                self.app_logger.log_warning("Голосовой менеджер недоступен")

        except Exception as e:
            if self.app_logger:
                self.app_logger.log_error(f"Ошибка инициализации базы данных: {e}")
            self.logger.error(f"Ошибка инициализации базы данных: {e}")
            messagebox.showerror("Ошибка", f"Не удалось инициализировать базу данных: {e}")

    def new_project(self):
        """Создание нового проекта"""
        folder_path = filedialog.askdirectory(title="Выберите папку для проекта")
        if folder_path:
            self.project_path = Path(folder_path)

            # Инициализация новой системы баз данных
            if self.db_manager:
                self.current_project_id = self.db_manager.get_or_create_project(str(self.project_path))
                self.git_manager = GitManager(str(self.project_path), self.db_manager)

                # Обновляем Git контекст
                if self.git_manager.is_git_repo:
                    threading.Thread(target=self.git_manager.update_git_context, args=(self.current_project_id,), daemon=True).start()

            # Инициализация чата с sqlite3
            self.chat_manager = ChatManager(self.db_manager)

            # Сохраняем старую систему для совместимости
            self.project_context = ProjectContext(str(self.project_path))
            self.project_context.update_context("project_created", f"Проект создан в {folder_path}")

            self.refresh_file_tree()
            self.status_bar.config(text=f"Проект: {self.project_path.name}")

            # Отправляем контекст в нейросеть
            if self.ollama_manager:
                threading.Thread(target=self.send_context_to_neuro, daemon=True).start()

    def open_project(self):
        """Открытие существующего проекта автоматически"""
        folder_path = filedialog.askdirectory(title="Выберите папку проекта")
        if folder_path:
            self.project_path = Path(folder_path)

            # Проверяем, что это действительно проект
            if not self._is_valid_project_folder(self.project_path):
                result = messagebox.askyesno(
                    "Внимание",
                    "Выбранная папка не похожа на программный проект. Открыть anyway?"
                )
                if not result:
                    return

            # Инициализация новой системы баз данных
            if self.db_manager:
                self.current_project_id = self.db_manager.get_or_create_project(str(self.project_path))
                self.git_manager = GitManager(str(self.project_path), self.db_manager)

                # Автоанализ проекта в фоне
                from shared.project_auto_analyzer import ProjectAutoAnalyzer
                analyzer = ProjectAutoAnalyzer(self.db_manager)

                threading.Thread(
                    target=self._auto_analyze_and_update,
                    args=(analyzer, str(self.project_path)),
                    daemon=True
                ).start()

                # Обновляем Git контекст
                if self.git_manager.is_git_repo:
                    threading.Thread(target=self.git_manager.update_git_context, args=(self.current_project_id,), daemon=True).start()

            # Инициализация чата с sqlite3
            self.chat_manager = ChatManager(self.db_manager)

            # Сохраняем старую систему для совместимости
            self.project_context = ProjectContext(str(self.project_path))
            self.project_context.update_context("project_opened", f"Проект открыт: {self.project_path}")

            self.refresh_file_tree()
            self.status_bar.config(text=f"Проект: {self.project_path.name} (анализ...)")

            # Отправляем контекст в нейросеть
            if self.ollama_manager:
                threading.Thread(target=self.send_context_to_neuro, daemon=True).start()

            if self.app_logger:
                self.app_logger.log_project_open(str(self.project_path), self.current_project_id)

    def _is_valid_project_folder(self, path: Path) -> bool:
        """Проверка, является ли папка проектом"""
        # Индикаторы проекта
        project_indicators = [
            # Файлы конфигурации
            'package.json', 'requirements.txt', 'setup.py', 'pyproject.toml',
            'pom.xml', 'build.gradle', 'Cargo.toml', 'go.mod', 'composer.json',
            'Gemfile', 'Makefile', 'CMakeLists.txt',

            # Основные файлы
            'main.py', 'app.py', 'index.js', 'app.js', 'main.js',
            'index.html', 'index.php', 'main.cpp', 'main.go', 'main.rs',

            # Папки проекта
            'src/', 'lib/', 'app/', 'components/', 'models/', 'views/'
        ]

        for indicator in project_indicators:
            if indicator.endswith('/'):
                # Проверка папки
                if (path / indicator).exists():
                    return True
            else:
                # Проверка файла
                if (path / indicator).exists():
                    return True

        # Проверяем наличие исходных файлов
        code_extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs', '.php', '.rb']
        for item in path.iterdir():
            if item.is_file() and item.suffix in code_extensions:
                return True

        return False

    def _auto_analyze_and_update(self, analyzer: 'ProjectAutoAnalyzer', project_path: str):
        """Автоанализ проекта и обновление UI"""
        try:
            # Выполняем анализ
            project_data = analyzer.analyze_project(project_path)

            if project_data:
                # Обновляем статус в главном потоке
                self.root.after(0, lambda: self.status_bar.config(text=f"Проект: {project_data['name']}"))

                # Обновляем информацию о проекте
                self.root.after(0, lambda: self.update_project_info_display(project_data))

                self.logger.info(f"Проанализирован проект: {project_data['name']}")
            else:
                self.root.after(0, lambda: self.status_bar.config(text=f"Проект: {Path(project_path).name}"))

        except Exception as e:
            self.logger.error(f"Ошибка автоанализа проекта: {e}")
            self.root.after(0, lambda: self.status_bar.config(text=f"Проект: {Path(project_path).name} (ошибка анализа)"))

    def update_project_info_display(self, project_data: Dict):
        """Обновление отображения информации о проекте"""
        try:
            # Обновляем индикатор проекта
            project_name = project_data.get('name', 'Проект')
            self.project_status_label.config(text=f" {project_name}", foreground="green")

            # Обновляем индикатор Git
            git_info = project_data.get('git_info', {})
            if git_info.get('is_git_repo'):
                branch = git_info.get('current_branch', 'main')
                self.git_status_indicator.config(text=f" {branch}", foreground="green")
            else:
                self.git_status_indicator.config(text=" нет", foreground="gray")

            # Показываем основные технологии в статусе
            tech_stack = project_data.get('tech_stack', {})
            if tech_stack.get('languages'):
                main_lang = tech_stack['languages'][0]['name']
                current_status = self.status_bar.cget("text")
                self.status_bar.config(text=f"{current_status} | {main_lang}")

        except Exception as e:
            self.logger.error(f"Ошибка обновления информации о проекте: {e}")

    def update_status_indicators(self):
        """Обновление всех индикаторов статуса"""
        try:
            # Индикатор AI
            if hasattr(self, 'ollama_manager') and self.ollama_manager:
                if self.ollama_manager.test_connection():
                    self.ai_status_indicator.config(text=" онлайн", foreground="green")
                else:
                    self.ai_status_indicator.config(text=" оффлайн", foreground="red")
            else:
                self.ai_status_indicator.config(text=" -", foreground="gray")

            # Индикатор голосового ввода
            if hasattr(self, 'voice_manager') and self.voice_manager:
                if hasattr(self, 'is_recording_voice') and self.is_recording_voice:
                    self.voice_status_indicator.config(text=" запись", foreground="red")
                else:
                    self.voice_status_indicator.config(text=" готов", foreground="green")
            else:
                self.voice_status_indicator.config(text=" недоступен", foreground="gray")

        except Exception as e:
            self.logger.error(f"Ошибка обновления индикаторов: {e}")

    def refresh_file_tree(self):
        """Обновление дерева файлов"""
        if not self.project_path:
            return

        # Очищаем дерево
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)

        # Добавляем файлы и папки
        try:
            for item in self.project_path.iterdir():
                if item.name.startswith('.'):
                    continue

                if item.is_dir():
                    node = self.file_tree.insert("", "end", text=f"📁 {item.name}", values=("", "folder"))
                    self.add_folder_contents(item, node)
                else:
                    size = f"{item.stat().st_size} байт" if item.stat().st_size < 1024 else f"{item.stat().st_size//1024} КБ"
                    self.file_tree.insert("", "end", text=f"📄 {item.name}", values=(size, "file"))
        except Exception as e:
            self.logger.error(f"Ошибка обновления дерева файлов: {e}")

    def add_folder_contents(self, folder_path, parent_node):
        """Рекурсивное добавление содержимого папки"""
        try:
            for item in folder_path.iterdir():
                if item.name.startswith('.'):
                    continue

                if item.is_dir():
                    node = self.file_tree.insert(parent_node, "end", text=f"📁 {item.name}", values=("", "folder"))
                    self.add_folder_contents(item, node)
                else:
                    size = f"{item.stat().st_size} байт" if item.stat().st_size < 1024 else f"{item.stat().st_size//1024} КБ"
                    self.file_tree.insert(parent_node, "end", text=f"📄 {item.name}", values=(size, "file"))
        except Exception as e:
            self.logger.error(f"Ошибка добавления содержимого папки: {e}")

    def create_file(self):
        """Создание нового файла"""
        if not self.project_path:
            messagebox.showwarning("Внимание", "Сначала создайте или откройте проект")
            return

        file_name = tk.simpledialog.askstring("Создать файл", "Введите имя файла:")
        if file_name:
            try:
                new_file = self.project_path / file_name
                new_file.touch()

                if self.project_context:
                    self.project_context.add_file_change(str(new_file), "created")

                self.refresh_file_tree()
                self.status_bar.config(text=f"Файл создан: {file_name}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать файл: {e}")

    def create_folder(self):
        """Создание новой папки"""
        if not self.project_path:
            messagebox.showwarning("Внимание", "Сначала создайте или откройте проект")
            return

        folder_name = tk.simpledialog.askstring("Создать папку", "Введите имя папки:")
        if folder_name:
            try:
                new_folder = self.project_path / folder_name
                new_folder.mkdir()

                if self.project_context:
                    self.project_context.add_folder_change(str(new_folder), "created")

                self.refresh_file_tree()
                self.status_bar.config(text=f"Папка создана: {folder_name}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать папку: {e}")

    def open_file_in_editor(self, event):
        """Открытие файла в редакторе"""
        selection = self.file_tree.selection()
        if selection:
            item = self.file_tree.item(selection[0])
            file_name = item['text'].replace('📁 ', '').replace('📄 ', '')

            if item['values'][1] == 'file':
                try:
                    # Сохраняем текущий файл если есть изменения
                    if self.current_file and self.file_modified:
                        result = messagebox.askyesno("Несохраненные изменения",
                                                   f"Сохранить изменения в файле {self.current_file.name}?")
                        if result:
                            self.save_current_file()

                    file_path = self.project_path / file_name
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Загружаем файл в редактор
                    self.editor_text.delete(1.0, tk.END)
                    self.editor_text.insert(1.0, content)

                    # Обновляем интерфейс
                    self.current_file = file_path
                    self.original_content = content
                    self.file_modified = False
                    self.save_button.config(state=tk.DISABLED)

                    # Обновляем метки
                    self.file_path_label.config(text=f"📄 {file_name}", foreground="black")
                    self.file_info_label.config(text=f"Файл: {file_name} | Размер: {len(content)} символов")
                    self.status_bar.config(text=f"Открыт файл: {file_name}")

                    if self.project_context:
                        self.project_context.add_file_change(str(file_path), "opened")

                except Exception as e:
                    messagebox.showerror("Ошибка", f"Не удалось открыть файл: {e}")

    def on_text_changed(self, event=None):
        """Обработка изменений в тексте"""
        if self.current_file and not self.file_modified:
            current_content = self.editor_text.get(1.0, tk.END).strip()
            if current_content != self.original_content.strip():
                self.file_modified = True
                self.save_button.config(state=tk.NORMAL)
                self.file_path_label.config(text=f"📄 {self.current_file.name} *", foreground="red")
                self.status_bar.config(text=f"Файл изменен: {self.current_file.name}")

    def on_text_modified(self, event):
        """Обработка события Modified"""
        try:
            self.editor_text.edit_modified(False)
            self.on_text_changed()
        except:
            pass

    def save_current_file(self):
        """Сохранение текущего файла"""
        if not self.current_file:
            return

        try:
            content = self.editor_text.get(1.0, tk.END).rstrip()
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(content)

            # Обновляем состояние
            self.original_content = content
            self.file_modified = False
            self.save_button.config(state=tk.DISABLED)

            # Обновляем интерфейс
            self.file_path_label.config(text=f"📄 {self.current_file.name}", foreground="black")
            self.status_bar.config(text=f"Файл сохранен: {self.current_file.name}")

            if self.project_context:
                self.project_context.add_file_change(str(self.current_file), "saved")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")

    def save_file_as(self):
        """Сохранение файла под новым именем"""
        if not self.current_file:
            return

        new_file_path = filedialog.asksaveasfilename(
            title="Сохранить файл как...",
            initialdir=str(self.project_path),
            initialname=self.current_file.name,
            filetypes=[("Текстовые файлы", "*.txt"), ("Python файлы", "*.py"),
                       ("Все файлы", "*.*")]
        )

        if new_file_path:
            try:
                content = self.editor_text.get(1.0, tk.END).rstrip()
                with open(new_file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                # Обновляем текущий файл
                self.current_file = Path(new_file_path)
                self.original_content = content
                self.file_modified = False
                self.save_button.config(state=tk.DISABLED)

                # Обновляем интерфейс
                self.file_path_label.config(text=f"📄 {self.current_file.name}", foreground="black")
                self.file_info_label.config(text=f"Файл: {self.current_file.name} | Размер: {len(content)} символов")
                self.status_bar.config(text=f"Файл сохранен как: {self.current_file.name}")

                # Обновляем дерево файлов
                self.refresh_file_tree()

                if self.project_context:
                    self.project_context.add_file_change(str(self.current_file), "saved_as")

            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")

    def show_file_context_menu(self, event):
        """Показ контекстного меню для файлов"""
        pass

    def toggle_neuro_panel(self):
        """Переключение видимости панели Нейро"""
        if self.right_frame.winfo_viewable():
            self.right_frame.pack_forget()
        else:
            self.right_frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)

    def ask_neuro(self):
        """Задать вопрос нейросети"""
        if not self.ollama_manager or not self.project_path:
            messagebox.showwarning("Внимание", "Нейросеть не доступна или проект не открыт")
            return

        question = self.neuro_question.get(1.0, tk.END).strip()
        if not question:
            return

        def get_response():
            response = self.ollama_manager.ask_about_project(question, str(self.project_path))

            self.neuro_response.config(state=tk.NORMAL)
            self.neuro_response.delete(1.0, tk.END)
            self.neuro_response.insert(1.0, f"Вопрос: {question}\n\nОтвет: {response}")
            self.neuro_response.config(state=tk.DISABLED)

        threading.Thread(target=get_response, daemon=True).start()

    def update_neuro_context(self):
        """Обновление контекста нейросети"""
        if not self.ollama_manager or not self.project_context:
            messagebox.showwarning("Внимание", "Нейросеть не доступна")
            return

        threading.Thread(target=self.send_context_to_neuro, daemon=True).start()

    def send_context_to_neuro(self):
        """Отправка контекста в нейросеть"""
        try:
            context_data = self.project_context.load_context()
            success = self.ollama_manager.send_project_context(str(self.project_path), context_data)

            if success:
                self.status_bar.config(text="Контекст отправлен в нейросеть")
            else:
                self.status_bar.config(text="Ошибка отправки контекста")
        except Exception as e:
            self.logger.error(f"Ошибка отправки контекста: {e}")

    # ===== МЕТОДЫ ДЛЯ РАБОТЫ С ОБЩИМ ЧАТОМ =====

    def refresh_chat(self):
        """Обновление истории чата из базы данных"""
        if not self.current_project_id or not hasattr(self, 'chat_manager') or not self.chat_manager:
            return

        try:
            messages = self.chat_manager.get_messages(self.current_project_id, limit=100)

            self.chat_history.config(state=tk.NORMAL)
            self.chat_history.delete(1.0, tk.END)

            for msg in messages:
                timestamp = str(msg.get('timestamp', ''))
                if len(timestamp) >= 19:
                    time_str = timestamp[11:19]
                else:
                    time_str = timestamp
                sender = msg.get('sender', 'Unknown')
                content = msg.get('content', '')

                if sender in ['StartIDE', 'StartOffice']:
                    self.chat_history.insert(tk.END, f"[{time_str}] Вы:\n")
                else:
                    self.chat_history.insert(tk.END, f"[{time_str}] AI:\n")
                self.chat_history.insert(tk.END, f"  {content}\n")
                self.chat_history.insert(tk.END, "-" * 40 + "\n")

            self.chat_history.see(tk.END)
            self.chat_history.config(state=tk.DISABLED)

        except Exception as e:
            self.logger.error(f"Ошибка обновления чата: {e}")

    def clear_chat(self):
        """Очистка чата"""
        if not self.ensure_project_selected():
            return

        if messagebox.askyesno("Подтверждение", "Очистить историю чата?"):
            try:
                # Очищаем чат в базе данных
                self.chat_manager.clear_chat(self.current_project_id)

                # Очищаем UI
                self.chat_history.config(state=tk.NORMAL)
                self.chat_history.delete(1.0, tk.END)
                self.chat_history.config(state=tk.DISABLED)
                self.last_chat_timestamp = None
                self.status_bar.config(text="Чат очищен")

                self.logger.info(f"Чат очищен для проекта {self.current_project_id}")

            except Exception as e:
                self.logger.error(f"Ошибка очистки чата: {e}")
                messagebox.showerror("Ошибка", "Не удалось очистить чат")

    def send_chat_message(self):
        """Отправка текстового сообщения в чат"""
        if not self.current_project_id:
            messagebox.showwarning("Внимание", "Сначала откройте проект")
            return

        message = self.chat_message.get(1.0, tk.END).strip()
        if not message:
            return

        # Сохраняем сообщение в базу данных
        if self.chat_manager:
            self.chat_manager.add_message(
                self.current_project_id,
                "StartIDE",
                "text",
                message
            )

        # Очищаем поле ввода и обновляем чат
        self.chat_message.delete(1.0, tk.END)
        self.refresh_chat()

        # Получаем AI ответ с сохранением контекста
        if self.ollama_manager and self.current_project_id and self.chat_manager:
            def get_ai_response():
                try:
                    chat_context = self.chat_manager.get_ai_context(self.current_project_id)
                    response = self.ollama_manager.send_chat_message(message, chat_context)

                    if response:
                        self.chat_manager.add_message(
                            self.current_project_id,
                            "AI",
                            "text",
                            response
                        )
                        self.root.after(0, self.refresh_chat)
                        self.root.after(0, lambda: self.status_bar.config(text="AI ответ получен"))
                    else:
                        self.root.after(0, lambda: self.status_bar.config(text="AI не ответил (проверьте Ollama)"))

                except Exception as e:
                    self.logger.error(f"Ошибка получения AI ответа: {e}")
                    self.root.after(0, lambda: self.status_bar.config(text="Ошибка AI ответа"))

            threading.Thread(target=get_ai_response, daemon=True).start()

        self.status_bar.config(text="Сообщение отправлено")

    def send_current_file_to_chat(self):
        """Отправка текущего файла в чат для анализа"""
        if not self.current_project_id:
            messagebox.showwarning("Внимание", "Сначала откройте проект")
            return

        if not self.current_file:
            messagebox.showwarning("Внимание", "Сначала откройте файл")
            return

        try:
            with open(self.current_file, 'r', encoding='utf-8', errors='replace') as f:
                file_content = f.read()

            question = tk.simpledialog.askstring(
                "Отправка файла в чат",
                "Введите вопрос или комментарий к файлу:",
                initialvalue="Проанализируй этот файл"
            )

            if question is None:
                return

            # Формируем сообщение с содержимым файла
            message = f"{question}\n\nФайл: {self.current_file.name}\n```\n{file_content[:3000]}\n```"

            # Сохраняем в базу данных
            if self.chat_manager:
                self.chat_manager.add_message(
                    self.current_project_id, "StartIDE", "file_analysis", message
                )

            self.refresh_chat()
            self.status_bar.config(text=f"Файл {self.current_file.name} отправлен в чат")
            self.center_notebook.select(self.chat_tab)

            # Получаем AI ответ
            if self.ollama_manager and self.chat_manager:
                def get_analysis():
                    try:
                        chat_context = self.chat_manager.get_ai_context(self.current_project_id)
                        response = self.ollama_manager.send_chat_message(message, chat_context)
                        if response:
                            self.chat_manager.add_message(
                                self.current_project_id, "AI", "file_analysis", response
                            )
                            self.root.after(0, self.refresh_chat)
                    except Exception as e:
                        self.logger.error(f"Ошибка анализа файла: {e}")
                threading.Thread(target=get_analysis, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось отправить файл: {e}")

    def generate_report_from_files(self):
        """Выбрать до 2 файлов проекта и сгенерировать подробный AI-отчёт"""
        if not self.ollama_manager:
            messagebox.showwarning("AI недоступен", "Сначала запустите Ollama")
            return
        if not self.project_path:
            messagebox.showwarning("Внимание", "Сначала откройте проект")
            return

        # Диалог выбора файлов
        dlg = tk.Toplevel(self.root)
        dlg.title("Отчёт по файлам")
        dlg.geometry("640x500")
        dlg.transient(self.root)
        dlg.grab_set()
        c = self.colors

        dlg.configure(bg=c["cream"])

        ttk.Label(dlg, text="📊 Генерация AI-отчёта", font=("Segoe UI", 13, "bold")).pack(pady=10)
        ttk.Label(dlg, text="Выберите до 2 файлов из проекта для анализа:", font=("Segoe UI", 10)).pack()

        # Список файлов проекта
        list_frame = ttk.Frame(dlg)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        sb = ttk.Scrollbar(list_frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        file_listbox = tk.Listbox(
            list_frame, selectmode=tk.MULTIPLE, font=("Segoe UI", 10),
            bg=c["cream_soft"], fg=c["ink"],
            selectbackground=c["lavender"], selectforeground=c["ink"],
            relief=tk.FLAT, yscrollcommand=sb.set
        )
        file_listbox.pack(fill=tk.BOTH, expand=True)
        sb.config(command=file_listbox.yview)

        # Наполняем список файлами проекта
        try:
            allowed = {'.py', '.txt', '.js', '.ts', '.json', '.md', '.yaml', '.yml',
                       '.html', '.css', '.java', '.cpp', '.c', '.go', '.rs', '.rb', '.php'}
            all_files = []
            for f in sorted(Path(self.project_path).rglob('*')):
                if f.is_file() and f.suffix.lower() in allowed:
                    rel = f.relative_to(self.project_path)
                    all_files.append((str(rel), str(f)))
                    file_listbox.insert(tk.END, str(rel))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось получить файлы: {e}")
            dlg.destroy()
            return

        # Поле для дополнительного контекста
        ctx_frame = ttk.LabelFrame(dlg, text="Дополнительный контекст (необязательно)")
        ctx_frame.pack(fill=tk.X, padx=10, pady=5)
        extra_ctx = tk.Text(ctx_frame, height=3, font=("Segoe UI", 10),
                            bg=c["cream_soft"], fg=c["ink"],
                            insertbackground=c["plum"], relief=tk.FLAT, padx=8, pady=5)
        extra_ctx.pack(fill=tk.X, padx=5, pady=5)
        extra_ctx.insert("1.0", "Проанализируй файлы, найди проблемы, предложи улучшения и напиши выводы.")

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(fill=tk.X, padx=10, pady=8)

        def _start():
            selected = file_listbox.curselection()
            if not selected:
                messagebox.showwarning("Внимание", "Выберите хотя бы один файл", parent=dlg)
                return
            if len(selected) > 2:
                messagebox.showwarning("Внимание", "Выберите не более 2 файлов", parent=dlg)
                return

            chosen = [all_files[i] for i in selected]
            prompt_extra = extra_ctx.get("1.0", tk.END).strip()
            dlg.destroy()
            self._run_ai_file_report(chosen, prompt_extra)

        ttk.Button(btn_frame, text="✨ Сгенерировать отчёт", command=_start,
                   style="Accent.TButton").pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Отмена", command=dlg.destroy).pack(side=tk.LEFT, padx=4)

    def _run_ai_file_report(self, files: list, extra_context: str = ""):
        """Читает выбранные файлы и отправляет в AI для генерации подробного отчёта"""
        self.status_bar.config(text="📊 Генерирую отчёт...")

        def _worker():
            try:
                parts = []

                # Собираем содержимое файлов
                for rel_name, abs_path in files:
                    try:
                        with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
                            content = f.read()
                        parts.append(
                            f"{'='*60}\n"
                            f"ФАЙЛ: {rel_name}\n"
                            f"{'='*60}\n"
                            f"{content}\n"
                        )
                    except Exception as e:
                        parts.append(f"[Не удалось прочитать {rel_name}: {e}]\n")

                # Добавляем технологический стек если есть
                tech_summary = ""
                if self.current_project_id and self.db_manager:
                    try:
                        cursor = self.db_manager.conn.execute(
                            "SELECT technology, version FROM tech_stack WHERE project_id = ? LIMIT 20",
                            (self.current_project_id,)
                        )
                        rows = cursor.fetchall()
                        if rows:
                            tech_summary = "Технологический стек: " + ", ".join(
                                f"{r[0]}{' '+r[1] if r[1] else ''}" for r in rows
                            )
                    except Exception:
                        pass

                # Формируем промпт
                prompt = (
                    "Ты — опытный разработчик ПО. Тебе предоставлены файлы проекта.\n"
                    "Напиши ПОДРОБНЫЙ технический отчёт на русском языке со следующими разделами:\n\n"
                    "1. ОБЩЕЕ ОПИСАНИЕ — что делает этот код, его назначение\n"
                    "2. АРХИТЕКТУРА — как устроен код, основные компоненты\n"
                    "3. СИЛЬНЫЕ СТОРОНЫ — что сделано хорошо\n"
                    "4. ПРОБЛЕМЫ И УЯЗВИМОСТИ — конкретные баги, риски, слабые места\n"
                    "5. РЕКОМЕНДАЦИИ — конкретные шаги по улучшению с примерами кода\n"
                    "6. ВЫВОДЫ — итоговое заключение\n\n"
                )
                if tech_summary:
                    prompt += f"{tech_summary}\n\n"
                if extra_context:
                    prompt += f"Дополнительный контекст: {extra_context}\n\n"
                prompt += "СОДЕРЖИМОЕ ФАЙЛОВ:\n\n" + "\n".join(parts)

                response = self.ollama_manager.ask_question(prompt) or "AI не вернул ответ"

                # Показываем результат
                self.root.after(0, lambda: self._show_report_window(response, files))
                self.root.after(0, lambda: self.status_bar.config(text="📊 Отчёт готов"))

            except Exception as e:
                self.logger.error(f"Ошибка генерации отчёта: {e}")
                self.root.after(0, lambda: self.status_bar.config(text=f"Ошибка отчёта: {e}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _show_report_window(self, report_text: str, files: list):
        """Показывает отчёт в отдельном окне с возможностью сохранить как .txt"""
        win = tk.Toplevel(self.root)
        win.title("AI Отчёт по проекту")
        win.geometry("800x600")
        win.transient(self.root)
        c = self.colors
        win.configure(bg=c["cream"])

        file_names = ", ".join(rel for rel, _ in files)
        ttk.Label(win, text=f"📊 Отчёт: {file_names}",
                  font=("Segoe UI", 12, "bold")).pack(pady=8, padx=10, anchor="w")

        txt = scrolledtext.ScrolledText(
            win, font=("Segoe UI", 10), wrap=tk.WORD,
            bg=c["cream_soft"], fg=c["ink"],
            relief=tk.FLAT, padx=12, pady=10
        )
        txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        txt.insert("1.0", report_text)

        def _save():
            path = filedialog.asksaveasfilename(
                parent=win, defaultextension=".txt",
                filetypes=[("Текстовые файлы", "*.txt")],
                initialfile="ai_report.txt"
            )
            if path:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(txt.get("1.0", tk.END))
                messagebox.showinfo("Сохранено", f"Отчёт сохранён: {path}", parent=win)

        btn_row = ttk.Frame(win)
        btn_row.pack(fill=tk.X, padx=10, pady=8)
        ttk.Button(btn_row, text="💾 Сохранить как .txt", command=_save,
                   style="Accent.TButton").pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Закрыть", command=win.destroy).pack(side=tk.LEFT, padx=4)

    def schedule_chat_refresh(self):
        """Планирование автоматического обновления чата"""
        if self.current_project_id:
            self.refresh_chat()
        self.root.after(5000, self.schedule_chat_refresh)

    def toggle_advanced_voice_input(self):
        """Переключение улучшенного голосового ввода с реальным временем"""
        if not ADVANCED_VOICE_AVAILABLE or not self.advanced_voice_manager:
            messagebox.showwarning("Голосовой ввод", "Улучшенный голосовой ввод недоступен. Установите speechrecognition.")
            return

        if not self.is_recording_voice:
            # Начинаем непрерывную запись
            self.voice_button.config(text="⏹️ Остановить запись")
            self.is_recording_voice = True

            # Настраиваем чувствительность для русского языка
            self.advanced_voice_manager.set_language("ru-RU")
            self.advanced_voice_manager.set_sensitivity(0.7)

            # Устанавливаем callback для частичного распознавания в реальном времени
            def partial_callback(text):
                # Показываем распознаваемый текст в статусе
                if hasattr(self, 'voice_status_label'):
                    self.voice_status_label.config(text=f"🗣️: {text}")

                # Умная логика вставки текста без затирания предыдущего
                current_text = self.neuro_question.get(1.0, tk.END).strip()
                text_to_add = text.strip()

                if not text_to_add:
                    return

                if not current_text:
                    # Если поле пустое, добавляем первое слово
                    self.neuro_question.insert(tk.END, text_to_add + " ")
                else:
                    # Проверяем, заканчивается ли текущий текст на неполное слово
                    words = current_text.split()
                    if words:
                        last_word = words[-1]

                        # Если последнее слово короче 3 символов или похоже на текущее распознавание
                        if len(last_word) <= 3 or (text_to_add.lower().startswith(last_word.lower()) and len(text_to_add) > len(last_word)):
                            # Заменяем последнее слово на более полное
                            words[-1] = text_to_add
                            new_text = " ".join(words) + " "

                            # Обновляем только последние символы
                            self.neuro_question.delete(1.0, tk.END)
                            self.neuro_question.insert(1.0, new_text)
                        else:
                            # Добавляем новое слово
                            self.neuro_question.insert(tk.END, text_to_add + " ")
                    else:
                        # Добавляем как новое слово
                        self.neuro_question.insert(tk.END, text_to_add + " ")

                self.neuro_question.see(tk.END)

            # Устанавливаем callback для финального текста
            def final_callback(text):
                if text.strip():
                    # Обновляем статус
                    if hasattr(self, 'voice_status_label'):
                        self.voice_status_label.config(text=f"✅: {text[:30]}...")

            self.advanced_voice_manager.set_partial_text_callback(partial_callback)
            self.advanced_voice_manager.set_text_callback(final_callback)

            # Начинаем непрерывную запись
            self.advanced_voice_manager.start_continuous_recording(self.neuro_question)

            if self.app_logger:
                self.app_logger.log_voice_action("start", "Начат улучшенный голосовой ввод (реальное время)")

            self.status_bar.config(text="🎤 Голосовой ввод (реальное время)...")
        else:
            # Останавливаем запись
            self.voice_button.config(text="🎤 Голос (реальное время)")
            self.is_recording_voice = False

            final_text = self.advanced_voice_manager.stop_recording()

            # Обновляем статус
            if hasattr(self, 'voice_status_label'):
                self.voice_status_label.config(text=f"✅ Готово")

            if self.app_logger:
                self.app_logger.log_voice_action("stop", f"Завершен улучшенный голосовой ввод: {final_text[:50]}...")

            self.status_bar.config(text="Готов к работе")

    def toggle_voice_input(self):
        """Переключение базового голосового ввода"""
        if not VOICE_AVAILABLE or not self.voice_manager:
            messagebox.showwarning("Голосовой ввод", "Голосовой ввод недоступен. Установите speechrecognition.")
            return

        if not self.is_recording_voice:
            # Начинаем запись
            self.voice_button.config(text="⏹️ Остановить запись", style="Accent.TButton")
            self.is_recording_voice = True

            # Устанавливаем callback для обработки распознанного текста
            def voice_callback(text):
                # Вставляем распознанный текст в поле вопроса
                self.neuro_question.insert(tk.END, text + " ")
                self.neuro_question.see(tk.END)

            self.voice_manager.set_text_callback(voice_callback)
            self.voice_manager.start_recording()

            if self.app_logger:
                self.app_logger.log_voice_action("start", "Начат голосовой ввод вопроса")

            self.status_bar.config(text="🎤 Голосовая запись...")
        else:
            # Останавливаем запись
            self.voice_button.config(text="🎤 Голосовой ввод")
            self.is_recording_voice = False

            recognized_text = self.voice_manager.stop_recording()

            if self.app_logger:
                self.app_logger.log_voice_action("stop", f"Распознано: {recognized_text[:50]}...")

            self.status_bar.config(text="Готов к работе")

    def open_project_manager(self):
        """Открыть окно управления проектами"""
        try:
            if not self.db_manager:
                messagebox.showerror("Ошибка", "База данных не инициализирована")
                return

            ProjectManagerWindow(self.root, self.db_manager, self.app_logger)

            if self.app_logger:
                self.app_logger.log_ui_action("open_project_manager", "Открыто окно управления проектами")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть управление проектами: {e}")
            if self.app_logger:
                self.app_logger.log_error(f"Ошибка открытия управления проектами: {e}")

    def open_file_manager(self):
        """Открыть управление файлами текущего проекта"""
        # Проверяем и устанавливаем current_project_id если нужно
        if not self.current_project_id and self.project_path and self.db_manager:
            self.current_project_id = self.db_manager.get_or_create_project(str(self.project_path))

        if not self.current_project_id:
            messagebox.showwarning("Внимание", "Сначала откройте проект")
            return

        try:
            # Создаем простое окно управления файлами
            file_window = tk.Toplevel(self.root)
            file_window.title("Управление файлами")
            file_window.geometry("800x600")
            file_window.transient(self.root)

            # Получаем файлы проекта
            files = self.file_tracker.get_tracked_files(self.current_project_id)

            # Создаем интерфейс
            ttk.Label(file_window, text=f"Файлы проекта (ID: {self.current_project_id})",
                     font=("Arial", 12, "bold")).pack(pady=10)

            # Дерево файлов
            columns = ("file_path", "description", "tags", "updated")
            files_tree = ttk.Treeview(file_window, columns=columns, show="tree headings")
            files_tree.heading("#0", text="ID")
            files_tree.heading("file_path", text="Файл")
            files_tree.heading("description", text="Описание")
            files_tree.heading("tags", text="Теги")
            files_tree.heading("updated", text="Обновлен")

            files_tree.column("#0", width=50)
            files_tree.column("file_path", width=250)
            files_tree.column("description", width=150)
            files_tree.column("tags", width=100)
            files_tree.column("updated", width=120)

            # Добавляем файлы
            for file_info in files:
                tags_str = ', '.join(file_info.get('tags', []))
                files_tree.insert("", "end", text=str(file_info['id']),
                               values=(file_info['file_path'],
                                      file_info.get('description', ''),
                                      tags_str,
                                      file_info['updated_at'][:16] if file_info['updated_at'] else ""))

            files_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

            # Кнопки
            button_frame = ttk.Frame(file_window)
            button_frame.pack(fill=tk.X, padx=10, pady=10)

            ttk.Button(button_frame, text="🔍 Автообнаружение",
                      command=lambda: self.auto_discover_files_for_window(file_window)).pack(side=tk.LEFT, padx=2)
            ttk.Button(button_frame, text="🔄 Обновить",
                      command=lambda: self.refresh_files_for_window(file_window)).pack(side=tk.LEFT, padx=2)
            ttk.Button(button_frame, text="Закрыть",
                      command=file_window.destroy).pack(side=tk.RIGHT, padx=2)

            if self.app_logger:
                self.app_logger.log_ui_action("open_file_manager", f"Проект {self.current_project_id}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть управление файлами: {e}")
            if self.app_logger:
                self.app_logger.log_error(f"Ошибка открытия управления файлами: {e}")

    def auto_discover_files(self):
        """Автообнаружение файлов для текущего проекта"""
        # Проверяем и устанавливаем current_project_id если нужно
        if not self.current_project_id and self.project_path and self.db_manager:
            self.current_project_id = self.db_manager.get_or_create_project(str(self.project_path))

        if not self.current_project_id:
            messagebox.showwarning("Внимание", "Сначала откройте проект")
            return

        try:
            count = self.file_tracker.auto_discover_files(self.current_project_id)
            messagebox.showinfo("Успех", f"Обнаружено {count} файлов")

            if self.app_logger:
                self.app_logger.log_ui_action("auto_discover_files", f"Проект {self.current_project_id}, файлов: {count}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка автообнаружения файлов: {e}")
            if self.app_logger:
                self.app_logger.log_error(f"Ошибка автообнаружения файлов: {e}")

    def auto_discover_files_for_window(self, window):
        """Автообнаружение файлов для окна"""
        if not self.current_project_id:
            messagebox.showwarning("Внимание", "Сначала откройте проект")
            return

        try:
            count = self.file_tracker.auto_discover_files(self.current_project_id)
            messagebox.showinfo("Успех", f"Обнаружено {count} файлов")

            # Обновляем окно
            window.destroy()
            self.open_file_manager()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка автообнаружения файлов: {e}")

    def refresh_files_for_window(self, window):
        """Обновление файлов для окна"""
        window.destroy()
        self.open_file_manager()

    def show_project_stats(self):
        """Показать статистику проекта"""
        # Проверяем и устанавливаем current_project_id если нужно
        if not self.current_project_id and self.project_path and self.db_manager:
            self.current_project_id = self.db_manager.get_or_create_project(str(self.project_path))

        if not self.current_project_id:
            messagebox.showwarning("Внимание", "Сначала откройте проект")
            return

        try:
            project_stats = self.project_manager.get_project_stats(self.current_project_id)
            file_stats = self.file_tracker.get_file_stats(self.current_project_id)

            stats_text = "=== СТАТИСТИКА ПРОЕКТА ===\n\n"
            stats_text += f"ID проекта: {self.current_project_id}\n"
            stats_text += f"Отслеживаемых файлов: {project_stats.get('tracked_files', 0)}\n"
            stats_text += f"Сообщений в чате: {project_stats.get('chat_messages', 0)}\n"
            stats_text += f"Git коммитов: {project_stats.get('git_commits', 0)}\n"
            stats_text += f"Размер контекста: {project_stats.get('context_size', 0)} байт\n\n"

            stats_text += "=== СТАТИСТИКА ФАЙЛОВ ===\n\n"
            stats_text += f"Всего файлов: {file_stats.get('total_files', 0)}\n"
            stats_text += f"Общий размер: {file_stats.get('total_size', 0)} байт\n\n"

            if file_stats.get('extensions'):
                stats_text += "Расширения:\n"
                for ext, count in file_stats['extensions'].items():
                    stats_text += f"  {ext}: {count}\n"

            # Показываем в отдельном окне
            stats_window = tk.Toplevel(self.root)
            stats_window.title("Статистика проекта")
            stats_window.geometry("400x500")

            from tkinter import scrolledtext
            text_widget = scrolledtext.ScrolledText(stats_window, wrap=tk.WORD)
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text_widget.insert(1.0, stats_text)
            text_widget.config(state=tk.DISABLED)

            if self.app_logger:
                self.app_logger.log_ui_action("show_project_stats", f"Проект {self.current_project_id}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка получения статистики: {e}")
            if self.app_logger:
                self.app_logger.log_error(f"Ошибка получения статистики: {e}")

    def extract_and_save_tech_stack(self):
        """Извлечь технологический стек из проекта и занести в БД"""
        if not self.current_project_id and self.project_path and self.db_manager:
            self.current_project_id = self.db_manager.get_or_create_project(str(self.project_path))

        if not self.current_project_id or not self.project_path:
            messagebox.showwarning("Внимание", "Сначала откройте проект")
            return

        self.status_bar.config(text="Анализ технологического стека...")

        def _run():
            try:
                from shared.tech_stack_detector import TechStackDetector
                detector = TechStackDetector(str(self.project_path))
                result = detector.detect_all()

                items_saved = 0
                # Очищаем старые данные
                self.db_manager.conn.execute(
                    "DELETE FROM tech_stack WHERE project_id = ?", (self.current_project_id,)
                )

                for category, items in result.items():
                    for item in items:
                        name = item.get("name", "")
                        version = item.get("version", "")
                        confidence = item.get("confidence", 0.8)
                        if name:
                            try:
                                self.db_manager.conn.execute(
                                    """INSERT INTO tech_stack
                                       (project_id, technology, version, detected_by, confidence)
                                       VALUES (?, ?, ?, ?, ?)""",
                                    (self.current_project_id, name, version, category, confidence)
                                )
                                items_saved += 1
                            except Exception:
                                pass

                self.db_manager.conn.commit()

                # Обновляем описание проекта
                tech_summary = ", ".join(
                    item.get("name", "")
                    for items in result.values()
                    for item in items
                    if item.get("name")
                )
                if tech_summary:
                    try:
                        self.db_manager.conn.execute(
                            "UPDATE projects SET description = ? WHERE id = ?",
                            (f"Стек: {tech_summary[:300]}", self.current_project_id)
                        )
                        self.db_manager.conn.commit()
                    except Exception:
                        pass

                self.root.after(0, lambda: self.status_bar.config(
                    text=f"Стек технологий обновлён: {items_saved} записей"
                ))
                self.root.after(0, lambda: self._show_tech_stack_result(result))

            except Exception as e:
                self.logger.error(f"Ошибка анализа стека: {e}")
                self.root.after(0, lambda: self.status_bar.config(
                    text=f"Ошибка анализа стека: {e}"
                ))

        threading.Thread(target=_run, daemon=True).start()

    def _show_tech_stack_result(self, result: dict):
        """Показать результаты анализа стека"""
        win = tk.Toplevel(self.root)
        win.title("Технологический стек проекта")
        win.geometry("520x460")
        win.transient(self.root)

        c = self.colors
        win.configure(bg=c["cream"])

        ttk.Label(win, text="🔬 Технологический стек", font=("Segoe UI", 13, "bold")).pack(pady=10)

        from tkinter import scrolledtext
        txt = scrolledtext.ScrolledText(win, font=("Segoe UI", 10), wrap=tk.WORD,
                                        bg=c["cream_soft"], fg=c["ink"], relief=tk.FLAT,
                                        padx=10, pady=8)
        txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        for category, items in result.items():
            if items:
                txt.insert(tk.END, f"\n{'='*40}\n{category.upper()}\n{'='*40}\n")
                for item in items:
                    name = item.get("name", "")
                    version = item.get("version", "")
                    conf = int(item.get("confidence", 0) * 100)
                    ver_str = f" ({version})" if version else ""
                    txt.insert(tk.END, f"  \u2022 {name}{ver_str}  [{conf}%]\n")

        txt.config(state=tk.DISABLED)

        ttk.Button(win, text="Закрыть", command=win.destroy,
                   style="Accent.TButton").pack(pady=8)

    def open_project_by_path(self, project_path):
        """Открыть проект по пути"""
        try:
            self.project_path = Path(project_path)

            # Инициализация новой системы баз данных
            if self.db_manager:
                self.current_project_id = self.db_manager.get_or_create_project(str(self.project_path))
                self.git_manager = GitManager(str(self.project_path), self.db_manager)

                # Обновляем Git контекст
                if self.git_manager.is_git_repo:
                    threading.Thread(target=self.git_manager.update_git_context, args=(self.current_project_id,), daemon=True).start()

            # Инициализация чата с sqlite3
            self.chat_manager = ChatManager(self.db_manager)

            # Сохраняем старую систему для совместимости
            self.project_context = ProjectContext(str(self.project_path))
            self.project_context.update_context("project_created", f"Проект открыт в {project_path}")

            self.refresh_file_tree()
            self.status_bar.config(text=f"Проект: {self.project_path.name}")

            # Отправляем контекст в нейросеть
            if self.ollama_manager:
                threading.Thread(target=self.send_context_to_neuro, daemon=True).start()

            if self.app_logger:
                self.app_logger.log_project_open(str(self.project_path), self.current_project_id)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть проект: {e}")
            if self.app_logger:
                self.app_logger.log_error(f"Ошибка открытия проекта: {e}")

    def add_file_to_tracking(self):
        """Добавить файл в отслеживание"""
        if not self.current_file:
            messagebox.showwarning("Внимание", "Нет открытого файла")
            return

        if not self.ensure_project_selected():
            return

        try:
            file_path = str(self.current_file.relative_to(self.project_path))

            # Проверяем, не отслеживается ли уже файл
            cursor = self.db_manager.conn.execute(
                "SELECT id FROM files_tracking WHERE project_id = ? AND file_path = ?",
                (self.current_project_id, file_path)
            )
            if cursor.fetchone():
                messagebox.showinfo("Информация", "Файл уже отслеживается")
                return

            # Добавляем файл в отслеживание
            self.db_manager.conn.execute(
                """
                INSERT INTO files_tracking (project_id, file_path, is_tracking)
                VALUES (?, ?, ?)
                """,
                (self.current_project_id, file_path, True)
            )
            self.db_manager.conn.commit()

            self.refresh_tracking_list()
            messagebox.showinfo("Успех", f"Файл {file_path} добавлен в отслеживание")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось добавить файл в отслеживание: {e}")

    def remove_file_from_tracking(self):
        """Удалить файл из отслеживания"""
        selection = self.tracking_listbox.curselection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите файл для удаления")
            return

        if not self.ensure_project_selected():
            return

        try:
            selected_file = self.tracking_listbox.get(selection[0])
            file_path = selected_file.split(" | ")[0]  # Получаем только путь

            # Удаляем файл из отслеживания
            self.db_manager.conn.execute(
                "DELETE FROM files_tracking WHERE project_id = ? AND file_path = ?",
                (self.current_project_id, file_path)
            )
            self.db_manager.conn.commit()

            self.refresh_tracking_list()
            messagebox.showinfo("Успех", f"Файл {file_path} удален из отслеживания")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось удалить файл из отслеживания: {e}")

    def refresh_tracking_list(self):
        """Обновить список отслеживаемых файлов"""
        if not self.current_project_id:
            return

        try:
            # Очищаем список
            self.tracking_listbox.delete(0, tk.END)

            # Получаем отслеживаемые файлы
            cursor = self.db_manager.conn.execute(
                """
                SELECT file_path, line_ranges, created
                FROM files_tracking
                WHERE project_id = ? AND is_tracking = TRUE
                ORDER BY created DESC
                """,
                (self.current_project_id,)
            )

            for row in cursor.fetchall():
                file_path = row['file_path']
                line_ranges = row['line_ranges'] or "все строки"
                last_updated = row['created'] or "никогда"

                display_text = f"{file_path} | {line_ranges} | {last_updated}"
                self.tracking_listbox.insert(tk.END, display_text)

            # Обновляем статистику
            self.update_project_stats()

        except Exception as e:
            self.logger.error(f"Ошибка обновления списка отслеживания: {e}")

    def ensure_project_selected(self):
        """Проверка и установка выбранного проекта"""
        if not self.current_project_id and self.project_path and self.db_manager:
            self.current_project_id = self.db_manager.get_or_create_project(str(self.project_path))

        if not self.current_project_id:
            messagebox.showwarning("Внимание", "Сначала откройте проект")
            return False
        return True

    def update_project_stats(self):
        """Обновить статистику проекта"""
        if not self.ensure_project_selected():
            return

        try:
            stats_text = "📊 Статистика проекта\n"
            stats_text += "=" * 30 + "\n\n"

            # Информация о проекте
            cursor = self.db_manager.conn.execute(
                "SELECT name, path, created, last_accessed FROM projects WHERE id = ?",
                (self.current_project_id,)
            )
            project = cursor.fetchone()

            if project:
                stats_text += f"📁 Название: {project['name']}\n"
                stats_text += f"📍 Путь: {project['path']}\n"
                stats_text += f"📅 Создан: {project['created']}\n"
                stats_text += f"👁️ Доступ: {project['last_accessed']}\n\n"
            else:
                stats_text += "📁 Проект не найден в базе данных\n\n"

            # Статистика файлов
            try:
                cursor = self.db_manager.conn.execute(
                    "SELECT COUNT(*) as count FROM files_tracking WHERE project_id = ? AND is_tracking = TRUE",
                    (self.current_project_id,)
                )
                tracked_files = cursor.fetchone()['count']
                stats_text += f"📄 Отслеживаемых файлов: {tracked_files}\n"
            except:
                stats_text += f"📄 Отслеживаемых файлов: -\n"

            # Статистика чата
            try:
                cursor = self.db_manager.conn.execute(
                    "SELECT COUNT(*) as count FROM chat_messages WHERE project_id = ?",
                    (self.current_project_id,)
                )
                chat_messages = cursor.fetchone()['count']
                stats_text += f"💬 Сообщений в чате: {chat_messages}\n"
            except:
                stats_text += f"💬 Сообщений в чате: -\n"

            # Статистика Git
            if hasattr(self, 'git_manager') and self.git_manager.is_git_repo:
                try:
                    cursor = self.db_manager.conn.execute(
                        "SELECT COUNT(*) as count FROM git_commits WHERE project_id = ?",
                        (self.current_project_id,)
                    )
                    git_commits = cursor.fetchone()['count']
                    stats_text += f"🌿 Git коммитов: {git_commits}\n"
                except:
                    stats_text += f"🌿 Git коммитов: -\n"
            else:
                stats_text += f"🌿 Git: репозиторий не найден\n"

            # Дополнительная информация
            stats_text += f"\n📋 ID проекта: {self.current_project_id}\n"
            stats_text += f"🔧 Путь к проекту: {self.project_path}\n"

            # Обновляем текстовое поле
            if hasattr(self, 'stats_text'):
                self.stats_text.config(state=tk.NORMAL)
                self.stats_text.delete("1.0", tk.END)
                self.stats_text.insert("1.0", stats_text)
                self.stats_text.config(state=tk.DISABLED)

        except Exception as e:
            self.logger.error(f"Ошибка обновления статистики: {e}")
            # Показываем ошибку в статистике
            if hasattr(self, 'stats_text'):
                self.stats_text.config(state=tk.NORMAL)
                self.stats_text.delete("1.0", tk.END)
                self.stats_text.insert("1.0", f"Ошибка загрузки статистики: {e}")
                self.stats_text.config(state=tk.DISABLED)

    def update_git_info(self):
        """Обновить Git информацию"""
        if not hasattr(self, 'git_manager') or not self.git_manager.is_git_repo:
            self.git_text.config(state=tk.NORMAL)
            self.git_text.delete("1.0", tk.END)
            self.git_text.insert("1.0", "🌿 Git репозиторий не найден")
            self.git_text.config(state=tk.DISABLED)
            return

        try:
            git_info = "🌿 Git информация\n"
            git_info += "=" * 30 + "\n\n"

            # Текущая ветка
            current_branch = self.git_manager.get_current_branch()
            git_info += f"📍 Текущая ветка: {current_branch}\n"

            # Удаленный репозиторий
            remote_url = self.git_manager.get_remote_url()
            if remote_url:
                git_info += f"🔗 Удаленный репозиторий: {remote_url}\n"

            # Статус
            status = self.git_manager.get_git_status()
            git_info += f"📊 Статус: {'Чистый' if status['is_clean'] else 'Есть изменения'}\n"

            if not status['is_clean']:
                git_info += f"📝 Измененные файлы: {len(status['modified'])}\n"
                git_info += f"➕ Новые файлы: {len(status['untracked'])}\n"

            # Последние коммиты
            git_info += "\n📜 Последние коммиты:\n"
            commits = self.git_manager.get_commits(5)
            for i, commit in enumerate(commits, 1):
                git_info += f"{i}. {commit['commit_hash'][:8]} - {commit['message'][:50]}...\n"
                git_info += f"   👤 {commit['author']} - {commit['date']}\n\n"

            # Обновляем текстовое поле
            self.git_text.config(state=tk.NORMAL)
            self.git_text.delete("1.0", tk.END)
            self.git_text.insert("1.0", git_info)
            self.git_text.config(state=tk.DISABLED)

        except Exception as e:
            self.logger.error(f"Ошибка обновления Git информации: {e}")

    def quit_app(self):
        """Выход из приложения"""
        if self.current_file and self.file_modified:
            result = messagebox.askyesno("Несохраненные изменения",
                                       f"Сохранить изменения в файле {self.current_file.name} перед выходом?")
            if result:
                self.save_current_file()

        # Закрытие ресурсов
        if self.db_manager:
            self.db_manager.close()
        if self.voice_manager:
            self.voice_manager.cleanup()
        if self.advanced_voice_manager:
            self.advanced_voice_manager.cleanup()

        self.root.quit()
        self.root.destroy()

    def setup_hotkeys(self):
        """Горячие клавиши — только те, что не конфликтуют с Text-виджетами на уровне root"""
        # Ctrl+S и Ctrl+Q — не конфликтуют с Text-виджетами
        self.root.bind('<Control-s>', lambda e: self.save_current_file())
        self.root.bind('<Control-S>', lambda e: self.save_current_file())
        self.root.bind('<Control-q>', lambda e: self.quit_app())
        # Ctrl+M — микрофон (Win+M перехватывается Windows, используем Ctrl+M)
        self.root.bind('<Control-m>', self.toggle_microphone_hotkey)
        self.root.bind('<Control-M>', self.toggle_microphone_hotkey)
        # Ctrl+A на уровне root для fallback (Entry и др.)
        self.root.bind('<Control-a>', self.select_all_text)
        self.root.bind('<Control-A>', self.select_all_text)

    def _select_all_in(self, widget, event=None):
        """Выделить весь текст в конкретном виджете"""
        try:
            widget.tag_add(tk.SEL, "1.0", tk.END)
            widget.mark_set(tk.INSERT, tk.END)
            widget.see(tk.INSERT)
        except Exception:
            pass
        return "break"

    def _redo_in(self, widget, event=None):
        """Redo в конкретном виджете"""
        try:
            widget.edit_redo()
        except Exception:
            pass
        return "break"

    def select_all_text(self, event):
        """Выделить весь текст в активном виджете"""
        try:
            widget = self.root.focus_get()
            if hasattr(widget, 'tag_add') and hasattr(widget, 'get'):
                widget.tag_add(tk.SEL, "1.0", tk.END)
                widget.mark_set(tk.INSERT, "1.0")
                widget.see(tk.INSERT)
                return "break"
        except:
            pass
        return None

    def toggle_microphone_hotkey(self, event=None):
        """Переключить микрофон по горячей клавише (Win+M / Ctrl+M)"""
        try:
            if ADVANCED_VOICE_AVAILABLE and hasattr(self, 'voice_button'):
                self.toggle_advanced_voice_input()
            elif VOICE_AVAILABLE and hasattr(self, 'voice_button'):
                self.toggle_voice_input()
            else:
                self.status_bar.config(text="Голосовой ввод недоступен (установите speechrecognition)")
        except Exception as e:
            self.logger.error(f"Ошибка переключения микрофона: {e}")
        return "break"

    def redo_text(self, event):
        """Вернуть текст вперед (redo)"""
        try:
            widget = self.root.focus_get()
            if hasattr(widget, 'edit_redo'):
                widget.edit_redo()
                return "break"
        except:
            pass
        return None

    def undo_text(self, event):
        """Вернуть текст назад (undo)"""
        try:
            widget = self.root.focus_get()
            if hasattr(widget, 'edit_undo'):
                widget.edit_undo()
                return "break"
        except:
            pass
        return None

    def copy_text(self, event=None):
        """Копировать выделенный текст"""
        try:
            widget = self.root.focus_get()
            if hasattr(widget, 'tag_ranges'):
                if widget.tag_ranges(tk.SEL):
                    text = widget.get(tk.SEL_FIRST, tk.SEL_LAST)
                    self.root.clipboard_clear()
                    self.root.clipboard_append(text)
        except Exception:
            pass
        return None  # не прерываем — позволяем tk обработать

    def paste_text(self, event=None):
        """Вставить текст из буфера"""
        try:
            widget = self.root.focus_get()
            if hasattr(widget, 'insert') and hasattr(widget, 'tag_ranges'):
                try:
                    text = self.root.clipboard_get()
                    # Удаляем выделенное, если есть
                    if widget.tag_ranges(tk.SEL):
                        widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
                    widget.insert(tk.INSERT, text)
                except tk.TclError:
                    pass
        except Exception:
            pass
        return "break"

    def run(self):
        """Запуск приложения"""
        self.root.mainloop()

if __name__ == "__main__":
    app = StartIDE()
    app.run()
