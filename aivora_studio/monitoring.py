"""Monitoring behaviors for Aivora Studio."""

from .dependencies import (
    File,
    ID3,
    ID3NoHeaderError,
    get_ffmpeg_exe,
    os,
    queue,
    shutil,
    subprocess,
    tempfile,
    threading,
    tk,
)
from . import config
from .config import (
    ACCENT,
    ACCENT_HOVER,
    AUDIO_EXTENSIONS,
    BG,
    CARD_2,
    DANGER,
    EXCLUDED_FOLDER,
    MONITORED_FOLDER,
    MONITOR_INTERVAL_MS,
    MUTED,
    SUCCESS,
    TEXT,
    WARNING,
)
from .helpers import (
    get_extension,
)
from .duplicates import (
    delete_review_file,
    duplicate_group_is_current,
    duplicate_group_key,
    find_audio_duplicates,
    format_file_details,
)


class MonitoringMixin:

    def is_excluded_path(self, path):

        try:
            path = os.path.normcase(os.path.abspath(path))
            excluded = os.path.normcase(os.path.abspath(EXCLUDED_FOLDER))
            return os.path.commonpath([path, excluded]) == excluded
        except ValueError:
            return False

    def get_mp3_output_path(self, source_path):

        folder, filename = os.path.split(source_path)
        stem, _ = os.path.splitext(filename)
        return os.path.join(folder, f"{stem}.mp3")

    def convert_to_mp3(self, source_path, output_path):

        if get_ffmpeg_exe is None:
            return "DÉCODEUR AUDIO INDISPONIBLE"

        if os.path.exists(output_path):
            return "UN MP3 AVEC CE NOM EXISTE DÉJÀ"

        command = [
            get_ffmpeg_exe(),
            "-v",
            "error",
            "-i",
            source_path,
            "-map_metadata",
            "0",
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "2",
            "-n",
            output_path,
        ]

        try:
            subprocess.run(
                command,
                capture_output=True,
                check=True,
                timeout=600,
            )
        except (OSError, subprocess.SubprocessError):
            return "CONVERSION MP3 IMPOSSIBLE"

        issue = self.validate_audio_file(output_path)
        if issue:
            return f"MP3 CRÉÉ MAIS INVALIDE : {issue}"

        try:
            os.remove(source_path)
        except OSError:
            return "MP3 CRÉÉ, MAIS ORIGINAL NON SUPPRIMÉ"

        return None

    def validate_audio_file(self, path):

        try:
            audio = File(path, easy=False)

            if audio is None:
                return "FORMAT AUDIO ILLISIBLE"

            duration = getattr(audio.info, "length", 0)
            if duration <= 0:
                return "DURÉE AUDIO INVALIDE"

        except Exception as error:
            return f"FICHIER AUDIO CORROMPU OU INCOMPLET : {error}"

        return None

    def get_embedded_m4a_offset(self, path):

        try:
            with open(path, "rb") as audio_file:
                header = audio_file.read(10)

                if len(header) != 10 or header[:3] != b"ID3":
                    return None

                size_bytes = header[6:10]
                if any(byte & 0x80 for byte in size_bytes):
                    return None

                tag_size = (
                    (size_bytes[0] << 21)
                    | (size_bytes[1] << 14)
                    | (size_bytes[2] << 7)
                    | size_bytes[3]
                )
                offset = 10 + tag_size + (10 if header[5] & 0x10 else 0)

                audio_file.seek(offset)
                container_header = audio_file.read(8)

                if len(container_header) == 8 and container_header[4:8] == b"ftyp":
                    return offset
        except OSError:
            return None

        return None

    def repair_audio_file(self, path):

        if get_ffmpeg_exe is None:
            return "DÉCODEUR AUDIO INDISPONIBLE"

        try:
            ffmpeg_exe = get_ffmpeg_exe()
        except (OSError, RuntimeError) as error:
            return f"DÉCODEUR AUDIO INDISPONIBLE : {error}"

        folder = os.path.dirname(os.path.abspath(path))
        try:
            file_descriptor, repaired_path = tempfile.mkstemp(
                prefix=".repair-",
                suffix=".mp3",
                dir=folder,
            )
        except OSError as error:
            return f"FICHIER TEMPORAIRE IMPOSSIBLE À CRÉER : {error}"

        os.close(file_descriptor)

        input_path = path
        temporary_input_path = None
        embedded_m4a_offset = self.get_embedded_m4a_offset(path)
        source_tags = None

        if embedded_m4a_offset is not None:
            try:
                file_descriptor, temporary_input_path = tempfile.mkstemp(
                    prefix=".repair-input-",
                    suffix=".m4a",
                    dir=folder,
                )
                with os.fdopen(file_descriptor, "wb") as m4a_file:
                    with open(path, "rb") as original_file:
                        original_file.seek(embedded_m4a_offset)
                        shutil.copyfileobj(original_file, m4a_file)

                input_path = temporary_input_path
                source_tags = ID3(path)
            except (OSError, ID3NoHeaderError, ValueError) as error:
                if temporary_input_path and os.path.exists(temporary_input_path):
                    os.remove(temporary_input_path)
                if os.path.exists(repaired_path):
                    os.remove(repaired_path)
                return f"CONTENEUR M4A INTÉGRÉ IMPOSSIBLE À EXTRAIRE : {error}"

        command = [
            ffmpeg_exe,
            "-v",
            "error",
            "-fflags",
            "+discardcorrupt",
            "-err_detect",
            "ignore_err",
            "-i",
            input_path,
            "-map",
            "0:a:0",
            "-map_metadata",
            "0",
            "-vn",
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "2",
            "-y",
            repaired_path,
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=600,
            )
        except (OSError, subprocess.SubprocessError) as error:
            repair_error = f"ÉCHEC DU RÉENCODAGE : {error}"
        else:
            issue = self.validate_audio_file(repaired_path)
            if not issue and source_tags is not None:
                try:
                    output_tags = ID3(repaired_path)
                    output_tags.update(source_tags)
                    output_tags.save(repaired_path)
                except (OSError, ValueError) as error:
                    issue = f"MÉTADONNÉES ID3 IMPOSSIBLES À COPIER : {error}"

            if not issue:
                issue = self.validate_audio_file(repaired_path)

            if issue:
                details = (result.stderr or "").strip()
                if details:
                    repair_error = (
                        f"RÉPARATION IMPOSSIBLE : {issue} ({details[-500:]})"
                    )
                else:
                    repair_error = f"RÉPARATION IMPOSSIBLE : {issue}"
            else:
                try:
                    os.replace(repaired_path, path)
                    repair_error = None
                except OSError as error:
                    repair_error = (
                        f"FICHIER RÉPARÉ MAIS REMPLACEMENT IMPOSSIBLE : {error}"
                    )

        for temporary_path in (repaired_path, temporary_input_path):
            if temporary_path and os.path.exists(temporary_path):
                try:
                    os.remove(temporary_path)
                except OSError as error:
                    cleanup_issue = f"FICHIER TEMPORAIRE NON SUPPRIMÉ : {error}"
                    if repair_error:
                        repair_error += f"\n{cleanup_issue}"
                    else:
                        repair_error = cleanup_issue

        return repair_error

    def scan_monitored_folder(self):

        summary = {
            "checked": 0,
            "converted": 0,
            "repaired": 0,
            "issues": [],
            "duplicate_groups": [],
        }

        try:
            duplicate_groups, duplicate_errors = find_audio_duplicates(
                MONITORED_FOLDER,
                EXCLUDED_FOLDER,
                AUDIO_EXTENSIONS,
                hash_cache=self.duplicate_hash_cache,
                fingerprint_cache=self.duplicate_fingerprint_cache,
            )
            for group in duplicate_groups:
                summary["duplicate_groups"].append(group)
                summary["issues"].append(
                    {
                        "path": "\n".join(
                            info["path"] for info in group["files"]
                        ),
                        "message": (
                            "DOUBLON AUDIO EXACT"
                            if group["kind"] == "exact"
                            else (
                                "DOUBLON AUDIO PROBABLE · "
                                f"similarité sonore {group['similarity']:.1f}%"
                            )
                        ),
                    }
                )
            for path, error in duplicate_errors:
                summary["issues"].append(
                    {
                        "path": path,
                        "message": f"ANALYSE DE DOUBLON IMPOSSIBLE : {error}",
                    }
                )

            for root, folders, files in os.walk(MONITORED_FOLDER):
                folders[:] = [
                    folder
                    for folder in folders
                    if not self.is_excluded_path(os.path.join(root, folder))
                ]

                if self.is_excluded_path(root):
                    continue

                for filename in files:
                    source_path = os.path.join(root, filename)
                    extension = get_extension(source_path)

                    if extension not in AUDIO_EXTENSIONS:
                        continue

                    if os.path.islink(source_path):
                        summary["issues"].append(
                            {
                                "path": source_path,
                                "message": "LIEN SYMBOLIQUE IGNORÉ",
                            }
                        )
                        continue

                    summary["checked"] += 1
                    target_path = source_path

                    if extension != ".mp3" and config.ENABLE_AUDIO_CONVERSION:
                        target_path = self.get_mp3_output_path(source_path)

                        if not os.path.exists(target_path):
                            error = self.convert_to_mp3(source_path, target_path)

                            if error:
                                summary["issues"].append(
                                    {
                                        "path": source_path,
                                        "message": error,
                                    }
                                )
                                continue

                            summary["converted"] += 1

                    issue = self.validate_audio_file(target_path)
                    if issue:
                        if config.ENABLE_AUDIO_REPAIR:
                            repair_error = self.repair_audio_file(target_path)
                        else:
                            repair_error = "RÉPARATION DÉSACTIVÉE DANS LES PARAMÈTRES"
                        if repair_error:
                            summary["issues"].append(
                                {
                                    "path": target_path,
                                    "message": f"{issue}\n{repair_error}",
                                }
                            )
                        else:
                            summary["repaired"] += 1

        except Exception as error:
            summary["issues"].append(
                {
                    "path": MONITORED_FOLDER,
                    "message": f"SCAN INTERROMPU : {error}",
                }
            )

        self.monitor_queue.put(summary)

    def start_folder_monitoring(self):

        if config.ENABLE_FOLDER_MONITORING:
            self.schedule_folder_scan(500)

    def schedule_folder_scan(self, delay):

        self._monitor_rescan_after_id = self.after(
            delay,
            self.run_folder_scan,
        )

    def force_folder_conversion(self):

        if not (
            config.ENABLE_AUDIO_CONVERSION
            or config.ENABLE_AUDIO_REPAIR
        ):
            return

        if self.monitor_running:
            self.monitor_label.config(
                text="Surveillance · Une opération est déjà en cours…",
                fg=ACCENT,
            )
            return

        self.run_folder_scan(automatic=False)

    def run_folder_scan(self, automatic=True):

        self._monitor_rescan_after_id = None

        if not os.path.isdir(MONITORED_FOLDER):
            self.monitor_label.config(
                text="Surveillance · Dossier introuvable",
                fg=DANGER,
            )
            if automatic and config.ENABLE_FOLDER_MONITORING:
                self.schedule_folder_scan(MONITOR_INTERVAL_MS)
            return

        if self.monitor_running:
            if automatic and config.ENABLE_FOLDER_MONITORING:
                self.schedule_folder_scan(MONITOR_INTERVAL_MS)
            return

        self.monitor_running = True
        self.monitor_label.config(
            text="Surveillance · Analyse en cours…",
            fg=ACCENT,
        )

        threading.Thread(
            target=self.scan_monitored_folder,
            daemon=True,
        ).start()
        self.after(250, self.collect_folder_scan)

    def collect_folder_scan(self):

        try:
            summary = self.monitor_queue.get_nowait()
        except queue.Empty:
            self.after(250, self.collect_folder_scan)
            return

        self.monitor_running = False
        self.last_monitor_issues = summary["issues"]
        issue_count = len(summary["issues"])
        text = (
            f"Surveillance · {summary['checked']} fichiers · "
            f"{summary['converted']} convertis · "
            f"{summary['repaired']} réparés · "
            f"{issue_count} anomalies"
        )
        if issue_count:
            text += " · Cliquer pour les détails"

        self.monitor_label.config(
            text=text,
            fg=WARNING if issue_count else SUCCESS,
            cursor="hand2" if issue_count else "",
        )
        if summary["duplicate_groups"]:
            self.after_idle(
                lambda groups=summary["duplicate_groups"]:
                    self.review_duplicate_groups(groups)
            )
        if config.ENABLE_FOLDER_MONITORING:
            self.schedule_folder_scan(MONITOR_INTERVAL_MS)

    def review_duplicate_groups(self, groups):
        for group in groups:
            if not duplicate_group_is_current(group):
                continue
            key = duplicate_group_key(group)
            if key in self.reviewed_duplicate_keys:
                continue
            self.reviewed_duplicate_keys.add(key)
            self.show_duplicate_review(group)

    def show_duplicate_review(self, group):
        dialog = tk.Toplevel(self)
        dialog.title("Doublon audio à vérifier")
        dialog.geometry("760x560")
        dialog.minsize(580, 420)
        dialog.configure(bg=BG)
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(
            dialog,
            text=(
                "Doublon exact"
                if group["kind"] == "exact"
                else "Fichiers audio probablement similaires"
            ),
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 15, "bold"),
        ).pack(anchor="w", padx=20, pady=(18, 4))
        tk.Label(
            dialog,
            text=(
                f"{group['reason']} Similarité sonore : "
                f"{group['similarity']:.1f} %. "
                "Vérifie les informations avant toute suppression."
            ),
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9),
            wraplength=700,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 14))

        content = tk.Frame(dialog, bg=BG)
        content.pack(fill="both", expand=True, padx=20)
        for index, file_info in enumerate(group["files"], start=1):
            card = tk.Frame(
                content,
                bg=CARD,
                highlightbackground=BORDER,
                highlightthickness=1,
            )
            card.pack(fill="x", pady=(0, 10))
            tk.Label(
                card,
                text=f"Fichier {index}",
                bg=CARD,
                fg=TEXT,
                font=("Segoe UI", 10, "bold"),
            ).pack(anchor="w", padx=14, pady=(12, 4))
            tk.Label(
                card,
                text=format_file_details(file_info),
                bg=CARD,
                fg=MUTED,
                font=("Segoe UI", 8),
                justify="left",
                anchor="w",
                wraplength=680,
            ).pack(fill="x", padx=14)

            def delete_candidate(candidate=file_info):
                confirmed = messagebox.askyesno(
                    "Confirmer la suppression",
                    "Supprimer définitivement ce fichier audio ?\n\n"
                    f"{format_file_details(candidate)}",
                    parent=dialog,
                )
                if not confirmed:
                    return
                try:
                    delete_review_file(candidate)
                except OSError as error:
                    messagebox.showerror(
                        "Suppression impossible",
                        str(error),
                        parent=dialog,
                    )
                    return
                self.duplicate_hash_cache.pop(candidate["cache_key"], None)
                self.duplicate_fingerprint_cache.pop(
                    candidate["cache_key"],
                    None,
                )
                dialog.destroy()
                self.run_folder_scan(automatic=False)

            tk.Button(
                card,
                text="Supprimer ce fichier…",
                command=delete_candidate,
                bg=CARD_2,
                fg=TEXT,
                activebackground=DANGER,
                activeforeground="white",
                relief="flat",
                borderwidth=0,
                cursor="hand2",
                font=("Segoe UI", 8, "bold"),
                padx=10,
                pady=6,
            ).pack(anchor="e", padx=14, pady=10)

        tk.Button(
            dialog,
            text="Garder tous les fichiers",
            command=dialog.destroy,
            bg=ACCENT,
            fg="white",
            activebackground=ACCENT_HOVER,
            activeforeground="white",
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
            padx=16,
            pady=8,
        ).pack(anchor="e", padx=20, pady=16)
        self.polish_widget_tree(dialog)
        self.wait_window(dialog)

    def show_monitor_issues(self, event=None):

        if not self.last_monitor_issues:
            return

        dialog = tk.Toplevel(self)
        dialog.title("Anomalies détectées")
        dialog.geometry("760x440")
        dialog.minsize(560, 300)
        dialog.configure(bg=BG)
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(
            dialog,
            text="Anomalies détectées",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", padx=20, pady=(18, 4))

        tk.Label(
            dialog,
            text="Fichier concerné et détail du problème",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=20, pady=(0, 12))

        content = tk.Frame(dialog, bg=BG)
        content.pack(fill="both", expand=True, padx=20)

        scrollbar = tk.Scrollbar(content, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        details = tk.Text(
            content,
            bg=CARD_2,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            borderwidth=0,
            wrap="word",
            font=("Consolas", 10),
            yscrollcommand=scrollbar.set,
            padx=12,
            pady=12,
        )
        details.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=details.yview)

        for index, issue in enumerate(self.last_monitor_issues, start=1):
            details.insert(
                tk.END,
                f"{index}. {issue['message']}\n{issue['path']}\n\n",
            )

        details.config(state="disabled")

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
        ).pack(anchor="e", padx=20, pady=18)
        self.polish_widget_tree(dialog)
