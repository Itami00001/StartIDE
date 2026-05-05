import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import sys
import os
from pathlib import Path
import threading
import logging

# Добавляем путь к shared модулям
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from shared.ollama_manager import OllamaManager
from shared.project_context import ProjectContext
from shared.shared_chat_manager import SharedChatManager

class StartIDE:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("StartIDE")
        self.root.geometry("1200x800")
        
        # Переменные проекта
        self.project_path = None
        self.ollama_manager = None
        self.project_context = None
        self.shared_chat_manager = None
        self.last_chat_timestamp = None
        
        # Настройка логирования
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Привязка горячих клавиш
        self.root.bind('<Control-s>', lambda e: self.save_current_file())
        self.root.bind('<Control-S>', lambda e: self.save_current_file())
        self.root.bind('<Control-q>', lambda e: self.quit_app())
        
        # Создание интерфейса
        self.setup_ui()
        
        # Попытка подключения к Ollama
        self.init_ollama()
    
    def setup_ui(self):
        """Создание интерфейса"""
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
        
        # Виджет меню
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Вид", menu=view_menu)
        view_menu.add_command(label="Показать/Скрыть Нейро", command=self.toggle_neuro_panel)
        
        # Основная панель
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # Левая панель (проводник файлов)
        self.left_frame = ttk.Frame(main_paned, width=250)
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
        
        # Статус бар
        self.status_bar = ttk.Label(self.root, text="Готов к работе", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_file_explorer(self):
        """Настройка проводника файлов"""
        # Заголовок
        ttk.Label(self.left_frame, text="Проводник файлов", font=("Arial", 10, "bold")).pack(pady=5)
        
        # Дерево файлов
        self.file_tree = ttk.Treeview(self.left_frame, columns=("size", "type"), show="tree")
        self.file_tree.heading("#0", text="Файлы")
        self.file_tree.column("#0", width=200)
        self.file_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Контекстное меню
        self.file_tree.bind("<Button-3>", self.show_file_context_menu)
        self.file_tree.bind("<Double-1>", self.open_file_in_editor)
        
        # Кнопки управления
        button_frame = ttk.Frame(self.left_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Создать файл", command=self.create_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Создать папку", command=self.create_folder).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Обновить", command=self.refresh_file_tree).pack(side=tk.LEFT, padx=2)
    
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
        
        ttk.Separator(toolbar_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        self.file_path_label = ttk.Label(toolbar_frame, text="Файл не открыт", foreground="gray")
        self.file_path_label.pack(side=tk.LEFT, padx=5)
        
        # Текстовое поле с прокруткой
        text_container = ttk.Frame(self.editor_tab)
        text_container.pack(fill=tk.BOTH, expand=True)
        
        self.editor_text = tk.Text(text_container, wrap=tk.WORD, font=("Consolas", 10), undo=True)
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
    
    def setup_chat_tab(self):
        """Настройка вкладки общего чата"""
        # Заголовок
        ttk.Label(self.chat_tab, text="💬 Общий чат проекта", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Кнопки управления чатом
        chat_controls = ttk.Frame(self.chat_tab)
        chat_controls.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(chat_controls, text="🔄 Обновить чат", command=self.refresh_chat).pack(side=tk.LEFT, padx=2)
        ttk.Button(chat_controls, text="🗑️ Очистить чат", command=self.clear_chat).pack(side=tk.LEFT, padx=2)
        ttk.Button(chat_controls, text="📤 Отправить файл в чат", command=self.send_current_file_to_chat).pack(side=tk.LEFT, padx=2)
        
        # Поле для сообщения
        msg_frame = ttk.LabelFrame(self.chat_tab, text="Сообщение")
        msg_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.chat_message = tk.Text(msg_frame, height=3, wrap=tk.WORD)
        self.chat_message.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(msg_frame, text="📨 Отправить сообщение", command=self.send_chat_message).pack(pady=5)
        
        # История чата
        chat_history_frame = ttk.LabelFrame(self.chat_tab, text="История чата")
        chat_history_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.chat_history = scrolledtext.ScrolledText(chat_history_frame, height=20, wrap=tk.WORD, state=tk.DISABLED)
        self.chat_history.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Автообновление чата каждые 5 секунд
        self.schedule_chat_refresh()
    
    def setup_neuro_panel(self):
        """Настройка панели Нейро"""
        # Заголовок
        ttk.Label(self.right_frame, text="🧠 Нейро", font=("Arial", 10, "bold")).pack(pady=5)
        
        # Статус подключения
        self.neuro_status_label = ttk.Label(self.right_frame, text="Статус: Не подключено", foreground="red")
        self.neuro_status_label.pack(pady=5)
        
        # Чат с нейросетью
        ttk.Label(self.right_frame, text="Вопрос к нейросети:").pack(pady=5)
        
        self.neuro_question = tk.Text(self.right_frame, height=3, wrap=tk.WORD)
        self.neuro_question.pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Button(self.right_frame, text="Отправить вопрос", command=self.ask_neuro).pack(pady=5)
        
        # Ответ нейросети
        ttk.Label(self.right_frame, text="Ответ:").pack(pady=5)
        
        self.neuro_response = tk.Text(self.right_frame, height=15, wrap=tk.WORD, state=tk.DISABLED)
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
    
    def new_project(self):
        """Создание нового проекта"""
        folder_path = filedialog.askdirectory(title="Выберите папку для проекта")
        if folder_path:
            self.project_path = Path(folder_path)
            self.project_context = ProjectContext(str(self.project_path))
            self.shared_chat_manager = SharedChatManager(str(self.project_path))
            self.project_context.update_context("project_created", f"Проект создан в {folder_path}")
            
            self.refresh_file_tree()
            self.status_bar.config(text=f"Проект: {self.project_path.name}")
            
            # Отправляем контекст в нейросеть
            if self.ollama_manager:
                threading.Thread(target=self.send_context_to_neuro, daemon=True).start()
    
    def open_project(self):
        """Открытие существующего проекта"""
        folder_path = filedialog.askdirectory(title="Выберите папку проекта")
        if folder_path:
            self.project_path = Path(folder_path)
            self.project_context = ProjectContext(str(self.project_path))
            self.shared_chat_manager = SharedChatManager(str(self.project_path))
            
            self.refresh_file_tree()
            self.status_bar.config(text=f"Проект: {self.project_path.name}")
    
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
        """Обновление истории чата"""
        if not self.shared_chat_manager:
            return
        
        try:
            messages = self.shared_chat_manager.get_messages_since(self.last_chat_timestamp)
            
            if messages:
                self.chat_history.config(state=tk.NORMAL)
                
                for msg in messages:
                    timestamp = msg.get("timestamp", "")[11:19]
                    sender = msg.get("sender", "Unknown")
                    msg_type = msg.get("type", "text")
                    content = msg.get("content", "")
                    file_name = msg.get("file_name", "")
                    
                    # Форматируем сообщение
                    if msg_type == "file" or msg_type == "code_analysis":
                        self.chat_history.insert(tk.END, f"[{timestamp}] {sender} отправил файл:\n")
                        if file_name:
                            self.chat_history.insert(tk.END, f"  📄 {file_name}\n")
                        if content:
                            self.chat_history.insert(tk.END, f"  💬 {content}\n")
                    else:
                        self.chat_history.insert(tk.END, f"[{timestamp}] {sender}:\n")
                        self.chat_history.insert(tk.END, f"  💬 {content}\n")
                    
                    self.chat_history.insert(tk.END, "-" * 50 + "\n")
                    
                    # Обновляем последний таймстамп
                    if msg.get("timestamp", "") > (self.last_chat_timestamp or ""):
                        self.last_chat_timestamp = msg.get("timestamp")
                
                self.chat_history.see(tk.END)  # Прокручиваем к последнему сообщению
                self.chat_history.config(state=tk.DISABLED)
                
        except Exception as e:
            self.logger.error(f"Ошибка обновления чата: {e}")
    
    def clear_chat(self):
        """Очистка чата"""
        if not self.shared_chat_manager:
            return
        
        if messagebox.askyesno("Подтверждение", "Очистить историю чата?"):
            self.shared_chat_manager.clear_chat()
            self.chat_history.config(state=tk.NORMAL)
            self.chat_history.delete(1.0, tk.END)
            self.chat_history.config(state=tk.DISABLED)
            self.last_chat_timestamp = None
            self.status_bar.config(text="Чат очищен")
    
    def send_chat_message(self):
        """Отправка текстового сообщения в чат"""
        if not self.shared_chat_manager:
            messagebox.showwarning("Внимание", "Сначала откройте проект")
            return
        
        message = self.chat_message.get(1.0, tk.END).strip()
        if not message:
            return
        
        success = self.shared_chat_manager.add_message(
            sender="StartIDE",
            message_type="text",
            content=message
        )
        
        if success:
            self.chat_message.delete(1.0, tk.END)
            self.refresh_chat()
            self.status_bar.config(text="Сообщение отправлено в чат")
        else:
            messagebox.showerror("Ошибка", "Не удалось отправить сообщение")
    
    def send_current_file_to_chat(self):
        """Отправка текущего файла в чат"""
        if not self.shared_chat_manager:
            messagebox.showwarning("Внимание", "Сначала откройте проект")
            return
        
        if not self.current_file:
            messagebox.showwarning("Внимание", "Сначала откройте файл")
            return
        
        try:
            # Читаем содержимое файла
            with open(self.current_file, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Спрашиваем вопрос для анализа
            question = tk.simpledialog.askstring(
                "Отправка файла в чат",
                "Введите вопрос или комментарий к файлу:",
                initialvalue="Проанализируй этот файл"
            )
            
            if question is None:  # Пользователь отменил
                return
            
            # Отправляем в чат
            success = self.shared_chat_manager.send_file_for_analysis(
                sender="StartIDE",
                file_path=str(self.current_file),
                question=question
            )
            
            if success:
                self.refresh_chat()
                self.status_bar.config(text=f"Файл {self.current_file.name} отправлен в чат")
                
                # Переключаемся на вкладку чата
                self.center_notebook.select(self.chat_tab)
            else:
                messagebox.showerror("Ошибка", "Не удалось отправить файл")
                
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось отправить файл: {e}")
    
    def schedule_chat_refresh(self):
        """Планирование автоматического обновления чата"""
        if self.project_path:
            self.refresh_chat()
        
        # Планируем следующее обновление через 5 секунд
        self.root.after(5000, self.schedule_chat_refresh)
    
    def quit_app(self):
        """Выход из приложения"""
        if self.current_file and self.file_modified:
            result = messagebox.askyesno("Несохраненные изменения", 
                                       f"Сохранить изменения в файле {self.current_file.name} перед выходом?")
            if result:
                self.save_current_file()
        self.root.quit()
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()

if __name__ == "__main__":
    app = StartIDE()
    app.run()
