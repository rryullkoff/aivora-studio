"""Editor behaviors for Aivora Studio."""

from .dependencies import (
    COMM,
    File,
    ID3,
    MP4,
    TALB,
    TBPM,
    TCOM,
    TCON,
    TDRC,
    TIT2,
    TPE1,
    TPE2,
    TRCK,
    WAVE,
    filedialog,
    messagebox,
    os,
    re,
    tk,
)
from . import config
from .config import (
    MUTED,
    SUCCESS,
    TRACK_TYPES,
    WARNING,
)
from .helpers import (
    clean_filename,
    get_extension,
    uppercase_text,
)
from .file_operations import move_file_to_folder
from .artist_folders import get_or_create_artist_folder


class EditorMixin:

    def choose_file(self):

        path = filedialog.askopenfilename(
            title="CHOISIR UN FICHIER AUDIO",
            filetypes=[
                (
                    "FICHIERS AUDIO",
                    "*.mp3 *.wav *.flac *.m4a *.mp4 *.ogg *.opus",
                ),
                (
                    "TOUS LES FICHIERS",
                    "*.*",
                ),
            ],
        )

        if path:
            self.load_file(path)

    def handle_drop(self, event):

        paths = self.tk.splitlist(event.data)

        if not paths:
            return

        path = paths[0]

        if os.path.isfile(path):
            self.load_file(path)

    def load_file(self, path):

        try:

            audio = File(path, easy=False)

            if audio is None:
                raise ValueError("FORMAT AUDIO NON RECONNU.")

            self.current_file = path
            self.audio = audio

            self.clear_fields()
            self.load_metadata()
            if config.ENABLE_COVER_EDITOR:
                self.load_cover()
            self.update_file_info()
            self.load_waveform()

            if (
                config.ENABLE_AUDIO_ANALYSIS
                and not self.entries["bpm"].get().strip()
            ):
                self.calculate_bpm(show_error=False)

            filename = os.path.basename(path)

            self.drop_title.config(
                text=f"✓  {filename.upper()}",
            )

            self.status_label.config(
                text=f"Fichier chargé · {filename}",
                fg=MUTED,
            )
            self.save_button.config(state="normal")
            self.update_quick_selection_highlight()

        except Exception as e:

            messagebox.showerror(
                "ERREUR",
                f"IMPOSSIBLE DE CHARGER LE FICHIER.\n\n{e}",
            )

    def clear_fields(self):

        for entry in self.entries.values():
            entry.delete(0, tk.END)

        self.set_track_types(("STUDIO",))

        while len(self.artist_entries) > 1:
            item = self.artist_entries.pop()
            item["frame"].destroy()

        if self.artist_entries:
            self.artist_entries[0]["entry"].delete(0, tk.END)

    def read_tag(self, names):

        if not self.audio:
            return ""

        for name in names:

            try:

                value = self.audio.get(name)

                if value is None:
                    continue

                # Mutagen peut retourner une Frame ID3
                if hasattr(value, "text"):
                    value = value.text

                if isinstance(value, list):
                    if not value:
                        continue
                    value = value[0]

                if value is not None:
                    return str(value)

            except Exception:
                pass

        return ""

    def load_metadata(self):

        if not self.audio:
            return

        # ARTISTES
        artist_value = self.read_tag(
            [
                "TPE1",
                "\xa9ART",
                "artist",
            ]
        )

        if artist_value:

            artists = [
                x.strip()
                for x in re.split(
                    r"\s*&\s*|\s*;\s*",
                    artist_value,
                )
                if x.strip()
            ]

            if artists:

                self.artist_entries[0]["entry"].insert(
                    0,
                    uppercase_text(artists[0]),
                )

                for artist in artists[1:]:

                    self.add_artist_field()

                    self.artist_entries[-1]["entry"].insert(
                        0,
                        uppercase_text(artist),
                    )

        mapping = {
            "title": [
                "TIT2",
                "\xa9nam",
                "title",
            ],
            "album": [
                "TALB",
                "\xa9alb",
                "album",
            ],
            "albumartist": [
                "TPE2",
                "aART",
                "albumartist",
            ],
            "date": [
                "TDRC",
                "\xa9day",
                "date",
            ],
            "genre": [
                "TCON",
                "\xa9gen",
                "genre",
            ],
            "bpm": [
                "TBPM",
                "tmpo",
                "bpm",
            ],
            "tracknumber": [
                "TRCK",
                "trkn",
                "tracknumber",
            ],
            "composer": [
                "TCOM",
                "\xa9wrt",
                "composer",
            ],
            "comment": [
                "COMM::eng",
                "\xa9cmt",
                "comment",
            ],
        }

        for field, tags in mapping.items():

            value = self.read_tag(tags)

            if field == "title" and config.ENABLE_TRACK_TYPE:
                value, track_types = self.split_title_type(value)
                self.set_track_types(track_types)

            self.entries[field].insert(
                0,
                uppercase_text(value),
            )

    def split_title_type(self, title):

        match = re.fullmatch(
            r"(.*?)\s*\(([^()]*)\)\s*",
            title.strip(),
            flags=re.IGNORECASE,
        )

        if match:
            type_names = tuple(
                item.strip().upper()
                for item in match.group(2).split("+")
            )
            if (
                type_names
                and all(item in TRACK_TYPES for item in type_names)
                and len(set(type_names)) == len(type_names)
            ):
                return match.group(1).strip(), type_names

        return title, ("STUDIO",)

    def get_selected_track_types(self):

        if not config.ENABLE_TRACK_TYPE:
            return ()

        selected = getattr(self, "track_type_vars", {})
        return tuple(
            track_type
            for track_type in TRACK_TYPES
            if track_type in selected and selected[track_type].get()
        )

    def set_track_types(self, track_types):

        selected_types = set(track_types)
        if not selected_types:
            selected_types = {"STUDIO"}

        if not selected_types.issubset(TRACK_TYPES):
            raise ValueError("TYPE DE SON INVALIDE.")

        for track_type, variable in getattr(self, "track_type_vars", {}).items():
            variable.set(track_type in selected_types)

        self.track_type_var.set(" + ".join(
            track_type
            for track_type in TRACK_TYPES
            if track_type in selected_types
        ))
        self.update_type_help()

    def update_track_type_display(self):

        selected_types = self.get_selected_track_types()
        if not selected_types:
            self.set_track_types(("STUDIO",))
            return

        self.track_type_var.set(" + ".join(selected_types))
        self.update_type_help()

    def get_track_type_suffix(self):

        selected_types = self.get_selected_track_types()
        if not selected_types or selected_types == ("STUDIO",):
            return ""

        return f" ({' + '.join(selected_types)})"

    def get_formatted_title(self):

        title = uppercase_text(self.entries["title"].get())
        if not config.ENABLE_TRACK_TYPE:
            return title

        suffix = self.get_track_type_suffix()
        if title and suffix:
            return f"{title}{suffix}"

        return title

    def save_metadata(self):

        if not self.current_file:
            raise ValueError("AUCUN FICHIER CHARGÉ.")

        values = {
            key: uppercase_text(entry.get())
            for key, entry in self.entries.items()
        }
        values["title"] = self.get_formatted_title()

        if values["bpm"] and not re.fullmatch(r"[1-9][0-9]{0,2}", values["bpm"]):
            raise ValueError(
                "BPM INVALIDE. UTILISE UN NOMBRE ENTIER ENTRE 1 ET 999."
            )

        artists = self.get_artists()

        if not artists:
            artists = ["ARTISTE INCONNU"]

        combined_artist = " & ".join(artists)
        values["artist"] = combined_artist

        extension = get_extension(self.current_file)

        # ----------------------------------------------------
        # MP3 / WAV (tags ID3)
        # ----------------------------------------------------

        if extension in (".mp3", ".wav"):

            if extension == ".wav":
                audio = WAVE(self.current_file)
                if audio.tags is None:
                    audio.add_tags()
                tags = audio.tags
            else:
                try:
                    tags = ID3(self.current_file)
                except Exception:
                    tags = ID3()

            # IMPORTANT :
            # Chaque Frame ID3 reçoit UNE LISTE de texte.
            # C'est la correction du problème "not a Frame instance".

            # ARTISTE
            tags.delall("TPE1")
            tags["TPE1"] = TPE1(
                encoding=3,
                text=[combined_artist],
            )

            # TITRE
            tags.delall("TIT2")
            if values["title"]:
                tags["TIT2"] = TIT2(
                    encoding=3,
                    text=[values["title"]],
                )

            # ALBUM
            tags.delall("TALB")
            if values["album"]:
                tags["TALB"] = TALB(
                    encoding=3,
                    text=[values["album"]],
                )

            # ARTISTE ALBUM
            tags.delall("TPE2")
            if values["albumartist"]:
                tags["TPE2"] = TPE2(
                    encoding=3,
                    text=[values["albumartist"]],
                )

            # DATE
            tags.delall("TDRC")
            if values["date"]:
                tags["TDRC"] = TDRC(
                    encoding=3,
                    text=[values["date"]],
                )

            # GENRE
            tags.delall("TCON")
            if values["genre"]:
                tags["TCON"] = TCON(
                    encoding=3,
                    text=[values["genre"]],
                )

            # BPM
            tags.delall("TBPM")
            if values["bpm"]:
                tags["TBPM"] = TBPM(
                    encoding=3,
                    text=[values["bpm"]],
                )

            # PISTE
            tags.delall("TRCK")
            if values["tracknumber"]:
                tags["TRCK"] = TRCK(
                    encoding=3,
                    text=[values["tracknumber"]],
                )

            # COMPOSITEUR
            tags.delall("TCOM")
            if values["composer"]:
                tags["TCOM"] = TCOM(
                    encoding=3,
                    text=[values["composer"]],
                )

            # COMMENTAIRE
            tags.delall("COMM")
            if values["comment"]:
                tags["COMM:Comment"] = COMM(
                    encoding=3,
                    lang="eng",
                    desc="Comment",
                    text=[values["comment"]],
                )

            if extension == ".wav":
                audio.save()
            else:
                tags.save(self.current_file)

        # ----------------------------------------------------
        # M4A / MP4
        # ----------------------------------------------------

        elif extension in (".m4a", ".mp4"):

            audio = MP4(self.current_file)

            if audio.tags is None:
                audio.add_tags()

            mapping = {
                "artist": "\xa9ART",
                "title": "\xa9nam",
                "album": "\xa9alb",
                "albumartist": "aART",
                "date": "\xa9day",
                "genre": "\xa9gen",
                "composer": "\xa9wrt",
                "comment": "\xa9cmt",
            }

            for field, tag in mapping.items():

                value = values[field]

                if value:
                    audio[tag] = [value]
                elif tag in audio:
                    del audio[tag]

            # BPM
            if values["bpm"]:
                audio["tmpo"] = [int(values["bpm"])]
            elif "tmpo" in audio:
                del audio["tmpo"]

            # Piste
            if values["tracknumber"]:

                try:

                    track_value = values["tracknumber"].split("/")[0]
                    number = int(track_value)

                    audio["trkn"] = [(number, 0)]

                except Exception:
                    raise ValueError(
                        "NUMÉRO DE PISTE INVALIDE.\n"
                        "UTILISE PAR EXEMPLE : 1 OU 1/12."
                    )

            elif "trkn" in audio:
                del audio["trkn"]

            audio.save()

        # ----------------------------------------------------
        # FLAC / OGG / OPUS
        # ----------------------------------------------------

        elif extension in (".flac", ".ogg", ".opus"):

            audio = File(self.current_file, easy=True)

            if audio is None:
                raise ValueError("FORMAT AUDIO NON SUPPORTÉ.")

            # Easy tags
            easy_values = {
                "artist": values["artist"],
                "title": values["title"],
                "album": values["album"],
                "albumartist": values["albumartist"],
                "date": values["date"],
                "genre": values["genre"],
                "bpm": values["bpm"],
                "tracknumber": values["tracknumber"],
                "composer": values["composer"],
                "comment": values["comment"],
            }

            for field, value in easy_values.items():

                if value:
                    audio[field] = [value]
                elif field in audio:
                    del audio[field]

            audio.save()

        else:
            raise ValueError(
                f"FORMAT NON SUPPORTÉ : {extension.upper()}"
            )

    def get_available_path(self, path):

        base, extension = os.path.splitext(path)
        index = 2
        candidate = path

        while os.path.exists(candidate):
            candidate = f"{base} ({index}){extension}"
            index += 1

        return candidate

    def rename_file(self):

        if not self.current_file:
            return
        if not config.ENABLE_FILE_RENAMING:
            return True

        artists = self.get_artists()

        if artists:
            artist_name = " & ".join(artists)
        else:
            artist_name = "ARTISTE INCONNU"

        title = self.get_formatted_title()

        if not title:
            title = f"SANS TITRE{self.get_track_type_suffix()}"

        artist_name = clean_filename(artist_name)
        title = clean_filename(title)

        extension = get_extension(self.current_file)

        new_filename = f"{artist_name} - {title}{extension}"

        folder = os.path.dirname(self.current_file)
        new_path = os.path.join(folder, new_filename)

        # Même fichier
        if os.path.abspath(new_path) == os.path.abspath(self.current_file):
            return

        # Libère la référence au fichier avant de demander à Windows
        # de le renommer ou de remplacer un fichier existant.
        self.audio = None

        # Le nom existe déjà
        if os.path.exists(new_path):

            answer = messagebox.askyesno(
                "FICHIER EXISTANT",
                (
                    f"Le fichier\n\n{new_filename}\n\n"
                    "existe déjà.\n\n"
                    "Voulez-vous le remplacer ?"
                ),
            )

            if not answer:
                return False

            try:
                os.replace(self.current_file, new_path)
            except PermissionError:
                new_path = self.get_available_path(new_path)

                messagebox.showwarning(
                    "FICHIER VERROUILLÉ",
                    (
                        "LE FICHIER EXISTANT EST UTILISÉ PAR UNE AUTRE "
                        "APPLICATION.\n\n"
                        "LES MODIFICATIONS SERONT CONSERVÉES SOUS :\n"
                        f"{os.path.basename(new_path)}"
                    ),
                )

                os.rename(self.current_file, new_path)
        else:
            os.rename(self.current_file, new_path)

        self.current_file = new_path

        return True

    def get_artist_folder_warning(self):

        artists = self.get_artists()
        if (
            not self.current_file
            or not artists
            or not config.ENABLE_ARTIST_FOLDER_CHECK
            or self.is_excluded_path(self.current_file)
        ):
            return None

        folder_name = os.path.basename(
            os.path.dirname(self.current_file)
        ).strip()
        artist_name = artists[0].strip()

        if folder_name.casefold() == clean_filename(artist_name).casefold():
            return None

        return folder_name, artist_name

    def save_all(self):

        if not self.current_file:

            messagebox.showwarning(
                "AUCUN FICHIER",
                "CHARGE D'ABORD UN FICHIER AUDIO.",
            )
            return

        try:

            self.force_all_uppercase()

            # Vérification minimale
            artists = self.get_artists()
            title = uppercase_text(self.entries["title"].get())

            if not artists:
                messagebox.showwarning(
                    "⚠️ ARTISTE MANQUANT",
                    "Aucun artiste n'a été renseigné.\n\n"
                    "Le programme utilisera : ARTISTE INCONNU",
                )

            if not title:
                messagebox.showwarning(
                    "⚠️ TITRE MANQUANT",
                    "Aucun titre n'a été renseigné.\n\n"
                    "Le programme utilisera : SANS TITRE",
                )

            # 1. Métadonnées
            self.save_metadata()

            # 2. Pochette
            if config.ENABLE_COVER_EDITOR:
                self.save_cover()

            # 3. Renommage
            if config.ENABLE_FILE_RENAMING:
                self.rename_file()
            source_path = self.current_file
            self.audio = None
            try:
                first_artist = artists[0] if artists else "ARTISTE INCONNU"
                artist_folder = get_or_create_artist_folder(
                    config.MONITORED_FOLDER,
                    first_artist,
                )
                self.current_file = move_file_to_folder(
                    source_path,
                    artist_folder,
                )
            except OSError as error:
                self.load_file(source_path)
                self.status_label.config(
                    text="Enregistré · déplacement impossible",
                    fg=WARNING,
                )
                messagebox.showerror(
                    "DÉPLACEMENT IMPOSSIBLE",
                    "LES MÉTADONNÉES ONT BIEN ÉTÉ ENREGISTRÉES, MAIS LE "
                    "FICHIER N'A PAS PU ÊTRE RANGÉ DANS LE DOSSIER DU "
                    f"PREMIER ARTISTE « {first_artist} » SOUS :\n"
                    f"{config.MONITORED_FOLDER}\n\n"
                    f"LE FICHIER EST RESTÉ ICI :\n{source_path}\n\n{error}",
                )
                return
            except ValueError as error:
                self.load_file(source_path)
                self.status_label.config(
                    text="Enregistré · dossier artiste invalide",
                    fg=WARNING,
                )
                messagebox.showerror(
                    "DOSSIER ARTISTE IMPOSSIBLE",
                    "LES MÉTADONNÉES ONT ÉTÉ ENREGISTRÉES, MAIS LE DOSSIER "
                    f"DU PREMIER ARTISTE N'A PAS PU ÊTRE UTILISÉ :\n\n{error}",
                )
                return

            self.artist_folder_names = sorted(
                set(self.artist_folder_names) | {os.path.basename(artist_folder)},
                key=str.casefold,
            )
            for item in self.artist_entries:
                self.refresh_artist_option_menu(item)

            # 4. Recharge le fichier avec ses nouvelles métadonnées
            self.load_file(self.current_file)
            self.refresh_quick_selection()
            folder_warning = self.get_artist_folder_warning()

            filename = os.path.basename(self.current_file)
            destination_message = (
                f"\n\nFICHIER DÉPLACÉ DANS LE DOSSIER DU PREMIER ARTISTE :\n"
                f"{artist_folder}"
            )

            self.status_label.config(
                text=f"Enregistré · déplacé · {filename}",
                fg=WARNING if folder_warning else SUCCESS,
            )

            if folder_warning:
                folder_name, artist_name = folder_warning
                messagebox.showwarning(
                    "EMPLACEMENT À VÉRIFIER",
                    (
                        "LES MODIFICATIONS ONT BIEN ÉTÉ ENREGISTRÉES.\n\n"
                        f"NOUVEAU NOM :\n{filename.upper()}\n\n"
                        f"FICHIER DÉPLACÉ VERS :\n{artist_folder}\n\n"
                        f"LE DOSSIER D'ORIGINE « {folder_name} » NE "
                        f"CORRESPONDAIT PAS AU PREMIER ARTISTE "
                        f"« {artist_name} »."
                    ),
                )
            else:
                messagebox.showinfo(
                    "ENREGISTREMENT TERMINÉ",
                    (
                        "✓ LES MODIFICATIONS ONT ÉTÉ ENREGISTRÉES.\n\n"
                        f"NOUVEAU NOM :\n{filename.upper()}"
                        f"{destination_message}"
                    ),
                )

        except Exception as e:

            messagebox.showerror(
                "❌ ERREUR",
                (
                    "IMPOSSIBLE D'ENREGISTRER LES MODIFICATIONS.\n\n"
                    f"{type(e).__name__} : {e}"
                ),
            )

    def update_file_info(self):

        if not self.audio:
            return

        try:

            info = self.audio.info

            duration = getattr(info, "length", 0)
            bitrate = getattr(info, "bitrate", None)
            sample_rate = getattr(info, "sample_rate", None)
            channels = getattr(info, "channels", None)

            minutes = int(duration // 60)
            seconds = int(duration % 60)

            lines = [
                f"DURÉE       : {minutes}:{seconds:02d}",
            ]

            if bitrate:
                lines.append(
                    f"BITRATE     : {bitrate // 1000} KBPS"
                )

            if sample_rate:
                lines.append(
                    f"FRÉQUENCE   : {sample_rate} HZ"
                )

            if channels:
                lines.append(
                    f"CANAUX      : {channels}"
                )

            self.info_label.config(
                text="\n".join(lines),
            )

        except Exception:
            self.info_label.config(text="")
