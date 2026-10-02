"""User-editable application settings and their modal interface."""

from .dependencies import (
    colorchooser,
    filedialog,
    messagebox,
    tk,
)
from . import config
from .config import (
    BG,
    BORDER,
    CARD,
    CARD_2,
    MUTED,
    TEXT,
)


class SettingsMixin:

    def show_settings(self):

        dialog = tk.Toplevel(self)
        dialog.title("AIVORA STUDIO • PARAMÈTRES")
        dialog.geometry("760x740")
        dialog.minsize(600, 600)
        dialog.configure(bg=BG)
        dialog.transient(self)
        dialog.grab_set()

        header = tk.Frame(dialog, bg=BG)
        header.pack(fill="x", padx=24, pady=(20, 14))

        tk.Label(
            header,
            text="Paramètres",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 19, "bold"),
        ).pack(anchor="w")

        tk.Label(
            header,
            text=(
                "Personnalise l'interface et choisis les fonctionnalités "
                "à activer."
            ),
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(4, 0))

        body = tk.Frame(dialog, bg=BG)
        body.pack(fill="both", expand=True, padx=24)

        scrollbar = tk.Scrollbar(
            body,
            orient="vertical",
            troughcolor=BG,
            bg=CARD_2,
            activebackground=config.ACCENT,
        )
        scrollbar.pack(side="right", fill="y", padx=(10, 0))

        canvas = tk.Canvas(
            body,
            bg=BG,
            highlightthickness=0,
            yscrollcommand=scrollbar.set,
        )
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=canvas.yview)

        content = tk.Frame(canvas, bg=BG)
        content_window = canvas.create_window(
            (0, 0),
            window=content,
            anchor="nw",
        )
        content.bind(
            "<Configure>",
            lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.bind(
            "<Configure>",
            lambda event: canvas.itemconfigure(
                content_window,
                width=event.width,
            ),
        )

        current = config.get_settings()
        color_entries = {}
        color_swatches = {}

        color_card = self.create_settings_section(content, "COULEURS DE L'INTERFACE")
        colors_grid = tk.Frame(color_card, bg=CARD)
        colors_grid.pack(fill="x", padx=14, pady=(0, 14))
        colors_grid.columnconfigure(1, weight=1)
        colors_grid.columnconfigure(4, weight=1)

        color_labels = {
            "BG": "Arrière-plan",
            "CARD": "Panneaux",
            "CARD_2": "Panneaux secondaires",
            "TEXT": "Texte principal",
            "MUTED": "Texte secondaire",
            "ACCENT": "Couleur d'accent",
            "ACCENT_HOVER": "Accent au survol",
            "DANGER": "Alerte",
            "DANGER_HOVER": "Alerte au survol",
            "BORDER": "Contours",
            "SUCCESS": "Succès",
            "WARNING": "Avertissement",
        }

        color_names = config.COLOR_SETTING_NAMES
        rows_per_column = (len(color_names) + 1) // 2
        for index, name in enumerate(color_names):
            column_group = index // rows_per_column
            row = index % rows_per_column
            column = column_group * 3

            tk.Label(
                colors_grid,
                text=color_labels[name],
                bg=CARD,
                fg=MUTED,
                font=("Segoe UI", 8),
                anchor="w",
            ).grid(row=row, column=column, sticky="w", padx=(0, 8), pady=5)

            entry = tk.Entry(
                colors_grid,
                bg=CARD_2,
                fg=TEXT,
                insertbackground=TEXT,
                relief="flat",
                highlightthickness=1,
                highlightbackground=BORDER,
                font=("Consolas", 9),
                width=10,
            )
            entry.insert(0, current[name])
            entry.grid(row=row, column=column + 1, sticky="ew", pady=5)
            color_entries[name] = entry

            swatch = tk.Button(
                colors_grid,
                text="",
                bg=current[name],
                activebackground=current[name],
                relief="flat",
                borderwidth=0,
                width=3,
                cursor="hand2",
                command=lambda key=name: self.choose_setting_color(
                    key,
                    color_entries,
                    color_swatches,
                ),
            )
            swatch.grid(row=row, column=column + 2, padx=(5, 12), pady=5)
            color_swatches[name] = swatch

        folder_card = self.create_settings_section(content, "DOSSIERS AUDIO")
        folder_rows = tk.Frame(folder_card, bg=CARD)
        folder_rows.pack(fill="x", padx=14, pady=(0, 14))

        monitored_entry = self.create_folder_setting(
            folder_rows,
            "Dossier surveillé",
            current["MONITORED_FOLDER"],
            0,
        )
        excluded_entry = self.create_folder_setting(
            folder_rows,
            "Dossier exclu",
            current["EXCLUDED_FOLDER"],
            1,
        )

        interval_card = self.create_settings_section(content, "SURVEILLANCE")
        interval_row = tk.Frame(interval_card, bg=CARD)
        interval_row.pack(fill="x", padx=14, pady=(0, 12))

        tk.Label(
            interval_row,
            text="Intervalle de vérification",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(side="left")

        interval_entry = tk.Entry(
            interval_row,
            bg=CARD_2,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            font=("Segoe UI", 9),
            width=9,
        )
        interval_entry.insert(0, str(current["MONITOR_INTERVAL_MS"] // 1000))
        interval_entry.pack(side="right")

        tk.Label(
            interval_row,
            text="secondes",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 8),
        ).pack(side="right", padx=(0, 8))

        feature_card = self.create_settings_section(content, "FONCTIONNALITÉS")
        feature_rows = tk.Frame(feature_card, bg=CARD)
        feature_rows.pack(fill="x", padx=14, pady=(0, 12))
        feature_vars = {}
        feature_labels = (
            ("ENABLE_QUICK_SELECTION", "Rail de sélection rapide"),
            ("ENABLE_COVER_EDITOR", "Gestion des pochettes"),
            ("ENABLE_AUDIO_ANALYSIS", "Forme d'onde et calcul du BPM"),
            ("ENABLE_FOLDER_MONITORING", "Surveillance automatique du dossier"),
            ("ENABLE_AUDIO_CONVERSION", "Conversion des fichiers en MP3"),
            ("ENABLE_AUDIO_REPAIR", "Réparation automatique des fichiers audio invalides"),
            ("ENABLE_FILE_RENAMING", "Renommage des fichiers à l'enregistrement"),
            ("ENABLE_ARTIST_FOLDER_CHECK", "Alerte si le dossier ne correspond pas au premier artiste"),
            ("ENABLE_TRACK_TYPE", "Type du son et suffixe de titre"),
            ("ENABLE_AUTO_UPPERCASE", "Mise en majuscules automatique"),
        )
        for row, (name, label) in enumerate(feature_labels):
            variable = tk.BooleanVar(master=dialog, value=current[name])
            feature_vars[name] = variable
            tk.Checkbutton(
                feature_rows,
                text=label,
                variable=variable,
                onvalue=True,
                offvalue=False,
                anchor="w",
                bg=CARD,
                fg=TEXT,
                activebackground=CARD,
                activeforeground=TEXT,
                selectcolor=CARD_2,
                font=("Segoe UI", 9),
                cursor="hand2",
            ).grid(row=row, column=0, sticky="ew", pady=3)
        feature_rows.columnconfigure(0, weight=1)

        footer = tk.Frame(dialog, bg=BG)
        footer.pack(fill="x", padx=24, pady=18)

        tk.Button(
            footer,
            text="Réinitialiser",
            command=lambda: self.reset_settings_form(
                color_entries,
                color_swatches,
                monitored_entry,
                excluded_entry,
                interval_entry,
                feature_vars,
            ),
            bg=CARD_2,
            fg=TEXT,
            activebackground=BORDER,
            activeforeground=TEXT,
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
            padx=14,
            pady=9,
        ).pack(side="left")

        tk.Button(
            footer,
            text="Annuler",
            command=dialog.destroy,
            bg=CARD_2,
            fg=TEXT,
            activebackground=BORDER,
            activeforeground=TEXT,
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
            padx=14,
            pady=9,
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            footer,
            text="Enregistrer",
            command=lambda: self.save_settings_form(
                dialog,
                color_entries,
                monitored_entry,
                excluded_entry,
                interval_entry,
                feature_vars,
            ),
            bg=config.ACCENT,
            fg="white",
            activebackground=config.ACCENT_HOVER,
            activeforeground="white",
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
            padx=16,
            pady=9,
        ).pack(side="right")
        self.polish_widget_tree(dialog)

    def create_settings_section(self, parent, title):

        card = tk.Frame(
            parent,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        card.pack(fill="x", pady=(0, 12))

        tk.Label(
            card,
            text=title,
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w", padx=14, pady=(12, 8))

        return card

    def create_folder_setting(self, parent, label, value, row):

        tk.Label(
            parent,
            text=label,
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 8),
        ).grid(row=row * 2, column=0, sticky="w", pady=(6, 3))

        field_row = tk.Frame(parent, bg=CARD)
        field_row.grid(row=row * 2 + 1, column=0, sticky="ew", pady=(0, 8))
        parent.columnconfigure(0, weight=1)

        entry = tk.Entry(
            field_row,
            bg=CARD_2,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            font=("Segoe UI", 8),
        )
        entry.insert(0, value)
        entry.pack(side="left", fill="x", expand=True)

        tk.Button(
            field_row,
            text="Parcourir",
            command=lambda: self.browse_setting_folder(entry),
            bg=CARD_2,
            fg=TEXT,
            activebackground=BORDER,
            activeforeground=TEXT,
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 8, "bold"),
            padx=10,
            pady=6,
        ).pack(side="left", padx=(8, 0))

        return entry

    def browse_setting_folder(self, entry):

        selected = filedialog.askdirectory(
            title="CHOISIR UN DOSSIER",
            initialdir=entry.get() or None,
            parent=entry.winfo_toplevel(),
        )
        if selected:
            entry.delete(0, tk.END)
            entry.insert(0, selected)

    def choose_setting_color(self, name, entries, swatches):

        selected = colorchooser.askcolor(
            color=entries[name].get(),
            title="CHOISIR UNE COULEUR",
            parent=entries[name].winfo_toplevel(),
        )[1]
        if selected:
            entries[name].delete(0, tk.END)
            entries[name].insert(0, selected.upper())
            swatches[name].config(
                bg=selected,
                activebackground=selected,
            )

    def reset_settings_form(
        self,
        color_entries,
        color_swatches,
        monitored_entry,
        excluded_entry,
        interval_entry,
        feature_vars,
    ):

        defaults = config.DEFAULT_SETTINGS
        for name, entry in color_entries.items():
            entry.delete(0, tk.END)
            entry.insert(0, defaults[name])
            color_swatches[name].config(
                bg=defaults[name],
                activebackground=defaults[name],
            )

        monitored_entry.delete(0, tk.END)
        monitored_entry.insert(0, defaults["MONITORED_FOLDER"])
        excluded_entry.delete(0, tk.END)
        excluded_entry.insert(0, defaults["EXCLUDED_FOLDER"])
        interval_entry.delete(0, tk.END)
        interval_entry.insert(0, str(defaults["MONITOR_INTERVAL_MS"] // 1000))
        for name, variable in feature_vars.items():
            variable.set(defaults[name])

    def save_settings_form(
        self,
        dialog,
        color_entries,
        monitored_entry,
        excluded_entry,
        interval_entry,
        feature_vars,
    ):

        values = {
            name: entry.get().strip()
            for name, entry in color_entries.items()
        }
        values.update(
            {
                "MONITORED_FOLDER": monitored_entry.get().strip(),
                "EXCLUDED_FOLDER": excluded_entry.get().strip(),
                **{
                    name: variable.get()
                    for name, variable in feature_vars.items()
                },
            }
        )

        try:
            interval_seconds = int(interval_entry.get().strip())
            if not 1 <= interval_seconds <= 3600:
                raise ValueError(
                    "L'INTERVALLE DOIT ÊTRE ENTRE 1 ET 3600 SECONDES."
                )
            values["MONITOR_INTERVAL_MS"] = interval_seconds * 1000
            config.save_settings(values)
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "PARAMÈTRES INVALIDES",
                str(error),
                parent=dialog,
            )
            return

        self.apply_settings()
        dialog.destroy()
        messagebox.showinfo(
            "PARAMÈTRES ENREGISTRÉS",
            "TES PRÉFÉRENCES ONT ÉTÉ ENREGISTRÉES ET APPLIQUÉES.",
            parent=self,
        )

    def apply_settings(self):

        previous = self._active_palette
        current = {
            name: getattr(config, name)
            for name in config.COLOR_SETTING_NAMES
        }
        color_map = {
            old_color.upper(): current[name]
            for name, old_color in previous.items()
        }
        color_options = (
            "bg",
            "fg",
            "activebackground",
            "activeforeground",
            "disabledforeground",
            "highlightbackground",
            "highlightcolor",
            "insertbackground",
            "selectbackground",
            "selectforeground",
            "troughcolor",
        )

        widgets = [self]
        while widgets:
            widget = widgets.pop()
            widgets.extend(widget.winfo_children())

            options = {}
            for option in color_options:
                try:
                    if option in widget.keys():
                        value = str(widget.cget(option)).upper()
                        if value in color_map:
                            options[option] = color_map[value]
                except tk.TclError:
                    continue

            if options:
                try:
                    widget.configure(**options)
                    if isinstance(widget, tk.Button) and "bg" in options:
                        widget._aivora_base_bg = options["bg"]
                except tk.TclError:
                    pass

        self._active_palette = current
        self.apply_feature_settings()

        if (
            hasattr(self, "_monitor_rescan_after_id")
            and self._monitor_rescan_after_id
        ):
            self.after_cancel(self._monitor_rescan_after_id)
            self._monitor_rescan_after_id = None

        if config.ENABLE_FOLDER_MONITORING and not self.monitor_running:
            self.run_folder_scan()

    def apply_feature_settings(self):

        uppercase_label = getattr(self, "uppercase_help_label", None)
        if uppercase_label:
            if config.ENABLE_AUTO_UPPERCASE:
                uppercase_label.config(
                    text="Toutes les informations seront automatiquement enregistrées en MAJUSCULES."
                )
            else:
                uppercase_label.config(
                    text="La casse saisie sera conservée lors de l'enregistrement."
                )

        quick_panel = getattr(self, "quick_selection_panel", None)
        if quick_panel:
            if config.ENABLE_QUICK_SELECTION:
                quick_panel.pack(
                    fill="x",
                    padx=30,
                    pady=(0, 12),
                    before=self.choose_file_button,
                )
                self.refresh_quick_selection()
            else:
                quick_panel.pack_forget()

        analysis_panel = getattr(self, "audio_analysis_panel", None)
        if analysis_panel:
            if config.ENABLE_AUDIO_ANALYSIS:
                analysis_panel.pack(
                    fill="x",
                    padx=20,
                    pady=(14, 4),
                    before=self.artist_title_header,
                )
                self.waveform_canvas.configure(bg=config.CARD_2)
                self.draw_waveform()
                if self.current_file:
                    self.load_waveform()
            else:
                analysis_panel.pack_forget()

        cover_panel = getattr(self, "cover_panel", None)
        if cover_panel:
            if config.ENABLE_COVER_EDITOR:
                cover_panel.pack(side="right", fill="y", padx=(10, 0))
                if self.current_file:
                    self.load_cover()
            else:
                cover_panel.pack_forget()

        type_menu = getattr(self, "type_menu", None)
        if type_menu:
            type_menu.configure(
                state="normal" if config.ENABLE_TRACK_TYPE else "disabled"
            )

        conversion_button = getattr(self, "folder_conversion_button", None)
        if conversion_button:
            enabled = (
                config.ENABLE_AUDIO_CONVERSION
                or config.ENABLE_AUDIO_REPAIR
            )
            conversion_button.configure(
                state="normal" if enabled else "disabled"
            )

        monitor_label = getattr(self, "monitor_label", None)
        if monitor_label:
            if config.ENABLE_FOLDER_MONITORING:
                monitor_label.config(
                    text="Surveillance · En attente",
                    fg=config.MUTED,
                    cursor="",
                )
            else:
                monitor_label.config(
                    text="Surveillance · Désactivée",
                    fg=config.MUTED,
                    cursor="",
                )

        if not config.ENABLE_FOLDER_MONITORING:
            after_id = getattr(self, "_monitor_rescan_after_id", None)
            if after_id:
                self.after_cancel(after_id)
                self._monitor_rescan_after_id = None
