import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
import threading
import logging

class ProjectManagerWindow:
    """Окно управления проектами"""

    def __init__(self, parent, db_manager, app_logger=None):
        self.parent = parent
        self.db_manager = db_manager
        self.app_logger = app_logger
        self.logger = logging.getLogger(__name__)

        # Импортируем менеджеры
        from shared.project_manager import ProjectManager
        from shared.file_tracker import FileTracker

        _base_dir = Path(__file__).resolve().parent.parent
        self.project_manager = ProjectManager(str(_base_dir / "context"))
        self.file_tracker = FileTracker(str(_base_dir / "context"))

        # Создаем окно
        self.window = tk.Toplevel(parent)
        self.window.title("Управление проектами")
        self.window.geometry("900x700")
        self.window.transient(parent)
        self.window.grab_set()

        # Переменные
        self.projects_list = []
        self.selected_project = None
        self.current_project_id = None

        # Создаем интерфейс
        self.setup_ui()

        # Загружаем проекты
        self.load_projects()

        # Привязка событий
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        """Создание интерфейса"""
        # Главная панель
        main_paned = ttk.PanedWindow(self.window, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Левая панель - список проектов
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)

        # Правая панель - детали проекта
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=2)

        # Левая панель
        self.setup_projects_list(left_frame)

        # Правая панель
        self.setup_project_details(right_frame)

    def setup_projects_list(self, parent):
        """Настройка списка проектов"""
        # Заголовок
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(header_frame, text="Проекты", font=("Arial", 12, "bold")).pack(side=tk.LEFT)

        # Кнопки управления
        ttk.Button(header_frame, text="➕ Новый", command=self.create_project).pack(side=tk.RIGHT, padx=2)
        ttk.Button(header_frame, text="🔄 Обновить", command=self.load_projects).pack(side=tk.RIGHT, padx=2)

        # Поиск
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill=tk.X, padx=5, pady=2)

        ttk.Label(search_frame, text="Поиск:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Список проектов
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Treeview для проектов
        columns = ("name", "path", "updated")
        self.projects_tree = ttk.Treeview(list_frame, columns=columns, show="tree headings")
        self.projects_tree.heading("#0", text="ID")
        self.projects_tree.heading("name", text="Имя")
        self.projects_tree.heading("path", text="Путь")
        self.projects_tree.heading("updated", text="Обновлен")

        self.projects_tree.column("#0", width=50)
        self.projects_tree.column("name", width=150)
        self.projects_tree.column("path", width=200)
        self.projects_tree.column("updated", width=120)

        # Скроллбар
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.projects_tree.yview)
        self.projects_tree.configure(yscrollcommand=scrollbar.set)

        self.projects_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Контекстное меню
        self.projects_tree.bind("<Button-3>", self.show_project_context_menu)
        self.projects_tree.bind("<Double-1>", self.on_project_double_click)
        self.projects_tree.bind("<<TreeviewSelect>>", self.on_project_select)

        # Кнопки действий
        actions_frame = ttk.Frame(parent)
        actions_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(actions_frame, text="Открыть", command=self.open_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(actions_frame, text="Удалить", command=self.delete_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(actions_frame, text="Экспорт", command=self.export_project).pack(side=tk.LEFT, padx=2)

    def setup_project_details(self, parent):
        """Настройка деталей проекта"""
        # Notebook для вкладок
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Вкладка "Информация"
        info_frame = ttk.Frame(self.notebook)
        self.notebook.add(info_frame, text="📋 Информация")
        self.setup_info_tab(info_frame)

        # Вкладка "Файлы"
        files_frame = ttk.Frame(self.notebook)
        self.notebook.add(files_frame, text="📁 Файлы")
        self.setup_files_tab(files_frame)

        # Вкладка "Настройки"
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="⚙️ Настройки")
        self.setup_settings_tab(settings_frame)

    def setup_info_tab(self, parent):
        """Настройка вкладки информации"""
        # Основная информация
        info_frame = ttk.LabelFrame(parent, text="Основная информация")
        info_frame.pack(fill=tk.X, padx=5, pady=5)

        # Поля для редактирования
        fields = [
            ("Имя проекта:", "name"),
            ("Путь:", "path"),
            ("Описание:", "description"),
            ("Создан:", "created_at"),
            ("Обновлен:", "updated_at")
        ]

        self.info_vars = {}
        for i, (label, key) in enumerate(fields):
            ttk.Label(info_frame, text=label).grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)

            if key in ["created_at", "updated_at"]:
                # Только для чтения
                var = tk.StringVar()
                entry = ttk.Entry(info_frame, textvariable=var, state=tk.DISABLED)
            else:
                # Редактируемые поля
                var = tk.StringVar()
                entry = ttk.Entry(info_frame, textvariable=var)

            entry.grid(row=i, column=1, sticky=tk.EW, padx=5, pady=2)
            self.info_vars[key] = var

        info_frame.columnconfigure(1, weight=1)

        # Технологический стек
        tech_frame = ttk.LabelFrame(parent, text="Технологический стек")
        tech_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Список технологий
        tech_list_frame = ttk.Frame(tech_frame)
        tech_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.tech_listbox = tk.Listbox(tech_list_frame)
        tech_scrollbar = ttk.Scrollbar(tech_list_frame, orient=tk.VERTICAL, command=self.tech_listbox.yview)
        self.tech_listbox.configure(yscrollcommand=tech_scrollbar.set)

        self.tech_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tech_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Управление технологиями
        tech_controls = ttk.Frame(tech_frame)
        tech_controls.pack(fill=tk.X, padx=5, pady=5)

        self.tech_entry = ttk.Entry(tech_controls)
        self.tech_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        ttk.Button(tech_controls, text="➕", command=self.add_tech, width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(tech_controls, text="➖", command=self.remove_tech, width=3).pack(side=tk.LEFT, padx=2)

        # Кнопки сохранения
        save_frame = ttk.Frame(parent)
        save_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(save_frame, text="💾 Сохранить изменения", command=self.save_project_info).pack(side=tk.LEFT, padx=2)
        ttk.Button(save_frame, text="📊 Статистика", command=self.show_project_stats).pack(side=tk.LEFT, padx=2)

    def setup_files_tab(self, parent):
        """Настройка вкладки файлов"""
        # Панель инструментов
        toolbar = ttk.Frame(parent)
        toolbar.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(toolbar, text="🔍 Автообнаружение", command=self.auto_discover_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="➕ Добавить файл", command=self.add_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="➖ Удалить", command=self.remove_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔄 Обновить", command=self.refresh_files).pack(side=tk.LEFT, padx=2)

        # Список файлов
        files_frame = ttk.Frame(parent)
        files_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        columns = ("file_path", "description", "tags", "updated")
        self.files_tree = ttk.Treeview(files_frame, columns=columns, show="tree headings")
        self.files_tree.heading("#0", text="ID")
        self.files_tree.heading("file_path", text="Файл")
        self.files_tree.heading("description", text="Описание")
        self.files_tree.heading("tags", text="Теги")
        self.files_tree.heading("updated", text="Обновлен")

        self.files_tree.column("#0", width=50)
        self.files_tree.column("file_path", width=250)
        self.files_tree.column("description", width=150)
        self.files_tree.column("tags", width=100)
        self.files_tree.column("updated", width=120)

        # Скроллбар
        files_scrollbar = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=self.files_tree.yview)
        self.files_tree.configure(yscrollcommand=files_scrollbar.set)

        self.files_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        files_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Контекстное меню файлов
        self.files_tree.bind("<Button-3>", self.show_file_context_menu)
        self.files_tree.bind("<Double-1>", self.on_file_double_click)

    def setup_settings_tab(self, parent):
        """Настройка вкладки настроек"""
        # Настройки отслеживания
        tracking_frame = ttk.LabelFrame(parent, text="Настройки отслеживания")
        tracking_frame.pack(fill=tk.X, padx=5, pady=5)

        # Расширения файлов
        ttk.Label(tracking_frame, text="Расширения файлов (через запятую):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.extensions_var = tk.StringVar(value=".py,.js,.ts,.jsx,.tsx,.html,.css,.md,.txt,.json")
        ttk.Entry(tracking_frame, textvariable=self.extensions_var).grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)

        # Исключенные папки
        ttk.Label(tracking_frame, text="Исключенные папки (через запятую):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.exclude_folders_var = tk.StringVar(value="__pycache__,.git,.vscode,node_modules")
        ttk.Entry(tracking_frame, textvariable=self.exclude_folders_var).grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)

        tracking_frame.columnconfigure(1, weight=1)

        # Кнопки настроек
        settings_buttons = ttk.Frame(parent)
        settings_buttons.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(settings_buttons, text="💾 Сохранить настройки", command=self.save_settings).pack(side=tk.LEFT, padx=2)
        ttk.Button(settings_buttons, text="📥 Импорт", command=self.import_project).pack(side=tk.LEFT, padx=2)
        ttk.Button(settings_buttons, text="📤 Экспорт", command=self.export_project).pack(side=tk.LEFT, padx=2)

    def load_projects(self):
        """Загрузка списка проектов"""
        try:
            self.projects_list = self.project_manager.get_all_projects()

            # Очищаем дерево
            for item in self.projects_tree.get_children():
                self.projects_tree.delete(item)

            # Добавляем проекты
            for project in self.projects_list:
                self.projects_tree.insert("", "end", text=str(project['id']),
                                       values=(project['name'], project['path'],
                                              project['updated_at'][:16] if project['updated_at'] else ""))

            self.logger.info(f"Загружено {len(self.projects_list)} проектов")

        except Exception as e:
            self.logger.error(f"Ошибка загрузки проектов: {e}")
            messagebox.showerror("Ошибка", f"Не удалось загрузить проекты: {e}")

    def on_search(self, *args):
        """Поиск проектов"""
        query = self.search_var.get().strip()

        if not query:
            self.load_projects()
            return

        try:
            search_results = self.project_manager.search_projects(query)

            # Очищаем дерево
            for item in self.projects_tree.get_children():
                self.projects_tree.delete(item)

            # Добавляем результаты поиска
            for project in search_results:
                self.projects_tree.insert("", "end", text=str(project['id']),
                                       values=(project['name'], project['path'],
                                              project['updated_at'][:16] if project['updated_at'] else ""))

        except Exception as e:
            self.logger.error(f"Ошибка поиска проектов: {e}")

    def on_project_select(self, event=None):
        """Выбор проекта"""
        selection = self.projects_tree.selection()
        if not selection:
            self.selected_project = None
            self.current_project_id = None
            return

        item = self.projects_tree.item(selection[0])
        project_id = int(item['text'])

        # Получаем информацию о проекте
        project = self.project_manager.get_project(project_id)
        if project:
            self.selected_project = project
            self.current_project_id = project_id
            self.show_project_info(project)
            self.load_project_files(project_id)

    def show_project_info(self, project):
        """Отображение информации о проекте"""
        # Заполняем поля
        self.info_vars['name'].set(project.get('name', ''))
        self.info_vars['path'].set(project.get('path', ''))
        self.info_vars['description'].set(project.get('description', ''))
        self.info_vars['created_at'].set(project.get('created_at', '')[:16] if project.get('created_at') else '')
        self.info_vars['updated_at'].set(project.get('updated_at', '')[:16] if project.get('updated_at') else '')

        # Заполняем технологии
        self.tech_listbox.delete(0, tk.END)
        for tech in project.get('tech_stack', []):
            self.tech_listbox.insert(tk.END, tech)

    def load_project_files(self, project_id):
        """Загрузка файлов проекта"""
        try:
            files = self.file_tracker.get_tracked_files(project_id)

            # Очищаем дерево файлов
            for item in self.files_tree.get_children():
                self.files_tree.delete(item)

            # Добавляем файлы
            for file_info in files:
                tags_str = ', '.join(file_info.get('tags', []))
                self.files_tree.insert("", "end", text=str(file_info['id']),
                                       values=(file_info['file_path'],
                                              file_info.get('description', ''),
                                              tags_str,
                                              file_info['updated_at'][:16] if file_info['updated_at'] else ""))

        except Exception as e:
            self.logger.error(f"Ошибка загрузки файлов проекта: {e}")

    def create_project(self):
        """Создание нового проекта"""
        dialog = ProjectDialog(self.window, "Создание проекта")
        if dialog.result:
            try:
                project_id = self.project_manager.create_project(**dialog.result)
                if project_id:
                    self.load_projects()
                    messagebox.showinfo("Успех", f"Проект создан с ID: {project_id}")

                    if self.app_logger:
                        self.app_logger.log_ui_action("create_project", f"Проект {dialog.result['name']}")
                else:
                    messagebox.showerror("Ошибка", "Не удалось создать проект")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка создания проекта: {e}")

    def save_project_info(self):
        """Сохранение информации о проекте"""
        if not self.current_project_id:
            messagebox.showwarning("Внимание", "Проект не выбран")
            return

        try:
            # Собираем технологии
            tech_stack = []
            for i in range(self.tech_listbox.size()):
                tech_stack.append(self.tech_listbox.get(i))

            # Обновляем проект
            success = self.project_manager.update_project(
                self.current_project_id,
                name=self.info_vars['name'].get(),
                description=self.info_vars['description'].get(),
                tech_stack=tech_stack
            )

            if success:
                self.load_projects()
                messagebox.showinfo("Успех", "Информация о проекте обновлена")

                if self.app_logger:
                    self.app_logger.log_ui_action("update_project", f"Проект {self.current_project_id}")
            else:
                messagebox.showerror("Ошибка", "Не удалось обновить проект")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка обновления проекта: {e}")

    def delete_project(self):
        """Удаление проекта"""
        if not self.current_project_id:
            messagebox.showwarning("Внимание", "Проект не выбран")
            return

        if messagebox.askyesno("Подтверждение", f"Удалить проект '{self.selected_project['name']}'?"):
            try:
                success = self.project_manager.delete_project(self.current_project_id)
                if success:
                    self.load_projects()
                    self.clear_project_info()
                    messagebox.showinfo("Успех", "Проект удален")

                    if self.app_logger:
                        self.app_logger.log_ui_action("delete_project", f"Проект {self.current_project_id}")
                else:
                    messagebox.showerror("Ошибка", "Не удалось удалить проект")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка удаления проекта: {e}")

    def clear_project_info(self):
        """Очистка информации о проекте"""
        self.selected_project = None
        self.current_project_id = None

        for var in self.info_vars.values():
            var.set("")

        self.tech_listbox.delete(0, tk.END)

        # Очищаем файлы
        for item in self.files_tree.get_children():
            self.files_tree.delete(item)

    def add_tech(self):
        """Добавление технологии"""
        tech = self.tech_entry.get().strip()
        if tech:
            self.tech_listbox.insert(tk.END, tech)
            self.tech_entry.delete(0, tk.END)

    def remove_tech(self):
        """Удаление технологии"""
        selection = self.tech_listbox.curselection()
        if selection:
            self.tech_listbox.delete(selection[0])

    def auto_discover_files(self):
        """Автоматическое обнаружение файлов"""
        if not self.current_project_id:
            messagebox.showwarning("Внимание", "Проект не выбран")
            return

        try:
            extensions = [ext.strip() for ext in self.extensions_var.get().split(',') if ext.strip()]
            count = self.file_tracker.auto_discover_files(self.current_project_id, extensions)

            self.load_project_files(self.current_project_id)
            messagebox.showinfo("Успех", f"Обнаружено {count} файлов")

            if self.app_logger:
                self.app_logger.log_ui_action("auto_discover_files", f"Проект {self.current_project_id}, файлов: {count}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка обнаружения файлов: {e}")

    def add_file(self):
        """Добавление файла в отслеживание"""
        if not self.current_project_id:
            messagebox.showwarning("Внимание", "Проект не выбран")
            return

        file_path = filedialog.askopenfilename(
            title="Выберите файл для отслеживания",
            filetypes=[("Все файлы", "*.*")]
        )

        if file_path:
            try:
                success = self.file_tracker.add_file(self.current_project_id, file_path)
                if success:
                    self.load_project_files(self.current_project_id)
                    messagebox.showinfo("Успех", "Файл добавлен в отслеживание")
                else:
                    messagebox.showerror("Ошибка", "Не удалось добавить файл")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка добавления файла: {e}")

    def remove_file(self):
        """Удаление файла из отслеживания"""
        selection = self.files_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Файл не выбран")
            return

        item = self.files_tree.item(selection[0])
        file_path = item['values'][0]

        if messagebox.askyesno("Подтверждение", f"Удалить файл '{file_path}' из отслеживания?"):
            try:
                success = self.file_tracker.remove_file(self.current_project_id, file_path)
                if success:
                    self.load_project_files(self.current_project_id)
                    messagebox.showinfo("Успех", "Файл удален из отслеживания")
                else:
                    messagebox.showerror("Ошибка", "Не удалось удалить файл")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка удаления файла: {e}")

    def refresh_files(self):
        """Обновление списка файлов"""
        if self.current_project_id:
            self.load_project_files(self.current_project_id)

    def show_project_stats(self):
        """Показать статистику проекта"""
        if not self.current_project_id:
            messagebox.showwarning("Внимание", "Проект не выбран")
            return

        try:
            stats = self.project_manager.get_project_stats(self.current_project_id)
            file_stats = self.file_tracker.get_file_stats(self.current_project_id)

            stats_text = "=== СТАТИСТИКА ПРОЕКТА ===\n\n"
            stats_text += f"Отслеживаемых файлов: {stats.get('tracked_files', 0)}\n"
            stats_text += f"Сообщений в чате: {stats.get('chat_messages', 0)}\n"
            stats_text += f"Git коммитов: {stats.get('git_commits', 0)}\n"
            stats_text += f"Размер контекста: {stats.get('context_size', 0)} байт\n\n"

            stats_text += "=== СТАТИСТИКА ФАЙЛОВ ===\n\n"
            stats_text += f"Всего файлов: {file_stats.get('total_files', 0)}\n"
            stats_text += f"Общий размер: {file_stats.get('total_size', 0)} байт\n\n"

            if file_stats.get('extensions'):
                stats_text += "Расширения:\n"
                for ext, count in file_stats['extensions'].items():
                    stats_text += f"  {ext}: {count}\n"

            if file_stats.get('tags'):
                stats_text += "\nТеги:\n"
                for tag, count in file_stats['tags'].items():
                    stats_text += f"  {tag}: {count}\n"

            # Показываем в отдельном окне
            stats_window = tk.Toplevel(self.window)
            stats_window.title("Статистика проекта")
            stats_window.geometry("400x500")

            text_widget = scrolledtext.ScrolledText(stats_window, wrap=tk.WORD)
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text_widget.insert(1.0, stats_text)
            text_widget.config(state=tk.DISABLED)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка получения статистики: {e}")

    def export_project(self):
        """Экспорт проекта"""
        if not self.current_project_id:
            messagebox.showwarning("Внимание", "Проект не выбран")
            return

        file_path = filedialog.asksaveasfilename(
            title="Экспорт проекта",
            defaultextension=".json",
            filetypes=[("JSON файлы", "*.json"), ("Все файлы", "*.*")]
        )

        if file_path:
            try:
                success = self.project_manager.export_project(self.current_project_id, file_path)
                if success:
                    messagebox.showinfo("Успех", f"Проект экспортирован в {file_path}")

                    if self.app_logger:
                        self.app_logger.log_ui_action("export_project", f"Проект {self.current_project_id}")
                else:
                    messagebox.showerror("Ошибка", "Не удалось экспортировать проект")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка экспорта проекта: {e}")

    def import_project(self):
        """Импорт проекта"""
        file_path = filedialog.askopenfilename(
            title="Импорт проекта",
            filetypes=[("JSON файлы", "*.json"), ("Все файлы", "*.*")]
        )

        if file_path:
            try:
                project_id = self.project_manager.import_project(file_path)
                if project_id:
                    self.load_projects()
                    messagebox.showinfo("Успех", f"Проект импортирован с ID: {project_id}")

                    if self.app_logger:
                        self.app_logger.log_ui_action("import_project", f"Проект {project_id}")
                else:
                    messagebox.showerror("Ошибка", "Не удалось импортировать проект")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка импорта проекта: {e}")

    def open_project(self):
        """Открыть проект в StartIDE"""
        if not self.selected_project:
            messagebox.showwarning("Внимание", "Проект не выбран")
            return

        # Закрываем окно управления проектами
        self.on_close()

        # Открываем проект в родительском окне
        if hasattr(self.parent, 'open_project_by_path'):
            self.parent.open_project_by_path(self.selected_project['path'])

    def on_project_double_click(self, event):
        """Двойной клик по проекту"""
        self.open_project()

    def on_file_double_click(self, event):
        """Двойной клик по файлу"""
        selection = self.files_tree.selection()
        if selection and self.selected_project:
            item = self.files_tree.item(selection[0])
            file_path = item['values'][0]

            # Открываем файл в редакторе
            if hasattr(self.parent, 'open_file'):
                full_path = Path(self.selected_project['path']) / file_path
                self.parent.open_file(str(full_path))

    def show_project_context_menu(self, event):
        """Контекстное меню проектов"""
        item = self.projects_tree.identify_row(event.y)
        if item:
            self.projects_tree.selection_set(item)

            context_menu = tk.Menu(self.window, tearoff=0)
            context_menu.add_command(label="Открыть", command=self.open_project)
            context_menu.add_command(label="Удалить", command=self.delete_project)
            context_menu.add_separator()
            context_menu.add_command(label="Экспорт", command=self.export_project)

            context_menu.post(event.x_root, event.y_root)

    def show_file_context_menu(self, event):
        """Контекстное меню файлов"""
        item = self.files_tree.identify_row(event.y)
        if item:
            self.files_tree.selection_set(item)

            context_menu = tk.Menu(self.window, tearoff=0)
            context_menu.add_command(label="Удалить из отслеживания", command=self.remove_file)
            context_menu.add_separator()
            context_menu.add_command(label="Открыть файл", command=self.on_file_double_click)

            context_menu.post(event.x_root, event.y_root)

    def save_settings(self):
        """Сохранение настроек"""
        # Здесь можно сохранить настройки в файл или базу данных
        messagebox.showinfo("Настройки", "Настройки сохранены")

    def on_close(self):
        """Закрытие окна"""
        self.window.destroy()


class ProjectDialog:
    """Диалог создания/редактирования проекта"""

    def __init__(self, parent, title="Создание проекта"):
        self.result = None

        # Создаем диалог
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Переменные
        self.name_var = tk.StringVar()
        self.path_var = tk.StringVar()
        self.description_var = tk.StringVar()

        # Создаем интерфейс
        self.setup_ui()

        # Центрируем диалог
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")

        # Ждем закрытия
        self.dialog.wait_window()

    def setup_ui(self):
        """Создание интерфейса"""
        # Поля ввода
        fields = [
            ("Имя проекта:", self.name_var),
            ("Путь к проекту:", self.path_var),
            ("Описание:", self.description_var)
        ]

        for i, (label, var) in enumerate(fields):
            ttk.Label(self.dialog, text=label).grid(row=i, column=0, sticky=tk.W, padx=10, pady=5)

            if label == "Путь к проекту:":
                # С кнопкой обзора
                path_frame = ttk.Frame(self.dialog)
                path_frame.grid(row=i, column=1, sticky=tk.EW, padx=10, pady=5)

                entry = ttk.Entry(path_frame, textvariable=var)
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

                ttk.Button(path_frame, text="📁", command=self.browse_path).pack(side=tk.RIGHT, padx=2)

                self.dialog.columnconfigure(1, weight=1)
            else:
                entry = ttk.Entry(self.dialog, textvariable=var)
                entry.grid(row=i, column=1, sticky=tk.EW, padx=10, pady=5)

                self.dialog.columnconfigure(1, weight=1)

        # Технологический стек
        ttk.Label(self.dialog, text="Технологический стек:").grid(row=3, column=0, sticky=tk.W, padx=10, pady=5)

        tech_frame = ttk.Frame(self.dialog)
        tech_frame.grid(row=3, column=1, sticky=tk.EW, padx=10, pady=5)

        self.tech_entry = ttk.Entry(tech_frame)
        self.tech_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(tech_frame, text="(через запятую)").pack(side=tk.RIGHT, padx=5)

        # Кнопки
        button_frame = ttk.Frame(self.dialog)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)

        ttk.Button(button_frame, text="OK", command=self.ok_clicked).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Отмена", command=self.cancel_clicked).pack(side=tk.LEFT, padx=5)

    def browse_path(self):
        """Обзор пути"""
        path = filedialog.askdirectory(title="Выберите папку проекта")
        if path:
            self.path_var.set(path)

            # Автоматически заполняем имя проекта
            if not self.name_var.get():
                project_name = Path(path).name
                self.name_var.set(project_name)

    def ok_clicked(self):
        """Нажатие OK"""
        name = self.name_var.get().strip()
        path = self.path_var.get().strip()

        if not name:
            messagebox.showerror("Ошибка", "Имя проекта не может быть пустым")
            return

        if not path:
            messagebox.showerror("Ошибка", "Путь к проекту не может быть пустым")
            return

        if not Path(path).exists():
            messagebox.showerror("Ошибка", "Указанный путь не существует")
            return

        # Собираем результат
        tech_stack = [tech.strip() for tech in self.tech_entry.get().split(',') if tech.strip()]

        self.result = {
            'name': name,
            'path': path,
            'description': self.description_var.get().strip(),
            'tech_stack': tech_stack
        }

        self.dialog.destroy()

    def cancel_clicked(self):
        """Нажатие Отмена"""
        self.dialog.destroy()
