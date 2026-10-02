"""Interface behaviors for Aivora Studio."""

from datetime import datetime, timedelta

from .dependencies import (
    tk,
    tkfont,
)
from . import config
from .config import (
    ACCENT,
    ACCENT_HOVER,
    APP_NAME,
    BG,
    BORDER,
    CARD,
    CARD_2,
    DANGER,
    DANGER_HOVER,
    MUTED,
    TEXT,
    TRACK_TYPES,
    VERSION,
)
from .helpers import (
    uppercase_text,
)


class InterfaceMixin:

    FIRST_UPDATE_AT = datetime(2026, 10, 9)
    UPDATE_INTERVAL = timedelta(days=7)
    FRENCH_MONTHS = (
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    )

    def setup_styles(self):

        try:
            families = set(tkfont.families(self))
        except tk.TclError:
            families = set()

        if "Segoe UI Variable Text" in families:
            self.interface_font_family = "Segoe UI Variable Text"
        elif "Segoe UI Variable" in families:
            self.interface_font_family = "Segoe UI Variable"
        elif "Segoe UI" in families:
            self.interface_font_family = "Segoe UI"
        else:
            self.interface_font_family = tkfont.nametofont(
                "TkDefaultFont",
                root=self,
            ).actual("family")

    def polish_widget_tree(self, parent):

        for widget in parent.winfo_children():
            try:
                if "font" in widget.keys():
                    font_value = widget.cget("font")
                    if font_value:
                        font = tkfont.Font(root=self, font=font_value)
                        actual = font.actual()
                        if actual["family"] in ("Segoe UI", "TkDefaultFont"):
                            widget.configure(
                                font=(
                                    self.interface_font_family,
                                    actual["size"],
                                    actual["weight"],
                                    actual["slant"],
                                )
                            )

                if isinstance(widget, tk.Button):
                    self.polish_button(widget)
            except tk.TclError:
                pass

            self.polish_widget_tree(widget)

    def polish_button(self, button):

        button._aivora_base_bg = button.cget("bg")
        button.bind("<Enter>", self.handle_button_hover, add="+")
        button.bind("<Leave>", self.handle_button_leave, add="+")
        button.bind("<FocusIn>", self.handle_button_focus, add="+")
        button.bind("<FocusOut>", self.handle_button_blur, add="+")

    def handle_button_hover(self, event):

        button = event.widget
        if button.cget("state") == tk.DISABLED:
            return

        hover_color = button.cget("activebackground")
        if hover_color:
            button.configure(bg=hover_color)

    def handle_button_leave(self, event):

        button = event.widget
        button.configure(bg=getattr(button, "_aivora_base_bg", button.cget("bg")))

    def handle_button_focus(self, event):

        event.widget.configure(
            highlightthickness=2,
            highlightbackground=ACCENT,
            highlightcolor=ACCENT,
        )

    def handle_button_blur(self, event):

        event.widget.configure(highlightthickness=0)

    def build_interface(self):

        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=30, pady=(25, 15))

        title_frame = tk.Frame(header, bg=BG)
        title_frame.pack(side="left")

        brand_mark = tk.Label(
            title_frame,
            text="A",
            bg=ACCENT,
            fg="white",
            font=("Segoe UI", 19, "bold"),
            width=2,
            height=1,
        )
        brand_mark.pack(side="left", padx=(0, 12), pady=(2, 0))

        brand_text = tk.Frame(title_frame, bg=BG)
        brand_text.pack(side="left")

        tk.Label(
            brand_text,
            text=APP_NAME,
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 24, "bold"),
        ).pack(anchor="w")

        tk.Label(
            brand_text,
            text="Audio, métadonnées et pochettes",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", pady=(2, 0))

        self.update_countdown_label = tk.Label(
            brand_text,
            text="Prochaine mise à jour · calcul…",
            bg=BG,
            fg=ACCENT_HOVER,
            font=("Segoe UI", 8, "bold"),
        )
        self.update_countdown_label.pack(anchor="w", pady=(5, 0))

        header_actions = tk.Frame(header, bg=BG)
        header_actions.pack(side="right")

        tk.Button(
            header_actions,
            text="⚙  Paramètres",
            command=self.show_settings,
            bg=CARD_2,
            fg=TEXT,
            activebackground=BORDER,
            activeforeground=TEXT,
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=8,
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            header_actions,
            text=f"V{VERSION}  •  Versions",
            command=self.show_changelog,
            bg=ACCENT,
            fg="white",
            activebackground=ACCENT_HOVER,
            activeforeground="white",
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
            padx=14,
            pady=8,
        ).pack(side="right")

        # Zone de dépôt
        self.drop_zone = tk.Frame(
            self,
            bg=CARD,
            height=105,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        self.drop_zone.pack(fill="x", padx=30, pady=(0, 15))
        self.drop_zone.pack_propagate(False)

        self.drop_title = tk.Label(
            self.drop_zone,
            text="♪  Dépose ton fichier audio ici",
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 13, "bold"),
            wraplength=900,
        )
        self.drop_title.pack(pady=(22, 3))

        tk.Label(
            self.drop_zone,
            text="MP3 • WAV • FLAC • M4A • MP4 • OGG • OPUS",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack()

        self.create_quick_selection_panel(self)

        self.choose_file_button = tk.Button(
            self,
            text="Choisir un fichier",
            command=self.choose_file,
            bg=ACCENT,
            fg="white",
            activebackground=ACCENT_HOVER,
            activeforeground="white",
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=18,
            pady=9,
        )
        self.choose_file_button.pack(anchor="w", padx=30, pady=(0, 15))

        footer = tk.Frame(self, bg=BG)
        footer.pack(side="bottom", fill="x", padx=30, pady=(12, 20))

        self.status_label = tk.Label(
            footer,
            text="Aucun fichier chargé",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9, "bold"),
        )
        self.status_label.pack(side="left")

        self.monitor_label = tk.Label(
            footer,
            text="Surveillance · En attente",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 8),
        )
        self.monitor_label.pack(side="left", padx=(14, 0))
        self.monitor_label.bind("<Button-1>", self.show_monitor_issues)

        self.save_button = tk.Button(
            footer,
            text="Enregistrer les modifications",
            command=self.save_all,
            bg=ACCENT,
            fg="white",
            activebackground=ACCENT_HOVER,
            activeforeground="white",
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=20,
            pady=10,
            state="disabled",
            disabledforeground=MUTED,
        )
        self.save_button.pack(side="right")

        self.folder_conversion_button = tk.Button(
            footer,
            text="Convertir / réparer",
            command=self.force_folder_conversion,
            bg=CARD_2,
            fg=TEXT,
            activebackground=BORDER,
            activeforeground="white",
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
            padx=16,
            pady=10,
        )
        self.folder_conversion_button.pack(side="right", padx=(0, 8))

        content_container = tk.Frame(self, bg=BG)
        content_container.pack(fill="both", expand=True, padx=30)

        scrollbar = tk.Scrollbar(
            content_container,
            orient="vertical",
            troughcolor=BG,
            bg=CARD_2,
            activebackground=ACCENT,
        )
        scrollbar.pack(side="right", fill="y", padx=(10, 0))

        self.content_canvas = tk.Canvas(
            content_container,
            bg=BG,
            highlightthickness=0,
            yscrollcommand=scrollbar.set,
        )
        self.content_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.content_canvas.yview)

        content = tk.Frame(self.content_canvas, bg=BG)
        self.content_window = self.content_canvas.create_window(
            (0, 0),
            window=content,
            anchor="nw",
        )
        content.bind("<Configure>", self.update_content_scroll_region)
        self.content_canvas.bind("<Configure>", self.resize_content_width)
        self.content_canvas.bind_all("<MouseWheel>", self.scroll_content)

        self.create_metadata_panel(content)
        self.create_cover_panel(content)
        self.polish_widget_tree(self)
        self.update_release_countdown()

    @staticmethod
    def format_update_countdown(now, target):

        remaining_seconds = max(0, int((target - now).total_seconds()))
        days, remaining_seconds = divmod(remaining_seconds, 24 * 60 * 60)
        hours, remaining_seconds = divmod(remaining_seconds, 60 * 60)
        minutes, seconds = divmod(remaining_seconds, 60)

        if days:
            remaining = f"{days} j {hours:02} h {minutes:02} min {seconds:02} s"
        else:
            remaining = f"{hours:02} h {minutes:02} min {seconds:02} s"

        return remaining

    @classmethod
    def get_next_update_at(cls, now):

        if now < cls.FIRST_UPDATE_AT:
            return cls.FIRST_UPDATE_AT

        elapsed = now - cls.FIRST_UPDATE_AT
        elapsed_weeks = elapsed // cls.UPDATE_INTERVAL
        return cls.FIRST_UPDATE_AT + cls.UPDATE_INTERVAL * (elapsed_weeks + 1)

    def update_release_countdown(self):

        now = datetime.now()
        target = self.get_next_update_at(now)
        remaining = self.format_update_countdown(now, target)
        month = self.FRENCH_MONTHS[target.month - 1]
        text = (
            f"Prochaine mise à jour · dans {remaining} "
            f"({target.day} {month} {target.year})"
        )

        self.update_countdown_label.config(text=text)
        self.after(1000, self.update_release_countdown)

    def update_content_scroll_region(self, event=None):

        self.content_canvas.configure(
            scrollregion=self.content_canvas.bbox("all"),
        )

    def resize_content_width(self, event):

        self.content_canvas.itemconfigure(
            self.content_window,
            width=event.width,
        )

    def scroll_content(self, event):

        if self.content_canvas.winfo_ismapped():
            self.content_canvas.yview_scroll(-int(event.delta / 120), "units")

    def update_type_help(self, *args):

        if not hasattr(self, "type_help_label"):
            return

        track_types = self.get_selected_track_types()
        if track_types == ("STUDIO",):
            hint = "STUDIO : titre et nom de fichier sans suffixe."
        elif track_types:
            hint = "Types ajoutés au titre et au nom du fichier avec « + »."
        else:
            hint = "Choisis un ou plusieurs types."

        self.type_help_label.config(text=hint)

    def show_changelog(self):

        dialog = tk.Toplevel(self)
        dialog.title(f"{APP_NAME} • VERSIONS")
        dialog.geometry("620x560")
        dialog.minsize(500, 420)
        dialog.configure(bg=BG)
        dialog.transient(self)
        dialog.grab_set()

        header = tk.Frame(dialog, bg=BG)
        header.pack(fill="x", padx=24, pady=(22, 16))

        tk.Label(
            header,
            text="Guide des versions",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 19, "bold"),
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Aivora Studio repart sur une nouvelle base : la version 1.0.",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(4, 0))

        content = tk.Frame(dialog, bg=BG)
        content.pack(fill="both", expand=True, padx=24)

        scrollbar = tk.Scrollbar(
            content,
            orient="vertical",
            troughcolor=BG,
            bg=CARD_2,
            activebackground=ACCENT,
        )
        scrollbar.pack(side="right", fill="y", padx=(10, 0))

        canvas = tk.Canvas(
            content,
            bg=BG,
            highlightthickness=0,
            yscrollcommand=scrollbar.set,
        )
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=canvas.yview)

        history = tk.Frame(canvas, bg=BG)
        history_window = canvas.create_window(
            (0, 0),
            window=history,
            anchor="nw",
        )
        history.bind(
            "<Configure>",
            lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(
                history_window,
                width=event.width,
            ),
        )

        guide = tk.Frame(
            history,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        guide.pack(fill="x", pady=(0, 12))
        tk.Label(
            guide,
            text="Grandes mises à jour · environ chaque semaine",
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=16, pady=(14, 4))
        tk.Label(
            guide,
            text="Elles font évoluer le deuxième chiffre : 1.0 → 1.1 → 1.2.",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 9),
            justify="left",
            anchor="w",
            wraplength=490,
        ).pack(anchor="w", padx=16, pady=(0, 10))
        tk.Label(
            guide,
            text="Petits correctifs · environ chaque jour",
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", padx=16, pady=(0, 4))
        tk.Label(
            guide,
            text=(
                "Chaque correctif est un commit isolé et augmente le numéro "
                "sur trois chiffres : 1.0.001 → 1.0.002. Les nouvelles "
                "fonctionnalités sont regroupées dans une livraison "
                "hebdomadaire, qui augmente le deuxième chiffre : 1.1.000."
            ),
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 9),
            justify="left",
            anchor="w",
            wraplength=490,
        ).pack(anchor="w", padx=16, pady=(0, 14))

        entries = [
            (
                VERSION,
                "Compteur avant la prochaine mise à jour",
                (
                    "Ajout du compte à rebours jusqu’au 9 octobre 2026 et "
                    "démarrage de la numérotation des correctifs en 1.0.001."
                ),
            ),
        ]

        for version, title, *changes in entries:
            card = tk.Frame(
                history,
                bg=CARD,
                highlightbackground=BORDER,
                highlightthickness=1,
            )
            card.pack(fill="x", pady=(0, 12))

            card_header = tk.Frame(card, bg=CARD)
            card_header.pack(fill="x", padx=16, pady=(14, 8))

            tk.Label(
                card_header,
                text=f"V{version}",
                bg=ACCENT,
                fg="white",
                font=("Segoe UI", 8, "bold"),
                padx=9,
                pady=4,
            ).pack(side="left")

            tk.Label(
                card_header,
                text=title,
                bg=CARD,
                fg=TEXT,
                font=("Segoe UI", 11, "bold"),
            ).pack(side="left", padx=(10, 0))

            for change in changes:
                row = tk.Frame(card, bg=CARD)
                row.pack(fill="x", padx=16, pady=(0, 9))

                tk.Label(
                    row,
                    text="•",
                    bg=CARD,
                    fg=ACCENT_HOVER,
                    font=("Segoe UI", 12, "bold"),
                ).pack(side="left", anchor="n", padx=(0, 8))

                tk.Label(
                    row,
                    text=change,
                    bg=CARD,
                    fg=MUTED,
                    font=("Segoe UI", 9),
                    justify="left",
                    anchor="w",
                    wraplength=490,
                ).pack(side="left", fill="x", expand=True)

        tk.Button(
            dialog,
            text="Fermer",
            command=dialog.destroy,
            bg=ACCENT,
            fg="white",
            activebackground=ACCENT_HOVER,
            activeforeground="white",
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
            padx=18,
            pady=8,
        ).pack(anchor="e", padx=24, pady=18)
        self.polish_widget_tree(dialog)

    def create_metadata_panel(self, parent):

        panel = tk.Frame(parent, bg=CARD)
        self.metadata_panel = panel
        panel.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 10),
        )

        tk.Label(
            panel,
            text="Métadonnées",
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", padx=20, pady=(18, 3))

        self.uppercase_help_label = tk.Label(
            panel,
            text="Toutes les informations seront automatiquement enregistrées en MAJUSCULES.",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 9),
        )
        self.uppercase_help_label.pack(anchor="w", padx=20)

        self.create_audio_analysis_panel(panel)

        artist_title = tk.Frame(panel, bg=CARD)
        self.artist_title_header = artist_title
        artist_title.pack(fill="x", padx=20, pady=(20, 5))

        tk.Label(
            artist_title,
            text="Artistes",
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")

        tk.Button(
            artist_title,
            text="+ Ajouter un artiste",
            command=self.add_artist_field,
            bg=ACCENT,
            fg="white",
            activebackground=ACCENT_HOVER,
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 8, "bold"),
            padx=9,
            pady=5,
        ).pack(side="right")

        self.artist_container = tk.Frame(panel, bg=CARD_2)
        self.artist_container.pack(
            fill="x",
            padx=20,
            pady=(0, 12),
        )

        form = tk.Frame(panel, bg=CARD)
        form.pack(fill="both", expand=True, padx=20)

        fields = [
            ("NOM DU SON", "title"),
            ("TYPE", "type"),
            ("ALBUM", "album"),
            ("ARTISTE ALBUM", "albumartist"),
            ("ANNÉE", "date"),
            ("GENRE", "genre"),
            ("BPM", "bpm"),
            ("PISTE", "tracknumber"),
            ("COMPOSITEUR", "composer"),
            ("COMMENTAIRE", "comment"),
        ]

        self.entries = {}

        for row, (label, key) in enumerate(fields):

            tk.Label(
                form,
                text=label,
                bg=CARD,
                fg=MUTED,
                font=("Segoe UI", 9),
            ).grid(
                row=row,
                column=0,
                sticky="w",
                pady=5,
                padx=(0, 12),
            )

            if key == "type":
                type_frame = tk.Frame(form, bg=CARD)
                type_menu = tk.OptionMenu(
                    type_frame,
                    self.track_type_var,
                    "STUDIO",
                )
                self.type_menu = type_menu
                menu = type_menu["menu"]
                menu.delete(0, tk.END)
                self.track_type_vars = {
                    track_type: tk.BooleanVar(
                        master=self,
                        value=track_type == "STUDIO",
                    )
                    for track_type in TRACK_TYPES
                }
                for track_type in TRACK_TYPES:
                    menu.add_checkbutton(
                        label=track_type,
                        variable=self.track_type_vars[track_type],
                        command=self.update_track_type_display,
                    )
                self.update_track_type_display()
                type_menu.config(
                    bg=CARD_2,
                    fg=TEXT,
                    activebackground=ACCENT,
                    activeforeground="white",
                    relief="flat",
                    borderwidth=0,
                    highlightthickness=1,
                    highlightbackground=BORDER,
                    highlightcolor=ACCENT,
                    font=("Segoe UI", 10),
                    anchor="w",
                    padx=10,
                    pady=4,
                )
                type_menu["menu"].config(
                    bg=CARD_2,
                    fg=TEXT,
                    activebackground=ACCENT,
                    activeforeground="white",
                    font=("Segoe UI", 10),
                )
                type_menu.pack(fill="x")
                self.type_help_label = tk.Label(
                    type_frame,
                    text="",
                    bg=CARD,
                    fg=MUTED,
                    font=("Segoe UI", 8),
                    anchor="w",
                )
                self.type_help_label.pack(fill="x", pady=(3, 0))
                type_frame.grid(
                    row=row,
                    column=1,
                    sticky="ew",
                    pady=5,
                )
                self.track_type_var.trace_add(
                    "write",
                    self.update_type_help,
                )
                self.update_type_help()
                continue

            entry = tk.Entry(
                form,
                bg=CARD_2,
                fg=TEXT,
                insertbackground=TEXT,
                relief="flat",
                highlightthickness=1,
                highlightbackground=BORDER,
                highlightcolor=ACCENT,
                font=("Segoe UI", 10),
            )

            entry.grid(
                row=row,
                column=1,
                sticky="ew",
                pady=5,
            )

            self.entries[key] = entry

            entry.bind(
                "<KeyRelease>",
                lambda event, e=entry: self.force_uppercase(e),
            )

        form.columnconfigure(1, weight=1)

    def add_artist_field(self):

        index = len(self.artist_entries) + 1

        row = tk.Frame(self.artist_container, bg=CARD_2)
        row.pack(fill="x", padx=10, pady=5)

        label = tk.Label(
            row,
            text=f"ARTISTE {index}",
            bg=CARD_2,
            fg=MUTED,
            width=12,
            anchor="w",
            font=("Segoe UI", 9),
        )
        label.pack(side="left")

        entry = tk.Entry(
            row,
            bg="#282d37",
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            font=("Segoe UI", 10),
        )
        entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=5,
        )

        entry.bind(
            "<KeyRelease>",
            lambda event, e=entry: self.force_uppercase(e),
        )

        self.artist_entries.append(
            {
                "frame": row,
                "entry": entry,
                "label": label,
            }
        )

        tk.Button(
            row,
            text="×",
            command=lambda r=row: self.remove_artist_field(r),
            bg=DANGER,
            fg="white",
            activebackground=DANGER_HOVER,
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            width=3,
        ).pack(side="right")

        self.refresh_artist_labels()
        self.polish_widget_tree(row)

    def remove_artist_field(self, frame):

        if len(self.artist_entries) <= 1:
            return

        for item in self.artist_entries:
            if item["frame"] == frame:
                item["frame"].destroy()
                self.artist_entries.remove(item)
                break

        self.refresh_artist_labels()

    def refresh_artist_labels(self):

        for index, item in enumerate(self.artist_entries, start=1):
            item["label"].config(text=f"ARTISTE {index}")

    def get_artists(self):

        artists = []

        for item in self.artist_entries:
            value = uppercase_text(item["entry"].get())

            if value:
                artists.append(value)

        return artists

    def get_combined_artists(self):
        return " & ".join(self.get_artists())

    def force_uppercase(self, entry):

        current = entry.get()
        upper = current.upper()

        if current != upper:

            cursor = entry.index(tk.INSERT)

            entry.delete(0, tk.END)
            entry.insert(0, upper)

            try:
                entry.icursor(cursor)
            except Exception:
                pass

    def force_all_uppercase(self):

        if not config.ENABLE_AUTO_UPPERCASE:
            return

        for item in self.artist_entries:
            entry = item["entry"]
            if not config.ENABLE_AUTO_UPPERCASE:
                return

            value = entry.get().upper()

            entry.delete(0, tk.END)
            entry.insert(0, value)

        for entry in self.entries.values():
            value = entry.get().upper()

            entry.delete(0, tk.END)
            entry.insert(0, value)
