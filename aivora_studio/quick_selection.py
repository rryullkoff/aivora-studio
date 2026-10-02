"""Quick audio-file selection rail backed by the configured excluded folder."""

from . import config
from .dependencies import os, queue, threading, tk


class QuickSelectionMixin:

    QUICK_SELECTION_PAGE_SIZE = 6

    def create_quick_selection_panel(self, parent):

        panel = tk.Frame(parent, bg=config.BG)
        self.quick_selection_panel = panel
        panel.pack(fill="x", padx=30, pady=(0, 12))

        header = tk.Frame(panel, bg=config.BG)
        header.pack(fill="x", pady=(0, 7))

        tk.Label(
            header,
            text="Sélection rapide",
            bg=config.BG,
            fg=config.TEXT,
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left")

        self.quick_selection_info = tk.Label(
            header,
            text="Chargement des fichiers…",
            bg=config.BG,
            fg=config.MUTED,
            font=("Segoe UI", 8),
        )
        self.quick_selection_info.pack(side="left", padx=(10, 0))
        self.quick_selection_info.bind(
            "<Button-1>",
            self.show_quick_selection_errors,
        )

        actions = tk.Frame(header, bg=config.BG)
        actions.pack(side="right")

        self.quick_selection_page_label = tk.Label(
            actions,
            text="",
            bg=config.BG,
            fg=config.MUTED,
            font=("Segoe UI", 8),
        )
        self.quick_selection_page_label.pack(side="left", padx=(0, 8))

        self.quick_selection_previous = tk.Button(
            actions,
            text="‹",
            command=lambda: self.show_quick_selection_page(
                self.quick_selection_page - 1
            ),
            bg=config.CARD_2,
            fg=config.TEXT,
            activebackground=config.BORDER,
            activeforeground=config.TEXT,
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 13),
            width=3,
            state="disabled",
        )
        self.quick_selection_previous.pack(side="left", padx=(0, 5))

        self.quick_selection_next = tk.Button(
            actions,
            text="›",
            command=lambda: self.show_quick_selection_page(
                self.quick_selection_page + 1
            ),
            bg=config.CARD_2,
            fg=config.TEXT,
            activebackground=config.BORDER,
            activeforeground=config.TEXT,
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 13),
            width=3,
            state="disabled",
        )
        self.quick_selection_next.pack(side="left", padx=(0, 7))

        self.quick_selection_refresh_button = tk.Button(
            actions,
            text="Actualiser",
            command=self.refresh_quick_selection,
            bg=config.CARD_2,
            fg=config.TEXT,
            activebackground=config.BORDER,
            activeforeground=config.TEXT,
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 8, "bold"),
            padx=10,
            pady=5,
        )
        self.quick_selection_refresh_button.pack(side="left")

        self.quick_selection_canvas = tk.Canvas(
            panel,
            bg=config.BG,
            height=82,
            highlightthickness=0,
        )
        self.quick_selection_canvas.pack(fill="x")
        self.quick_selection_canvas.bind(
            "<Configure>",
            self.resize_quick_selection_rail,
        )

        self.quick_selection_items = tk.Frame(
            self.quick_selection_canvas,
            bg=config.BG,
        )
        self.quick_selection_window = self.quick_selection_canvas.create_window(
            (0, 0),
            window=self.quick_selection_items,
            anchor="nw",
        )
        self.quick_selection_items.bind(
            "<Configure>",
            self.update_quick_selection_scroll_region,
        )

        self.quick_selection_queue = queue.Queue()
        self.quick_selection_files = []
        self.quick_selection_errors = []
        self.quick_selection_page = 0
        self.quick_selection_scan_running = False
        self.quick_selection_refresh_pending = False
        self.quick_selection_card_buttons = []

        self.polish_widget_tree(panel)

    def refresh_quick_selection(self):

        if not config.ENABLE_QUICK_SELECTION:
            return

        if self.quick_selection_scan_running:
            self.quick_selection_refresh_pending = True
            return

        self.quick_selection_refresh_pending = False
        folder = config.EXCLUDED_FOLDER
        self.quick_selection_scan_running = True
        self.quick_selection_refresh_button.config(
            state="disabled",
            text="Analyse…",
        )
        self.quick_selection_info.config(
            text=f"Analyse de {folder}",
            fg=config.MUTED,
        )
        self.quick_selection_page_label.config(text="")

        threading.Thread(
            target=self.scan_quick_selection_folder,
            args=(folder,),
            daemon=True,
        ).start()
        self.after(100, self.collect_quick_selection_scan)

    def scan_quick_selection_folder(self, folder):

        files = []
        errors = []

        def record_error(error):
            errors.append(str(error))

        try:
            if not os.path.isdir(folder):
                result = {
                    "files": [],
                    "errors": [f"Le dossier n'existe pas : {folder}"],
                    "folder": folder,
                }
            else:
                for root, directories, filenames in os.walk(
                    folder,
                    onerror=record_error,
                ):
                    directories.sort(key=str.casefold)
                    for filename in filenames:
                        path = os.path.join(root, filename)
                        if os.path.splitext(filename)[1].lower() in config.AUDIO_EXTENSIONS:
                            files.append(path)

                result = {
                    "files": sorted(files, key=str.casefold),
                    "errors": errors,
                    "folder": folder,
                }
        except OSError as error:
            result = {
                "files": [],
                "errors": [str(error)],
                "folder": folder,
            }

        self.quick_selection_queue.put(result)

    def collect_quick_selection_scan(self):

        try:
            result = self.quick_selection_queue.get_nowait()
        except queue.Empty:
            self.after(100, self.collect_quick_selection_scan)
            return

        self.quick_selection_scan_running = False
        self.quick_selection_files = result["files"]
        self.quick_selection_errors = result["errors"]
        self.quick_selection_page = 0
        self.quick_selection_refresh_button.config(
            state="normal",
            text="Actualiser",
        )

        file_count = len(self.quick_selection_files)
        folder_name = os.path.basename(os.path.normpath(result["folder"]))
        if file_count:
            info = f"{file_count} fichier{'s' if file_count != 1 else ''} · {folder_name}"
            color = config.MUTED
        else:
            info = f"Aucun fichier audio · {folder_name}"
            color = config.MUTED

        if result["errors"]:
            info += f" · {len(result['errors'])} erreur{'s' if len(result['errors']) != 1 else ''} d'accès"
            color = config.WARNING

        self.quick_selection_info.config(
            text=info,
            fg=color,
            cursor="hand2" if result["errors"] else "",
        )
        self.show_quick_selection_page(0)

        if self.quick_selection_refresh_pending:
            self.after_idle(self.refresh_quick_selection)

    def show_quick_selection_errors(self, event=None):

        if not self.quick_selection_errors:
            return

        dialog = tk.Toplevel(self)
        dialog.title("Sélection rapide · Erreurs d'accès")
        dialog.geometry("700x400")
        dialog.minsize(500, 280)
        dialog.configure(bg=config.BG)
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(
            dialog,
            text="Certains dossiers n'ont pas pu être lus",
            bg=config.BG,
            fg=config.TEXT,
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", padx=20, pady=(18, 6))

        details = tk.Text(
            dialog,
            bg=config.CARD_2,
            fg=config.TEXT,
            relief="flat",
            borderwidth=0,
            wrap="word",
            font=("Segoe UI", 9),
            padx=12,
            pady=12,
        )
        details.pack(fill="both", expand=True, padx=20, pady=(0, 14))
        details.insert(tk.END, "\n".join(self.quick_selection_errors))
        details.config(state="disabled")

        tk.Button(
            dialog,
            text="Fermer",
            command=dialog.destroy,
            bg=config.ACCENT,
            fg="white",
            activebackground=config.ACCENT_HOVER,
            activeforeground="white",
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
            padx=16,
            pady=8,
        ).pack(anchor="e", padx=20, pady=(0, 16))
        self.polish_widget_tree(dialog)

    def show_quick_selection_page(self, page):

        page_count = max(
            1,
            (
                len(self.quick_selection_files)
                + self.QUICK_SELECTION_PAGE_SIZE
                - 1
            ) // self.QUICK_SELECTION_PAGE_SIZE,
        )
        self.quick_selection_page = max(0, min(page, page_count - 1))

        for widget in self.quick_selection_items.winfo_children():
            widget.destroy()

        start = self.quick_selection_page * self.QUICK_SELECTION_PAGE_SIZE
        end = min(
            start + self.QUICK_SELECTION_PAGE_SIZE,
            len(self.quick_selection_files),
        )
        self.quick_selection_card_buttons = []

        for path in self.quick_selection_files[start:end]:
            card = tk.Frame(
                self.quick_selection_items,
                bg=config.CARD,
                highlightbackground=config.BORDER,
                highlightthickness=1,
                width=145,
                height=70,
            )
            card.pack(side="left", fill="y", padx=(0, 8))
            card.pack_propagate(False)

            filename = os.path.basename(path)
            title = filename
            if len(title) > 24:
                stem, extension = os.path.splitext(title)
                title = f"{stem[:19]}…{extension}"

            button = tk.Button(
                card,
                text=title,
                command=lambda selected_path=path: self.load_file(selected_path),
                bg=config.CARD,
                fg=config.TEXT,
                activebackground=config.CARD_2,
                activeforeground=config.TEXT,
                relief="flat",
                borderwidth=0,
                cursor="hand2",
                font=("Segoe UI", 9, "bold"),
                wraplength=125,
                justify="left",
                anchor="w",
            )
            button.pack(fill="both", expand=True, padx=9, pady=7)
            self.quick_selection_card_buttons.append((path, card, button))
            self.polish_button(button)

        if not self.quick_selection_files:
            empty = tk.Label(
                self.quick_selection_items,
                text="Les fichiers audio du dossier exclu apparaîtront ici.",
                bg=config.BG,
                fg=config.MUTED,
                font=("Segoe UI", 9),
                anchor="w",
            )
            empty.pack(fill="x", pady=20)

        if page_count > 1:
            self.quick_selection_page_label.config(
                text=f"{self.quick_selection_page + 1} / {page_count}"
            )
        else:
            self.quick_selection_page_label.config(text="")

        self.quick_selection_previous.config(
            state="normal" if self.quick_selection_page > 0 else "disabled"
        )
        self.quick_selection_next.config(
            state="normal" if self.quick_selection_page < page_count - 1 else "disabled"
        )

        self.quick_selection_items.update_idletasks()
        self.update_quick_selection_scroll_region()
        self.update_quick_selection_highlight()

    def update_quick_selection_scroll_region(self, event=None):

        self.quick_selection_canvas.configure(
            scrollregion=self.quick_selection_canvas.bbox("all"),
        )

    def resize_quick_selection_rail(self, event):

        self.quick_selection_canvas.itemconfigure(
            self.quick_selection_window,
            height=event.height,
        )

    def update_quick_selection_highlight(self):

        current_file = getattr(self, "current_file", None)
        current_path = (
            os.path.normcase(os.path.abspath(current_file))
            if current_file
            else None
        )

        for path, card, button in self.quick_selection_card_buttons:
            is_selected = (
                current_path == os.path.normcase(os.path.abspath(path))
            )
            button.configure(
                bg=config.ACCENT if is_selected else config.CARD,
                activebackground=config.ACCENT_HOVER if is_selected else config.CARD_2,
                fg="white" if is_selected else config.TEXT,
            )
            button._aivora_base_bg = config.ACCENT if is_selected else config.CARD
            card.configure(
                highlightbackground=config.ACCENT if is_selected else config.BORDER
            )
