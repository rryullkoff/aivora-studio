"""Cover behaviors for Aivora Studio."""

from .dependencies import (
    APIC,
    File,
    ID3,
    Image,
    ImageTk,
    MP4,
    MP4Cover,
    WAVE,
    filedialog,
    io,
    messagebox,
    tk,
)
from .config import (
    ACCENT,
    ACCENT_HOVER,
    CARD,
    CARD_2,
    DANGER,
    DANGER_HOVER,
    MUTED,
    TEXT,
)
from .helpers import (
    get_extension,
    image_to_jpeg,
)


class CoverMixin:

    def create_cover_panel(self, parent):

        panel = tk.Frame(
            parent,
            bg=CARD,
            width=340,
        )
        self.cover_panel = panel
        panel.pack(
            side="right",
            fill="y",
            padx=(10, 0),
        )
        panel.pack_propagate(False)

        tk.Label(
            panel,
            text="Pochette",
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 14, "bold"),
        ).pack(anchor="w", padx=20, pady=(18, 3))

        tk.Label(
            panel,
            text="La pochette sera conservée dans le fichier audio.",
            bg=CARD,
            fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=20)

        cover_container = tk.Frame(
            panel,
            bg=CARD_2,
            width=260,
            height=260,
        )
        cover_container.pack(pady=20)
        cover_container.pack_propagate(False)

        self.cover_label = tk.Label(
            cover_container,
            text="♪\n\nAUCUNE POCHETTE",
            bg=CARD_2,
            fg=MUTED,
            font=("Segoe UI", 10),
        )
        self.cover_label.pack(fill="both", expand=True)

        buttons = tk.Frame(panel, bg=CARD)
        buttons.pack(fill="x", padx=20)

        tk.Button(
            buttons,
            text="🖼  Remplacer",
            command=self.replace_cover,
            bg=ACCENT,
            fg="white",
            activebackground=ACCENT_HOVER,
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=9,
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 4),
        )

        tk.Button(
            buttons,
            text="🗑  Supprimer",
            command=self.remove_cover,
            bg=DANGER,
            fg="white",
            activebackground=DANGER_HOVER,
            relief="flat",
            borderwidth=0,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=9,
        ).pack(
            side="right",
            fill="x",
            expand=True,
            padx=(4, 0),
        )

        self.info_label = tk.Label(
            panel,
            text="",
            bg=CARD,
            fg=MUTED,
            justify="left",
            anchor="w",
            font=("Segoe UI", 9),
        )
        self.info_label.pack(fill="x", padx=20, pady=20)

    def load_cover(self):

        self.cover_data = None
        self.cover_photo = None

        extension = get_extension(self.current_file)

        # MP3 / WAV (tags ID3)
        if extension in (".mp3", ".wav"):

            try:

                if extension == ".wav":
                    tags = WAVE(self.current_file).tags
                else:
                    tags = ID3(self.current_file)

                if tags is None:
                    raise ValueError("AUCUN TAG ID3")

                for frame in tags.values():

                    if isinstance(frame, APIC):

                        self.cover_data = frame.data
                        self.display_cover(self.cover_data)
                        return

            except Exception:
                pass

        # M4A / MP4
        if extension in (".m4a", ".mp4"):

            try:

                mp4 = MP4(self.current_file)

                if mp4.tags:

                    covers = mp4.tags.get("covr", [])

                    if covers:

                        self.cover_data = bytes(covers[0])
                        self.display_cover(self.cover_data)
                        return

            except Exception:
                pass

        # FLAC
        if extension == ".flac":

            try:

                pictures = self.audio.pictures

                if pictures:

                    self.cover_data = pictures[0].data
                    self.display_cover(self.cover_data)
                    return

            except Exception:
                pass

        self.show_no_cover()

    def display_cover(self, data):

        try:

            image = Image.open(io.BytesIO(data))
            image.thumbnail(
                (250, 250),
                Image.Resampling.LANCZOS,
            )

            self.cover_photo = ImageTk.PhotoImage(image)

            self.cover_label.config(
                image=self.cover_photo,
                text="",
            )

        except Exception:
            self.show_no_cover()

    def show_no_cover(self):

        self.cover_photo = None

        self.cover_label.config(
            image="",
            text="♪\n\nAUCUNE POCHETTE",
        )

    def replace_cover(self):

        if not self.current_file:

            messagebox.showwarning(
                "AUCUN FICHIER",
                "CHARGE D'ABORD UN FICHIER AUDIO.",
            )
            return

        path = filedialog.askopenfilename(
            title="CHOISIR UNE POCHETTE",
            filetypes=[
                (
                    "IMAGES",
                    "*.jpg *.jpeg *.png *.webp",
                )
            ],
        )

        if not path:
            return

        try:

            with open(path, "rb") as file:
                self.cover_data = file.read()

            # Vérifie immédiatement que l'image est lisible
            Image.open(io.BytesIO(self.cover_data)).verify()

            self.display_cover(self.cover_data)

            self.status_label.config(
                text="NOUVELLE POCHETTE SÉLECTIONNÉE • CLIQUE SUR ENREGISTRER",
                fg=ACCENT,
            )

        except Exception as e:

            self.cover_data = None

            messagebox.showerror(
                "❌ POCHETTE INVALIDE",
                f"L'image ne peut pas être utilisée.\n\n{e}",
            )

    def remove_cover(self):

        if not self.current_file:
            return

        result = messagebox.askyesno(
            "SUPPRIMER LA POCHETTE",
            "SUPPRIMER LA POCHETTE DU FICHIER ?",
        )

        if not result:
            return

        self.cover_data = None
        self.show_no_cover()

        self.status_label.config(
            text="POCHETTE SUPPRIMÉE • CLIQUE SUR ENREGISTRER",
            fg=DANGER,
        )

    def save_cover(self):

        if not self.current_file:
            return

        extension = get_extension(self.current_file)

        # MP3 / WAV (tags ID3)
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

            tags.delall("APIC")

            if self.cover_data:

                jpeg_data = image_to_jpeg(self.cover_data)

                tags["APIC:Cover"] = APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,
                    desc="Cover",
                    data=jpeg_data,
                )

            if extension == ".wav":
                audio.save()
            else:
                tags.save(self.current_file)

        # M4A / MP4
        elif extension in (".m4a", ".mp4"):

            audio = MP4(self.current_file)

            if audio.tags is None:
                audio.add_tags()

            if self.cover_data:

                jpeg_data = image_to_jpeg(self.cover_data)

                audio["covr"] = [
                    MP4Cover(
                        jpeg_data,
                        imageformat=MP4Cover.FORMAT_JPEG,
                    )
                ]

            else:
                audio["covr"] = []

            audio.save()

        # FLAC
        elif extension == ".flac":

            audio = File(self.current_file)

            if audio is None:
                raise ValueError("FICHIER FLAC NON RECONNU.")

            audio.clear_pictures()

            if self.cover_data:

                from mutagen.flac import Picture

                jpeg_data = image_to_jpeg(self.cover_data)

                picture = Picture()
                picture.type = 3
                picture.mime = "image/jpeg"
                picture.desc = "Cover"
                picture.data = jpeg_data

                audio.add_picture(picture)

            audio.save()

        # OGG / OPUS
        else:
            # La gestion des pochettes Vorbis/Opus dépend du conteneur
            # et n'est volontairement pas modifiée ici.
            if self.cover_data is not None:
                raise ValueError(
                    "LA GESTION DE POCHETTE POUR OGG/OPUS N'EST PAS "
                    "ACTIVÉE DANS CETTE VERSION."
                )
