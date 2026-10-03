"""Standalone PySide6 interface prototype for the upcoming 1.1 redesign."""

import os
import re
import shutil
import tempfile
import base64
import sys
from array import array

from PySide6.QtCore import QProcess, QSettings, QThread, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from mutagen import File, MutagenError
from mutagen.id3 import (
    APIC,
    COMM,
    ID3,
    ID3NoHeaderError,
    TALB,
    TBPM,
    TCOM,
    TCON,
    TDRC,
    TIT2,
    TPE1,
    TPE2,
    TRCK,
)
from mutagen.flac import Picture
from mutagen.mp4 import MP4, MP4Cover
from shiboken6 import delete as delete_qobject

from . import config
from .config import VERSION
from .helpers import clean_filename, image_to_jpeg, uppercase_text
from .version_history import VERSION_HISTORY
from .qt_theme import (
    DENSITY,
    DENSITY_PRESETS,
    THEME,
    THEME_PRESETS,
    apply_density,
    apply_theme,
    build_stylesheet,
)


class WaveformWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.peaks = []
        self.setMinimumHeight(76)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center_y = self.height() / 2
        bar_count = max(1, self.width() // 7)
        gradient = QColor(THEME["accent"])
        painter.setPen(QPen(QColor(THEME["surface_raised"]), 1))
        painter.drawLine(0, round(center_y), self.width(), round(center_y))

        for index in range(bar_count):
            if self.peaks:
                peak_index = min(
                    len(self.peaks) - 1,
                    index * len(self.peaks) // bar_count,
                )
                envelope = self.peaks[peak_index]
            else:
                envelope = 0.02
            height = max(2, envelope * (self.height() - 12))
            x = index * 7 + 2
            painter.setPen(
                QPen(
                    gradient,
                    3,
                    Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.RoundCap,
                )
            )
            painter.drawLine(
                x,
                round(center_y - height / 2),
                x,
                round(center_y + height / 2),
            )


class DropZone(QFrame):

    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                self.file_dropped.emit(path)
                event.acceptProposedAction()
                return
        event.ignore()


class QuickSelectionScan(QThread):

    completed = Signal(object, object)

    def run(self):
        root = config.EXCLUDED_FOLDER
        files = []
        errors = []
        if not os.path.isdir(root):
            self.completed.emit(files, [f"Dossier introuvable : {root}"])
            return

        def record_error(error):
            errors.append(str(error))

        for directory, _, filenames in os.walk(root, onerror=record_error):
            if self.isInterruptionRequested():
                return
            for filename in filenames:
                if self.isInterruptionRequested():
                    return
                if os.path.splitext(filename)[1].lower() in config.AUDIO_EXTENSIONS:
                    files.append(os.path.join(directory, filename))
        files.sort(key=str.casefold)
        self.completed.emit(files, errors)


class PreviewWindow(QMainWindow):

    TRACK_TYPES = ("LIVE", "STUDIO", "EXTRAIT", "MAP")
    FEATURE_LABELS = (
        "Édition des métadonnées",
        "Types multiples",
        "Pochettes",
        "Forme d’onde et lecture",
        "Calcul du BPM",
        "Conversion MP3",
        "Réparation audio",
        "Surveillance automatique",
        "Sélection rapide",
        "Renommage automatique",
        "Vérification du dossier artiste",
        "Déplacer après enregistrement",
    )
    FEATURE_DEFAULTS = {
        "Déplacer après enregistrement": True,
    }

    def __init__(self, preferences=None):
        super().__init__()
        self.setWindowTitle("Aivora Studio • Aperçu PySide6")
        self.resize(1100, 820)
        self.setMinimumSize(900, 680)
        self.preferences = preferences or QSettings(
            "Aivora Studio",
            "QtPreview",
        )
        self.theme_name = self.preferences.value(
            "appearance/theme",
            "Sombre · Violet",
            type=str,
        )
        if self.theme_name not in THEME_PRESETS:
            self.theme_name = "Sombre · Violet"
        self.density_name = self.preferences.value(
            "appearance/density",
            "Confortable",
            type=str,
        )
        if self.density_name not in DENSITY_PRESETS:
            self.density_name = "Confortable"
        apply_theme(self.theme_name)
        apply_density(self.density_name)
        self.selected_types = set()
        self.current_audio_path = ""
        self.loaded_from_quick_selection = False
        self.audio_is_playing = False
        self.cover_data = None
        self.cover_changed = False
        self.audio_pcm = b""
        self.audio_duration_ms = 0
        self.audio_process = None
        self.audio_output = QAudioOutput(self)
        self.create_media_player()
        self.feature_toggles = {
            label: self.preferences.value(
                f"features/{label}",
                self.FEATURE_DEFAULTS.get(label, True),
                type=bool,
            )
            for label in self.FEATURE_LABELS
        }
        QApplication.instance().setStyleSheet(build_stylesheet())

        root = QWidget()
        root.setObjectName("appRoot")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(30, 24, 30, 22)
        layout.setSpacing(16)

        header = QHBoxLayout()
        brand = QVBoxLayout()
        title = QLabel("Aivora Studio")
        title.setStyleSheet("font-size: 24pt; font-weight: 750;")
        subtitle = QLabel(
            "Aperçu de l’interface personnalisable en préparation pour 1.1"
        )
        subtitle.setProperty("role", "muted")
        brand.addWidget(title)
        brand.addWidget(subtitle)
        header.addLayout(brand)
        header.addStretch(1)

        header_actions = QVBoxLayout()
        modal_buttons = QHBoxLayout()
        self.version_button = QPushButton("Versions")
        self.version_button.clicked.connect(self.show_versions)
        self.anomalies_button = QPushButton("Anomalies · 2")
        self.anomalies_button.clicked.connect(self.show_anomalies)
        self.settings_button = QPushButton("Paramètres")
        self.settings_button.clicked.connect(self.show_settings)
        for button in (
            self.version_button,
            self.anomalies_button,
            self.settings_button,
        ):
            modal_buttons.addWidget(button)
        header_actions.addLayout(modal_buttons)
        version_badge = QLabel(f"APERÇU • PYSIDE6 · {VERSION}")
        version_badge.setAlignment(Qt.AlignmentFlag.AlignRight)
        version_badge.setProperty("role", "eyebrow")
        header_actions.addWidget(version_badge)
        header.addLayout(header_actions)
        layout.addLayout(header)
        self.preview_status = QLabel(
            "Maquette interactive · les outils audio ne modifient pas les fichiers."
        )
        self.preview_status.setProperty("role", "muted")
        layout.addWidget(self.preview_status)

        update_card = QFrame()
        update_card.setProperty("card", True)
        update_layout = QHBoxLayout(update_card)
        update_layout.setContentsMargins(16, 12, 16, 12)
        update_title = QLabel("PROCHAINE MISE À JOUR")
        update_title.setProperty("role", "eyebrow")
        update_layout.addWidget(update_title)
        update_layout.addStretch(1)
        update_layout.addWidget(QLabel("Vendredi 9 octobre 2026 • 18 h"))
        layout.addWidget(update_card)

        self.drop_zone = DropZone()
        drop_layout = QVBoxLayout(self.drop_zone)
        drop_layout.setContentsMargins(20, 20, 20, 20)
        drop_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_title = QLabel("Dépose ton fichier audio ici")
        drop_title.setStyleSheet("font-size: 15pt; font-weight: 700;")
        drop_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_label = QLabel("MP3 • WAV • FLAC • M4A • OGG • OPUS")
        self.file_label.setProperty("role", "muted")
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.choose_button = QPushButton("Choisir un fichier")
        self.choose_button.setProperty("primary", True)
        self.choose_button.clicked.connect(self.choose_file)
        drop_layout.addWidget(drop_title)
        drop_layout.addWidget(self.file_label)
        drop_layout.addSpacing(6)
        drop_layout.addWidget(
            self.choose_button,
            alignment=Qt.AlignmentFlag.AlignHCenter,
        )
        self.drop_zone.file_dropped.connect(self.show_selected_file)
        layout.addWidget(self.drop_zone)

        self.quick_selection_card = QFrame()
        self.quick_selection_card.setProperty("card", True)
        quick_layout = QVBoxLayout(self.quick_selection_card)
        quick_layout.setContentsMargins(14, 10, 14, 10)
        quick_header = QHBoxLayout()
        quick_title = QLabel("SÉLECTION RAPIDE · DOSSIER EXCLU")
        quick_title.setProperty("role", "eyebrow")
        quick_header.addWidget(quick_title)
        self.quick_selection_info = QLabel("Chargement…")
        self.quick_selection_info.setProperty("role", "muted")
        quick_header.addWidget(self.quick_selection_info)
        quick_header.addStretch(1)
        self.quick_previous_button = QPushButton("‹")
        self.quick_previous_button.clicked.connect(
            lambda: self.show_quick_selection_page(
                self.quick_selection_page - 1
            )
        )
        self.quick_page_label = QLabel("—")
        self.quick_page_label.setProperty("role", "muted")
        self.quick_next_button = QPushButton("›")
        self.quick_next_button.clicked.connect(
            lambda: self.show_quick_selection_page(
                self.quick_selection_page + 1
            )
        )
        self.quick_refresh_button = QPushButton("Actualiser")
        self.quick_refresh_button.clicked.connect(
            self.refresh_quick_selection
        )
        for button in (
            self.quick_previous_button,
            self.quick_page_label,
            self.quick_next_button,
            self.quick_refresh_button,
        ):
            quick_header.addWidget(button)
        quick_layout.addLayout(quick_header)
        self.quick_selection_files_layout = QHBoxLayout()
        self.quick_selection_files_layout.setSpacing(8)
        quick_layout.addLayout(self.quick_selection_files_layout)
        self.quick_selection_files = []
        self.quick_selection_errors = []
        self.quick_selection_page = 0
        layout.addWidget(self.quick_selection_card)

        columns = QHBoxLayout()
        columns.setSpacing(16)
        metadata = QFrame()
        self.metadata_card = metadata
        metadata.setProperty("card", True)
        metadata_layout = QVBoxLayout(metadata)
        metadata_layout.setContentsMargins(20, 18, 20, 20)
        metadata_layout.setSpacing(11)
        section_title = QLabel("Métadonnées")
        section_title.setStyleSheet("font-size: 15pt; font-weight: 700;")
        metadata_layout.addWidget(section_title)
        self.metadata_scroll = QScrollArea()
        self.metadata_scroll.setWidgetResizable(True)
        self.metadata_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.metadata_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        metadata_content = QWidget()
        fields_layout = QVBoxLayout(metadata_content)
        fields_layout.setContentsMargins(0, 0, 4, 0)
        fields_layout.setSpacing(9)
        self.title_input = self.add_field(
            fields_layout,
            "NOM DU SON",
            "Titre du morceau",
        )
        self.artist_input = self.add_field(
            fields_layout,
            "ARTISTE",
            "Nom de l’artiste",
        )

        type_title = QLabel("TYPE")
        type_title.setProperty("role", "eyebrow")
        self.type_title = type_title
        fields_layout.addWidget(type_title)
        type_row = QHBoxLayout()
        self.type_buttons = {}
        for track_type in self.TRACK_TYPES:
            button = QToolButton()
            button.setText(track_type)
            button.setCheckable(True)
            button.setProperty("trackType", True)
            button.toggled.connect(
                lambda checked, value=track_type: self.toggle_type(value, checked)
            )
            self.type_buttons[track_type] = button
            type_row.addWidget(button)
        fields_layout.addLayout(type_row)

        self.metadata_fields = {}
        for key, label, placeholder in (
            ("album", "ALBUM", "Nom de l’album"),
            ("album_artist", "ARTISTE ALBUM", "Artiste de l’album"),
            ("year", "ANNÉE", "2026"),
            ("genre", "GENRE", "Genre musical"),
            ("bpm", "BPM", "120"),
            ("track", "PISTE", "1"),
            ("composer", "COMPOSITEUR", "Nom du compositeur"),
            ("comment", "COMMENTAIRE", "Commentaire"),
        ):
            self.metadata_fields[key] = self.add_field(
                fields_layout,
                label,
                placeholder,
            )
        fields_layout.addStretch(1)
        self.metadata_scroll.setWidget(metadata_content)
        metadata_layout.addWidget(self.metadata_scroll, 1)

        cover = QFrame()
        self.cover_card = cover
        cover.setProperty("card", True)
        cover.setMinimumWidth(260)
        cover.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        cover_layout = QVBoxLayout(cover)
        cover_layout.setContentsMargins(20, 18, 20, 20)
        cover_title = QLabel("Pochette")
        cover_title.setStyleSheet("font-size: 15pt; font-weight: 700;")
        cover_layout.addWidget(cover_title)
        self.cover_preview = QLabel("♪\n\nAUCUNE POCHETTE")
        self.cover_preview.setObjectName("coverPreview")
        self.cover_preview.setProperty("role", "coverPlaceholder")
        self.cover_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_preview.setMinimumHeight(200)
        self.cover_preview.setScaledContents(False)
        cover_layout.addWidget(self.cover_preview, 1)
        cover_actions = QHBoxLayout()
        self.replace_cover_button = QPushButton("Ajouter / remplacer")
        self.replace_cover_button.clicked.connect(self.choose_cover)
        self.replace_cover_button.setEnabled(False)
        self.remove_cover_button = QPushButton("Supprimer")
        self.remove_cover_button.clicked.connect(self.remove_cover)
        self.remove_cover_button.setEnabled(False)
        cover_actions.addWidget(self.replace_cover_button)
        cover_actions.addWidget(self.remove_cover_button)
        cover_layout.addLayout(cover_actions)
        waveform_card = QFrame()
        self.waveform_card = waveform_card
        waveform_card.setProperty("card", True)
        waveform_layout = QVBoxLayout(waveform_card)
        waveform_layout.setContentsMargins(18, 14, 18, 14)
        waveform_header = QHBoxLayout()
        waveform_title = QLabel("Forme d’onde")
        waveform_title.setStyleSheet("font-weight: 700;")
        waveform_header.addWidget(waveform_title)
        waveform_header.addStretch(1)
        self.waveform_time_label = QLabel("00:00 / 03:24")
        waveform_header.addWidget(self.waveform_time_label)
        waveform_layout.addLayout(waveform_header)
        self.waveform = WaveformWidget()
        waveform_layout.addWidget(self.waveform)
        playback = QHBoxLayout()
        self.play_button = QPushButton("▶  Lecture")
        self.play_button.clicked.connect(self.toggle_playback)
        self.play_button.setEnabled(False)
        playback.addWidget(self.play_button)
        playback.addStretch(1)
        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.setValue(0)
        self.seek_slider.setEnabled(False)
        self.seek_slider.valueChanged.connect(self.update_waveform_time)
        self.seek_slider.sliderMoved.connect(self.media_player.setPosition)
        waveform_layout.addWidget(self.seek_slider)
        self.bpm_button = QPushButton("Calculer le BPM")
        self.bpm_button.clicked.connect(self.show_bpm_preview)
        self.bpm_button.setEnabled(False)
        playback.addWidget(self.bpm_button)
        self.bpm_badge = QLabel("BPM · —")
        self.bpm_badge.setProperty("role", "eyebrow")
        playback.addWidget(self.bpm_badge)
        waveform_layout.addLayout(playback)
        columns.addWidget(metadata, 3)
        columns.addWidget(cover, 2)
        layout.addLayout(columns, 1)
        layout.addWidget(waveform_card)

        self.tools_card = QFrame()
        self.tools_card.setProperty("card", True)
        tools_layout = QHBoxLayout(self.tools_card)
        tools_layout.setContentsMargins(14, 10, 14, 10)
        tools_title = QLabel("OUTILS AUDIO")
        tools_title.setProperty("role", "eyebrow")
        tools_layout.addWidget(tools_title)
        tools_layout.addStretch(1)
        self.convert_button = QPushButton("Convertir en MP3")
        self.convert_button.clicked.connect(
            lambda: self.show_tool_preview("Conversion MP3")
        )
        self.repair_button = QPushButton("Réparer un fichier")
        self.repair_button.clicked.connect(
            lambda: self.show_tool_preview("Réparation audio")
        )
        tools_layout.addWidget(self.convert_button)
        tools_layout.addWidget(self.repair_button)
        layout.addWidget(self.tools_card)

        footer = QHBoxLayout()
        self.save_status = QLabel(
            "Aperçu visuel · les métadonnées ne sont pas encore enregistrées."
        )
        self.save_status.setProperty("role", "muted")
        footer.addWidget(self.save_status)
        footer.addStretch(1)
        self.file_placement_hint = QLabel(
            "Emplacement artiste · vérification visuelle uniquement."
        )
        self.file_placement_hint.setProperty("role", "muted")
        footer.addWidget(self.file_placement_hint)
        self.renaming_hint = QLabel("Nommage automatique · aperçu")
        self.renaming_hint.setProperty("role", "muted")
        footer.addWidget(self.renaming_hint)
        self.save_button = QPushButton("Enregistrer les modifications")
        self.save_button.setProperty("primary", True)
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_preview)
        footer.addWidget(self.save_button)
        layout.addLayout(footer)
        self.apply_feature_visibility()
        self.apply_density_to_widget(self)
        self.refresh_quick_selection()

    def apply_appearance(
        self,
        theme_name=None,
        density_name=None,
        persist=True,
    ):

        if theme_name is not None:
            apply_theme(theme_name)
            self.theme_name = theme_name
            if persist:
                self.preferences.setValue("appearance/theme", theme_name)

        if density_name is not None:
            apply_density(density_name)
            self.density_name = density_name
            if persist:
                self.preferences.setValue("appearance/density", density_name)

        stylesheet = build_stylesheet()
        QApplication.instance().setStyleSheet(stylesheet)
        for widget in QApplication.topLevelWidgets():
            widget.setStyleSheet(stylesheet)
            self.apply_density_to_widget(widget)
        self.waveform.update()

    def apply_density_to_widget(self, widget):

        layouts = [widget.layout()]
        layouts.extend(widget.findChildren(QLayout))
        for layout in layouts:
            if layout is None:
                continue
            if not hasattr(layout, "_aivora_base_margins"):
                layout._aivora_base_margins = layout.getContentsMargins()
                layout._aivora_base_spacing = layout.spacing()
            scale = DENSITY["scale"]
            left, top, right, bottom = layout._aivora_base_margins
            layout.setContentsMargins(
                round(left * scale),
                round(top * scale),
                round(right * scale),
                round(bottom * scale),
            )
            if layout._aivora_base_spacing >= 0:
                layout.setSpacing(round(layout._aivora_base_spacing * scale))

    def apply_feature_visibility(self):

        self.metadata_card.setVisible(
            self.feature_toggles["Édition des métadonnées"]
        )
        self.quick_selection_card.setVisible(
            self.feature_toggles["Sélection rapide"]
        )
        self.cover_card.setVisible(self.feature_toggles["Pochettes"])
        self.replace_cover_button.setEnabled(
            self.feature_toggles["Pochettes"]
            and bool(self.current_audio_path)
        )
        self.waveform_card.setVisible(
            self.feature_toggles["Forme d’onde et lecture"]
        )
        self.play_button.setEnabled(
            self.feature_toggles["Forme d’onde et lecture"]
            and bool(self.current_audio_path)
        )
        self.seek_slider.setEnabled(
            self.feature_toggles["Forme d’onde et lecture"]
            and bool(self.current_audio_path)
        )
        self.bpm_button.setVisible(self.feature_toggles["Calcul du BPM"])
        self.bpm_button.setEnabled(
            self.feature_toggles["Calcul du BPM"] and bool(self.audio_pcm)
        )
        self.bpm_badge.setVisible(self.feature_toggles["Calcul du BPM"])
        self.tools_card.setVisible(
            self.feature_toggles["Conversion MP3"]
            or self.feature_toggles["Réparation audio"]
        )
        self.convert_button.setVisible(self.feature_toggles["Conversion MP3"])
        self.repair_button.setVisible(self.feature_toggles["Réparation audio"])
        self.save_button.setVisible(
            self.feature_toggles["Édition des métadonnées"]
        )
        self.file_placement_hint.setVisible(
            self.feature_toggles["Vérification du dossier artiste"]
        )
        self.renaming_hint.setVisible(
            self.feature_toggles["Renommage automatique"]
        )
        self.anomalies_button.setVisible(
            self.feature_toggles["Surveillance automatique"]
        )
        self.type_title.setVisible(self.feature_toggles["Types multiples"])
        for button in self.type_buttons.values():
            button.setVisible(self.feature_toggles["Types multiples"])

    def set_feature_enabled(self, name, enabled, persist=True):

        self.feature_toggles[name] = enabled
        if persist:
            self.preferences.setValue(f"features/{name}", enabled)
        self.apply_feature_visibility()
        if name == "Sélection rapide" and enabled:
            self.refresh_quick_selection()
        if (
            enabled
            and name in ("Forme d’onde et lecture", "Calcul du BPM")
            and self.current_audio_path
            and not self.audio_pcm
        ):
            self.start_audio_analysis(self.current_audio_path)

    def add_field(self, parent_layout, label_text, placeholder):
        label = QLabel(label_text)
        label.setProperty("role", "eyebrow")
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        parent_layout.addWidget(label)
        parent_layout.addWidget(field)
        return field

    def toggle_type(self, track_type, checked):
        if checked:
            self.selected_types.add(track_type)
        else:
            self.selected_types.discard(track_type)

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir un fichier audio",
            "",
            "Fichiers audio (*.mp3 *.wav *.flac *.m4a *.mp4 *.ogg *.opus)",
        )
        if path:
            self.show_selected_file(path)

    def show_selected_file(self, path):
        self.loaded_from_quick_selection = False
        try:
            audio = File(path, easy=False)
            if audio is None:
                raise ValueError("Format audio non reconnu par Mutagen.")

            metadata = {
                "artist": self.read_audio_tag(
                    audio,
                    ("TPE1", "\xa9ART", "artist"),
                ),
                "title": self.read_audio_tag(
                    audio,
                    ("TIT2", "\xa9nam", "title"),
                ),
                "album": self.read_audio_tag(
                    audio,
                    ("TALB", "\xa9alb", "album"),
                ),
                "album_artist": self.read_audio_tag(
                    audio,
                    ("TPE2", "aART", "albumartist"),
                ),
                "year": self.read_audio_tag(
                    audio,
                    ("TDRC", "\xa9day", "date"),
                ),
                "genre": self.read_audio_tag(
                    audio,
                    ("TCON", "\xa9gen", "genre"),
                ),
                "bpm": self.read_audio_tag(
                    audio,
                    ("TBPM", "tmpo", "bpm"),
                ),
                "track": self.read_audio_tag(
                    audio,
                    ("TRCK", "trkn", "tracknumber"),
                ),
                "composer": self.read_audio_tag(
                    audio,
                    ("TCOM", "\xa9wrt", "composer"),
                ),
                "comment": self.read_audio_tag(
                    audio,
                    ("COMM::eng", "COMM", "\xa9cmt", "comment"),
                ),
            }
        except (
            OSError,
            ValueError,
            TypeError,
            AttributeError,
            MutagenError,
        ) as error:
            self.preview_status.setText(
                f"Impossible de lire les métadonnées : {error}"
            )
            QMessageBox.critical(
                self,
                "Lecture des métadonnées impossible",
                f"Le fichier n’a pas pu être chargé :\n\n{path}\n\n{error}",
            )
            return

        title, track_types = self.split_title_type(metadata["title"])
        metadata["title"] = title
        cover_error = None
        try:
            cover_data = self.extract_cover(audio)
        except (OSError, ValueError, TypeError, MutagenError) as error:
            cover_data = None
            cover_error = error
        self.title_input.setText(title)
        self.metadata_fields["album"].setText(metadata["album"])
        self.metadata_fields["album_artist"].setText(metadata["album_artist"])
        self.metadata_fields["year"].setText(metadata["year"])
        self.metadata_fields["genre"].setText(metadata["genre"])
        self.metadata_fields["bpm"].setText(metadata["bpm"])
        self.metadata_fields["track"].setText(metadata["track"])
        self.metadata_fields["composer"].setText(metadata["composer"])
        self.metadata_fields["comment"].setText(metadata["comment"])
        self.bpm_badge.setText(
            f"BPM · {metadata['bpm']}" if metadata["bpm"] else "BPM · —"
        )
        self.artist_input.setText(metadata["artist"])
        for track_type, button in self.type_buttons.items():
            button.setChecked(track_type in track_types)

        self.current_audio_path = path
        self.cover_data = cover_data
        self.cover_changed = False
        self.file_label.setText(path)
        self.save_button.setEnabled(True)
        self.play_button.setEnabled(
            self.feature_toggles["Forme d’onde et lecture"]
        )
        self.seek_slider.setEnabled(
            self.feature_toggles["Forme d’onde et lecture"]
        )
        self.replace_cover_button.setEnabled(
            self.feature_toggles["Pochettes"]
        )
        self.show_cover_data(cover_data)
        self.media_player.stop()
        self.media_player.setSource(QUrl.fromLocalFile(os.path.abspath(path)))
        duration = getattr(getattr(audio, "info", None), "length", 0) or 0
        self.audio_duration_ms = int(duration * 1000)
        self.seek_slider.setRange(0, self.audio_duration_ms)
        self.seek_slider.setValue(0)
        self.update_waveform_time(0)
        self.start_audio_analysis(path)
        self.save_status.setText(
            "Métadonnées lues · le fichier original reste inchangé jusqu’à "
            "l’enregistrement."
        )
        self.preview_status.setText(
            (
                f"Tags lus, mais pochette illisible : {cover_error}"
                if cover_error
                else f"Tags lus depuis {os.path.basename(path)} · aucun "
                "changement n’a été écrit dans le fichier."
            )
        )

    @staticmethod
    def read_audio_tag(audio, names):
        tags = audio.tags
        if tags is None:
            return ""

        for name in names:
            try:
                value = tags.get(name)
            except (TypeError, ValueError):
                continue
            if value is None:
                continue
            if hasattr(value, "text"):
                value = value.text
            if isinstance(value, (list, tuple)):
                if not value:
                    continue
                if name in ("TPE1", "\xa9ART", "artist"):
                    value = " & ".join(str(item) for item in value)
                elif name in ("trkn", "tracknumber") and isinstance(
                    value[0], tuple
                ):
                    track, total = value[0]
                    value = f"{track}/{total}" if total else str(track)
                else:
                    value = value[0]
            return str(value)
        if "COMM" in names:
            for frame in tags.values():
                if getattr(frame, "FrameID", None) == "COMM":
                    comment = getattr(frame, "text", ())
                    if isinstance(comment, (list, tuple)):
                        return str(comment[0]) if comment else ""
                    return str(comment)
        return ""

    @staticmethod
    def extract_cover(audio):
        tags = audio.tags
        if tags is None:
            return None

        for frame in tags.values():
            if getattr(frame, "FrameID", None) == "APIC":
                return bytes(frame.data)
        try:
            covers = tags.get("covr", ())
        except (TypeError, ValueError):
            covers = ()
        if covers:
            return bytes(covers[0])
        pictures = getattr(audio, "pictures", ())
        if pictures:
            return bytes(pictures[0].data)
        try:
            encoded_pictures = tags.get("metadata_block_picture", ())
            cover_art = tags.get("coverart", ())
        except (TypeError, ValueError):
            encoded_pictures = ()
            cover_art = ()
        if encoded_pictures:
            return bytes(Picture(base64.b64decode(encoded_pictures[0])).data)
        if cover_art:
            return base64.b64decode(cover_art[0])
        return None

    def show_cover_data(self, data):
        pixmap = QPixmap()
        if data and not pixmap.loadFromData(data):
            self.cover_preview.setPixmap(QPixmap())
            self.cover_preview.setText("♪\n\nPOCHETTE ILLISIBLE")
            self.remove_cover_button.setEnabled(False)
            self.preview_status.setText(
                "Les tags ont été lus, mais l’image de pochette est illisible."
            )
            return
        if not data:
            self.cover_preview.setPixmap(QPixmap())
            self.cover_preview.setText("♪\n\nAUCUNE POCHETTE")
            self.remove_cover_button.setEnabled(False)
            return

        self.cover_preview.setPixmap(
            pixmap.scaled(
                self.cover_preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.cover_preview.setText("")
        self.remove_cover_button.setEnabled(True)

    def start_audio_analysis(self, path):
        if (
            self.audio_process
            and self.audio_process.state() != QProcess.ProcessState.NotRunning
        ):
            self.audio_process.kill()
            self.audio_process.waitForFinished(1000)
        self.audio_pcm = array("h")
        self.bpm_button.setEnabled(False)
        self.waveform.peaks = []
        self.waveform.update()

        if not (
            self.feature_toggles["Forme d’onde et lecture"]
            or self.feature_toggles["Calcul du BPM"]
        ):
            return

        try:
            from imageio_ffmpeg import get_ffmpeg_exe

            executable = get_ffmpeg_exe()
        except (ImportError, RuntimeError) as error:
            self.preview_status.setText(
                f"Analyse audio indisponible : FFmpeg est introuvable ({error})."
            )
            return

        process = QProcess(self)
        process._aivora_pcm = bytearray()
        self.audio_process = process
        process.readyReadStandardOutput.connect(
            lambda current=process: self.collect_audio_pcm(current)
        )
        process.finished.connect(
            lambda code, status, current=process, source=path:
                self.finish_audio_analysis(current, source, code, status)
        )
        process.errorOccurred.connect(
            lambda error, current=process:
                self.handle_audio_process_error(current, error)
        )
        process.start(
            executable,
            [
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                path,
                "-vn",
                "-ac",
                "1",
                "-ar",
                "4000",
                "-f",
                "s16le",
                "pipe:1",
            ],
        )

    def collect_audio_pcm(self, process):
        process._aivora_pcm.extend(bytes(process.readAllStandardOutput()))

    def finish_audio_analysis(self, process, path, exit_code, exit_status):
        self.collect_audio_pcm(process)
        if process is not self.audio_process or path != self.current_audio_path:
            return
        pcm = process._aivora_pcm
        if exit_code != 0 or not pcm:
            self.preview_status.setText(
                "Le décodage audio a échoué ; les tags restent chargés."
            )
            return

        samples = array("h")
        samples.frombytes(pcm[: len(pcm) // 2 * 2])
        if sys.byteorder != "little":
            samples.byteswap()
        self.audio_pcm = samples
        sample_rate = 4000
        decoded_duration = round(len(samples) * 1000 / sample_rate)
        if decoded_duration:
            self.audio_duration_ms = decoded_duration
            self.seek_slider.setRange(0, decoded_duration)
        if self.feature_toggles["Forme d’onde et lecture"]:
            self.waveform.peaks = self.get_pcm_peaks(samples, 220)
            self.waveform.update()
        self.bpm_button.setEnabled(
            self.feature_toggles["Calcul du BPM"]
        )
        self.update_waveform_time(self.media_player.position())
        self.preview_status.setText(
            f"Audio décodé · forme d’onde réelle pour "
            f"{os.path.basename(path)}."
        )

    @staticmethod
    def get_pcm_peaks(samples, bucket_count):
        if not samples:
            return []
        bucket_count = min(bucket_count, len(samples))
        peaks = []
        for bucket in range(bucket_count):
            start = bucket * len(samples) // bucket_count
            end = max(start + 1, (bucket + 1) * len(samples) // bucket_count)
            peaks.append(
                max(abs(sample) for sample in samples[start:end]) / 32768
            )
        return peaks

    def handle_audio_process_error(self, process, error):
        if process is self.audio_process:
            self.preview_status.setText(
                f"Erreur de décodage audio : {process.errorString()}"
            )

    def update_media_position(self, position):
        if not self.seek_slider.isSliderDown():
            self.seek_slider.setValue(position)
        self.update_waveform_time(position)

    def update_media_duration(self, duration):
        self.audio_duration_ms = duration
        self.seek_slider.setRange(0, duration)
        self.update_waveform_time(self.media_player.position())

    def update_playback_button(self, state):
        is_playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.audio_is_playing = is_playing
        self.play_button.setText("Ⅱ  Pause" if is_playing else "▶  Lecture")

    def handle_playback_error(self, error, error_string):
        if error == QMediaPlayer.Error.NoError:
            return
        self.preview_status.setText(f"Lecture audio impossible : {error_string}")

    def split_title_type(self, title):
        match = re.fullmatch(r"(.*?)\s*\(([^()]*)\)\s*", title.strip())
        if match:
            types = tuple(
                item.strip().upper()
                for item in match.group(2).split("+")
            )
            if (
                types
                and all(item in self.TRACK_TYPES for item in types)
                and len(set(types)) == len(types)
            ):
                return match.group(1).strip(), types
        return title, ("STUDIO",)

    def refresh_quick_selection(self):
        if not self.feature_toggles["Sélection rapide"]:
            return
        if (
            hasattr(self, "quick_selection_scan")
            and self.quick_selection_scan.isRunning()
        ):
            return
        self.quick_refresh_button.setEnabled(False)
        self.quick_selection_info.setText("Recherche des fichiers audio…")
        self.quick_selection_scan = QuickSelectionScan(self)
        self.quick_selection_scan.completed.connect(
            self.finish_quick_selection_scan
        )
        self.quick_selection_scan.start()

    def finish_quick_selection_scan(self, files, errors):
        self.quick_selection_files = files
        self.quick_selection_errors = errors
        self.quick_selection_page = min(
            self.quick_selection_page,
            max(0, (len(files) - 1) // 6),
        )
        self.quick_refresh_button.setEnabled(True)
        self.show_quick_selection_page(self.quick_selection_page)

    def show_quick_selection_page(self, page):
        self.quick_selection_page = max(
            0,
            min(page, max(0, (len(self.quick_selection_files) - 1) // 6)),
        )
        while self.quick_selection_files_layout.count():
            item = self.quick_selection_files_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        page_size = 6
        start = self.quick_selection_page * page_size
        visible_files = self.quick_selection_files[start : start + page_size]
        if not visible_files:
            empty = QLabel(
                "Aucun fichier audio trouvé."
                if not self.quick_selection_errors
                else "Rail indisponible · consulte le message ci-dessus."
            )
            empty.setProperty("role", "muted")
            self.quick_selection_files_layout.addWidget(empty)
        else:
            for path in visible_files:
                button = QPushButton(os.path.basename(path))
                button.setToolTip(path)
                button.setCheckable(True)
                button.setChecked(
                    os.path.normcase(path)
                    == os.path.normcase(self.current_audio_path)
                )
                button.clicked.connect(
                    lambda checked=False, selected_path=path:
                        self.load_from_quick_selection(selected_path)
                )
                self.quick_selection_files_layout.addWidget(button, 1)
        self.quick_selection_files_layout.addStretch(1)

        total_pages = max(1, (len(self.quick_selection_files) + page_size - 1) // page_size)
        self.quick_page_label.setText(
            f"{self.quick_selection_page + 1}/{total_pages}"
        )
        self.quick_previous_button.setEnabled(self.quick_selection_page > 0)
        self.quick_next_button.setEnabled(
            self.quick_selection_page + 1 < total_pages
        )
        if self.quick_selection_errors:
            self.quick_selection_info.setText(
                f"{len(self.quick_selection_files)} fichiers · "
                f"{len(self.quick_selection_errors)} erreur(s)"
            )
            self.quick_selection_info.setToolTip(
                "\n".join(self.quick_selection_errors)
            )
        else:
            self.quick_selection_info.setText(
                f"{len(self.quick_selection_files)} fichier(s)"
            )
            self.quick_selection_info.setToolTip(config.EXCLUDED_FOLDER)

    def load_from_quick_selection(self, path):
        self.show_selected_file(path)
        if os.path.normcase(path) == os.path.normcase(self.current_audio_path):
            self.loaded_from_quick_selection = True

    def save_preview(self):
        if not self.current_audio_path:
            QMessageBox.warning(
                self,
                "Aucun fichier chargé",
                "Charge d’abord un fichier audio avant d’enregistrer.",
            )
            return

        try:
            values = self.collect_metadata()
            self.release_media_player_source()
            self.write_metadata_atomically(
                self.current_audio_path,
                values,
                cover_data=self.cover_data,
                cover_changed=self.cover_changed,
            )
        except (OSError, ValueError, MutagenError) as error:
            if self.current_audio_path:
                self.media_player.setSource(
                    QUrl.fromLocalFile(os.path.abspath(self.current_audio_path))
                )
            self.save_status.setText(f"Échec de l’enregistrement : {error}")
            QMessageBox.critical(
                self,
                "Enregistrement impossible",
                f"Les modifications n’ont pas été enregistrées :\n\n{error}",
            )
            return

        rename_message = ""
        if self.feature_toggles["Renommage automatique"]:
            try:
                rename_message = self.rename_saved_file(values)
            except OSError as error:
                self.save_status.setText(
                    "Métadonnées enregistrées, mais renommage impossible : "
                    f"{error}"
                )
                QMessageBox.warning(
                    self,
                    "Renommage impossible",
                    "Les métadonnées ont bien été enregistrées, mais le fichier "
                    f"n’a pas pu être renommé :\n\n{error}",
                )
                return

        route_message = ""
        if (
            self.feature_toggles["Déplacer après enregistrement"]
            and self.loaded_from_quick_selection
            and self.is_excluded_audio(self.current_audio_path)
        ):
            try:
                route_message = self.move_saved_file_from_quick_selection()
            except OSError as error:
                self.save_status.setText(
                    "Métadonnées enregistrées, mais déplacement impossible : "
                    f"{error}"
                )
                QMessageBox.critical(
                    self,
                    "Déplacement impossible",
                    "Les métadonnées ont été enregistrées, mais le fichier "
                    f"est resté à son emplacement source :\n\n{error}",
                )
                return

        filename = os.path.basename(self.current_audio_path)
        self.file_label.setText(self.current_audio_path)
        self.cover_changed = False
        self.media_player.setSource(
            QUrl.fromLocalFile(os.path.abspath(self.current_audio_path))
        )
        self.save_status.setText(
            f"Métadonnées enregistrées · {filename}"
            f"{rename_message}{route_message}"
        )
        self.preview_status.setText(
            f"Fichier enregistré et déplacé vers {self.current_audio_path}."
            if "déplacé vers" in route_message
            else "Les tags ont été enregistrés dans le fichier audio."
        )
        self.media_player.setSource(
            QUrl.fromLocalFile(os.path.abspath(self.current_audio_path))
        )
        self.show_artist_folder_warning(values)

    @staticmethod
    def is_excluded_audio(path):
        if not path:
            return False
        excluded = os.path.abspath(config.EXCLUDED_FOLDER)
        candidate = os.path.abspath(path)
        try:
            return (
                os.path.commonpath((candidate, excluded)).casefold()
                == excluded.casefold()
            )
        except ValueError:
            return False

    def create_media_player(self):
        self.media_player = QMediaPlayer(self)
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.playbackStateChanged.connect(
            self.update_playback_button
        )
        self.media_player.positionChanged.connect(self.update_media_position)
        self.media_player.durationChanged.connect(self.update_media_duration)
        self.media_player.errorOccurred.connect(self.handle_playback_error)

    def release_media_player_source(self):
        player = self.media_player
        player.stop()
        player.setSource(QUrl())
        delete_qobject(player)
        self.create_media_player()

    def move_saved_file_from_quick_selection(self):
        previous_destination = self.preferences.value(
            "routing/last_destination",
            config.MONITORED_FOLDER,
            type=str,
        )
        destination_folder = QFileDialog.getExistingDirectory(
            self,
            "Choisir où déplacer le fichier modifié",
            previous_destination,
            QFileDialog.Option.ShowDirsOnly,
        )
        if not destination_folder:
            return (
                " · déplacement annulé, fichier conservé dans le dossier exclu"
            )

        source = os.path.abspath(self.current_audio_path)
        destination = os.path.join(
            os.path.abspath(destination_folder),
            os.path.basename(source),
        )
        if os.path.normcase(source) == os.path.normcase(destination):
            self.loaded_from_quick_selection = False
            return " · déjà dans le dossier choisi"

        if os.path.exists(destination):
            answer = QMessageBox.question(
                self,
                "Fichier déjà présent",
                f"{os.path.basename(destination)} existe déjà dans le dossier "
                "choisi. Veux-tu le remplacer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return (
                    " · déplacement annulé, fichier conservé dans le dossier exclu"
                )

        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix=".aivora-move-",
                suffix=os.path.splitext(destination)[1],
                dir=destination_folder,
                delete=False,
            ) as temporary_file:
                temporary_path = temporary_file.name
            shutil.copy2(source, temporary_path)
            os.replace(temporary_path, destination)
            temporary_path = None
            os.remove(source)
        except OSError:
            if temporary_path and os.path.exists(temporary_path):
                os.remove(temporary_path)
            raise

        self.current_audio_path = destination
        self.loaded_from_quick_selection = False
        self.preferences.setValue("routing/last_destination", destination_folder)
        self.refresh_quick_selection()
        return f" · déplacé vers {destination_folder}"

    def collect_metadata(self):
        values = {
            key: uppercase_text(field.text())
            for key, field in self.metadata_fields.items()
        }
        values["title"] = uppercase_text(self.title_input.text())
        values["artist"] = uppercase_text(self.artist_input.text())
        if not values["artist"]:
            values["artist"] = "ARTISTE INCONNU"

        selected_types = tuple(
            track_type
            for track_type in self.TRACK_TYPES
            if self.type_buttons[track_type].isChecked()
        )
        if not selected_types:
            selected_types = ("STUDIO",)
        if not self.feature_toggles["Types multiples"]:
            selected_types = ("STUDIO",)
        values["track_types"] = selected_types
        if selected_types != ("STUDIO",):
            values["title"] += f" ({' + '.join(selected_types)})"

        if values["bpm"] and not re.fullmatch(r"[1-9][0-9]{0,2}", values["bpm"]):
            raise ValueError(
                "BPM invalide. Utilise un nombre entier entre 1 et 999."
            )
        if values["track"]:
            match = re.fullmatch(
                r"([1-9][0-9]*)(?:/([1-9][0-9]*))?",
                values["track"],
            )
            if not match:
                raise ValueError(
                    "Numéro de piste invalide. Utilise par exemple 1 ou 1/12."
                )
            if match.group(2) and int(match.group(1)) > int(match.group(2)):
                raise ValueError(
                    "Le numéro de piste ne peut pas dépasser le nombre total "
                    "de pistes."
                )
        return values

    @staticmethod
    def write_metadata_atomically(
        path,
        values,
        cover_data=None,
        cover_changed=False,
    ):
        extension = os.path.splitext(path)[1].lower()
        supported_extensions = {
            ".mp3",
            ".wav",
            ".flac",
            ".m4a",
            ".mp4",
            ".ogg",
            ".opus",
        }
        if extension not in supported_extensions:
            raise ValueError(f"Format audio non pris en charge : {extension}")

        source_audio = File(path, easy=False)
        if source_audio is None:
            raise ValueError("Le fichier audio n’est plus lisible.")
        audio_type = type(source_audio).__name__
        expected_types = {
            ".mp3": ("MP3",),
            ".wav": ("WAVE",),
            ".flac": ("FLAC",),
            ".m4a": ("MP4",),
            ".mp4": ("MP4",),
            ".ogg": ("Ogg",),
            ".opus": ("OggOpus",),
        }[extension]
        if not any(
            audio_type == expected or audio_type.startswith(expected)
            for expected in expected_types
        ):
            raise ValueError(
                f"Le contenu du fichier ne correspond pas à l’extension "
                f"{extension} (format détecté : {audio_type})."
            )

        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                prefix=".aivora-",
                suffix=extension,
                dir=os.path.dirname(os.path.abspath(path)),
                delete=False,
            ) as temporary_file:
                temporary_path = temporary_file.name

            shutil.copy2(path, temporary_path)
            if extension in (".mp3", ".wav"):
                PreviewWindow.write_id3_metadata(temporary_path, extension, values)
            elif extension in (".m4a", ".mp4"):
                PreviewWindow.write_mp4_metadata(temporary_path, values)
            else:
                PreviewWindow.write_easy_metadata(temporary_path, values)
            if cover_changed:
                PreviewWindow.write_cover(temporary_path, extension, cover_data)
            os.replace(temporary_path, path)
            temporary_path = None
        finally:
            if temporary_path and os.path.exists(temporary_path):
                os.remove(temporary_path)

    @staticmethod
    def write_id3_metadata(path, extension, values):
        if extension == ".wav":
            audio = File(path, easy=False)
            if audio is None:
                raise ValueError("Le fichier WAV ne peut pas être lu.")
            if audio.tags is None:
                audio.add_tags()
            tags = audio.tags
        else:
            try:
                tags = ID3(path)
            except ID3NoHeaderError:
                tags = ID3()

        frames = (
            ("TPE1", TPE1, values["artist"]),
            ("TIT2", TIT2, values["title"]),
            ("TALB", TALB, values["album"]),
            ("TPE2", TPE2, values["album_artist"]),
            ("TDRC", TDRC, values["year"]),
            ("TCON", TCON, values["genre"]),
            ("TBPM", TBPM, values["bpm"]),
            ("TRCK", TRCK, values["track"]),
            ("TCOM", TCOM, values["composer"]),
        )
        for frame_id, frame_type, value in frames:
            tags.delall(frame_id)
            if value:
                tags.add(frame_type(encoding=3, text=[value]))
        tags.delall("COMM")
        if values["comment"]:
            tags.add(
                COMM(
                    encoding=3,
                    lang="eng",
                    desc="Comment",
                    text=[values["comment"]],
                )
            )

        if extension == ".wav":
            audio.save()
        else:
            tags.save(path, v2_version=3)

    @staticmethod
    def write_mp4_metadata(path, values):
        audio = MP4(path)
        if audio.tags is None:
            audio.add_tags()
        mapping = {
            "artist": "\xa9ART",
            "title": "\xa9nam",
            "album": "\xa9alb",
            "album_artist": "aART",
            "year": "\xa9day",
            "genre": "\xa9gen",
            "composer": "\xa9wrt",
            "comment": "\xa9cmt",
        }
        for field, tag in mapping.items():
            if values[field]:
                audio[tag] = [values[field]]
            elif tag in audio:
                del audio[tag]

        if values["bpm"]:
            audio["tmpo"] = [int(values["bpm"])]
        elif "tmpo" in audio:
            del audio["tmpo"]

        if values["track"]:
            match = re.fullmatch(
                r"([1-9][0-9]*)(?:/([1-9][0-9]*))?",
                values["track"],
            )
            if not match:
                raise ValueError("Numéro de piste MP4 invalide.")
            track_number = int(match.group(1))
            track_total = int(match.group(2) or 0)
            audio["trkn"] = [(track_number, track_total)]
        elif "trkn" in audio:
            del audio["trkn"]
        audio.save()

    @staticmethod
    def write_easy_metadata(path, values):
        audio = File(path, easy=True)
        if audio is None:
            raise ValueError("Le format audio ne prend pas en charge les tags.")
        if audio.tags is None:
            audio.add_tags()
        mapping = {
            "artist": "artist",
            "title": "title",
            "album": "album",
            "album_artist": "albumartist",
            "year": "date",
            "genre": "genre",
            "bpm": "bpm",
            "track": "tracknumber",
            "composer": "composer",
            "comment": "comment",
        }
        for field, tag in mapping.items():
            if values[field]:
                audio[tag] = [values[field]]
            elif tag in audio:
                del audio[tag]
        audio.save()

    @staticmethod
    def write_cover(path, extension, cover_data):
        if cover_data is None:
            jpeg_data = None
        else:
            jpeg_data = image_to_jpeg(cover_data)

        if extension in (".mp3", ".wav"):
            if extension == ".wav":
                audio = File(path, easy=False)
                if audio is None:
                    raise ValueError("Le fichier WAV ne peut pas être lu.")
                if audio.tags is None:
                    audio.add_tags()
                tags = audio.tags
            else:
                try:
                    tags = ID3(path)
                except ID3NoHeaderError:
                    tags = ID3()
            tags.delall("APIC")
            if jpeg_data:
                tags.add(
                    APIC(
                        encoding=3,
                        mime="image/jpeg",
                        type=3,
                        desc="Cover",
                        data=jpeg_data,
                    )
                )
            if extension == ".wav":
                audio.save()
            else:
                tags.save(path, v2_version=3)
            return

        if extension in (".m4a", ".mp4"):
            audio = MP4(path)
            if audio.tags is None:
                audio.add_tags()
            if jpeg_data:
                audio["covr"] = [
                    MP4Cover(
                        jpeg_data,
                        imageformat=MP4Cover.FORMAT_JPEG,
                    )
                ]
            elif "covr" in audio:
                del audio["covr"]
            audio.save()
            return

        audio = File(path, easy=False)
        if audio is None:
            raise ValueError("Le fichier audio ne peut pas recevoir de pochette.")
        if extension == ".flac":
            audio.clear_pictures()
            if jpeg_data:
                picture = Picture()
                picture.type = 3
                picture.mime = "image/jpeg"
                picture.desc = "Cover"
                picture.data = jpeg_data
                audio.add_picture(picture)
            audio.save()
            return

        if audio.tags is None:
            audio.add_tags()
        for cover_tag in ("metadata_block_picture", "coverart"):
            if cover_tag in audio.tags:
                del audio.tags[cover_tag]
        if jpeg_data:
            picture = Picture()
            picture.type = 3
            picture.mime = "image/jpeg"
            picture.desc = "Cover"
            picture.data = jpeg_data
            encoded = base64.b64encode(picture.write()).decode("ascii")
            audio.tags["metadata_block_picture"] = [encoded]
        audio.save()

    def rename_saved_file(self, values):
        folder = os.path.dirname(self.current_audio_path)
        extension = os.path.splitext(self.current_audio_path)[1]
        artist = clean_filename(values["artist"] or "ARTISTE INCONNU")
        title = clean_filename(values["title"] or "SANS TITRE")
        destination = os.path.join(folder, f"{artist} - {title}{extension}")
        source = os.path.abspath(self.current_audio_path)
        destination_absolute = os.path.abspath(destination)
        if os.path.normcase(source) == os.path.normcase(destination_absolute):
            return ""

        if os.path.exists(destination):
            answer = QMessageBox.question(
                self,
                "Fichier déjà existant",
                f"Le fichier {os.path.basename(destination)} existe déjà. "
                "Veux-tu le remplacer ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return " · nom d’origine conservé"

        os.replace(self.current_audio_path, destination)
        self.current_audio_path = destination
        return " · fichier renommé"

    def show_artist_folder_warning(self, values):
        if (
            not config.ENABLE_ARTIST_FOLDER_CHECK
            or not self.feature_toggles["Vérification du dossier artiste"]
            or not values["artist"]
        ):
            return
        path = os.path.abspath(self.current_audio_path)
        excluded = os.path.abspath(config.EXCLUDED_FOLDER)
        try:
            if os.path.commonpath((path, excluded)).casefold() == excluded.casefold():
                return
        except ValueError:
            pass

        folder = os.path.basename(os.path.dirname(path)).strip()
        artist = re.split(r"\s*&\s*|\s*;\s*", values["artist"], maxsplit=1)[0]
        artist = artist.strip()
        if folder.casefold() == artist.casefold():
            return
        QMessageBox.warning(
            self,
            "Emplacement à vérifier",
            "Les métadonnées sont enregistrées, mais le dossier parent "
            f"« {folder} » ne correspond pas au premier artiste « {artist} ».",
        )

    def choose_cover(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Choisir une pochette",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if path:
            self.show_cover(path)

    def show_cover(self, path):
        if not self.current_audio_path:
            QMessageBox.warning(
                self,
                "Aucun fichier chargé",
                "Charge d’abord un fichier audio avant d’ajouter une pochette.",
            )
            return
        try:
            with open(path, "rb") as cover_file:
                cover_data = cover_file.read()
        except OSError as error:
            self.preview_status.setText(
                f"Impossible de lire la pochette : {error}"
            )
            return
        pixmap = QPixmap()
        if not pixmap.loadFromData(cover_data):
            self.preview_status.setText(
                "Impossible de prévisualiser cette image de pochette."
            )
            return

        self.cover_data = cover_data
        self.cover_changed = True
        self.cover_preview.setPixmap(
            pixmap.scaled(
                self.cover_preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.cover_preview.setText("")
        self.remove_cover_button.setEnabled(True)
        self.preview_status.setText(
            "Nouvelle pochette prévisualisée · clique sur Enregistrer pour "
            "l’intégrer au fichier."
        )

    def remove_cover(self):
        self.cover_data = None
        self.cover_changed = True
        self.cover_preview.setPixmap(QPixmap())
        self.cover_preview.setText("♪\n\nAUCUNE POCHETTE")
        self.remove_cover_button.setEnabled(False)
        self.preview_status.setText(
            "Pochette marquée pour suppression · clique sur Enregistrer pour "
            "confirmer."
        )

    def toggle_playback(self):
        if not self.current_audio_path:
            QMessageBox.warning(
                self,
                "Aucun fichier chargé",
                "Charge un fichier audio avant de lancer la lecture.",
            )
            return
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            if (
                self.audio_duration_ms
                and self.media_player.position() >= self.audio_duration_ms
            ):
                self.media_player.setPosition(0)
            self.media_player.play()

    def update_waveform_time(self, value):
        elapsed_seconds = max(0, value) // 1000
        duration_seconds = max(0, self.audio_duration_ms) // 1000
        elapsed_minutes, elapsed_seconds = divmod(elapsed_seconds, 60)
        duration_minutes, duration_seconds = divmod(duration_seconds, 60)
        self.waveform_time_label.setText(
            f"{elapsed_minutes:02}:{elapsed_seconds:02} / "
            f"{duration_minutes:02}:{duration_seconds:02}"
        )

    def show_bpm_preview(self):
        bpm = self.estimate_bpm(self.audio_pcm, sample_rate=4000)
        if bpm is None:
            QMessageBox.warning(
                self,
                "BPM indisponible",
                "Le BPM n’a pas pu être estimé pour ce fichier.",
            )
            return
        self.metadata_fields["bpm"].setText(str(bpm))
        self.bpm_badge.setText(f"BPM · {bpm}")
        self.preview_status.setText(
            f"BPM estimé : {bpm} · clique sur Enregistrer pour l’écrire dans "
            "les métadonnées."
        )

    @staticmethod
    def estimate_bpm(samples, sample_rate):
        if not samples:
            return None
        hop_size = max(1, round(sample_rate * 0.032))
        envelope = []
        for start in range(0, min(len(samples), sample_rate * 45), hop_size):
            block = samples[start : start + hop_size]
            if block:
                envelope.append(max(abs(sample) for sample in block) / 32768)
        if len(envelope) < 32:
            return None

        onsets = [
            max(0.0, envelope[index] - envelope[index - 1])
            for index in range(1, len(envelope))
        ]
        average = sum(onsets) / len(onsets)
        if max(onsets, default=0.0) <= average * 1.5:
            return None
        centered = [value - average for value in onsets]
        hops_per_second = sample_rate / hop_size
        min_lag = max(1, int(hops_per_second * 60 / 200))
        max_lag = min(
            len(centered) // 2,
            int(hops_per_second * 60 / 60),
        )
        if min_lag >= max_lag:
            return None
        best_lag = max(
            range(min_lag, max_lag + 1),
            key=lambda lag: sum(
                centered[index] * centered[index - lag]
                for index in range(lag, len(centered))
            ),
        )
        bpm = 60 * hops_per_second / best_lag
        while bpm < 80:
            bpm *= 2
        while bpm > 180:
            bpm /= 2
        return round(bpm)

    def show_tool_preview(self, tool_name):

        self.preview_status.setText(
            f"{tool_name} · commande visuelle uniquement, aucun fichier modifié."
        )

    def create_preview_dialog(self, title, size="540x420"):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumSize(480, 360)
        dialog.resize(*map(int, size.split("x")))
        dialog.setStyleSheet("")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)
        return dialog, layout

    def show_versions(self):
        dialog, layout = self.create_preview_dialog("Aivora Studio • Versions")
        title = QLabel("Guide des versions")
        title.setProperty("role", "title")
        layout.addWidget(title)
        subtitle = QLabel(
            f"Version actuelle : {VERSION} · demandes et changements "
            "consignés avant et depuis la version 1.0."
        )
        subtitle.setProperty("role", "muted")
        layout.addWidget(subtitle)

        history_scroll = QScrollArea()
        history_scroll.setWidgetResizable(True)
        history_scroll.setFrameShape(QFrame.Shape.NoFrame)
        history_content = QWidget()
        history_layout = QVBoxLayout(history_content)
        history_layout.setContentsMargins(2, 2, 8, 2)
        history_layout.setSpacing(12)

        for version, title, changes in reversed(VERSION_HISTORY):
            card = QFrame()
            card.setProperty("card", True)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_heading = QLabel(f"{version} · {title}")
            card_heading.setProperty("role", "subtitle")
            card_layout.addWidget(card_heading)
            for change in changes:
                card_detail = QLabel(f"• {change}")
                card_detail.setProperty("role", "muted")
                card_detail.setWordWrap(True)
                card_layout.addWidget(card_detail)
            history_layout.addWidget(card)

        next_release = QFrame()
        next_release.setProperty("card", True)
        next_layout = QVBoxLayout(next_release)
        next_layout.setContentsMargins(14, 12, 14, 12)
        next_heading = QLabel("1.0.008 · Outils et paramètres")
        next_heading.setProperty("role", "subtitle")
        next_detail = QLabel(
            "Prochaine étape prévue : migrer conversion, réparation et anomalies, "
            "puis terminer la validation et les paramètres."
        )
        next_detail.setProperty("role", "muted")
        next_detail.setWordWrap(True)
        next_layout.addWidget(next_heading)
        next_layout.addWidget(next_detail)
        history_layout.addWidget(next_release)
        history_layout.addStretch(1)
        history_scroll.setWidget(history_content)
        layout.addWidget(history_scroll, 1)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(dialog.reject)
        close.accepted.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

    def show_anomalies(self):
        dialog, layout = self.create_preview_dialog(
            "Aivora Studio • Anomalies",
            "620x440",
        )
        title = QLabel("Anomalies détectées")
        title.setProperty("role", "title")
        layout.addWidget(title)
        warning = QLabel(
            "Exemple visuel — les anomalies ci-dessous sont fictives."
        )
        warning.setProperty("role", "muted")
        layout.addWidget(warning)

        for name, description in (
            ("fichier_incomplet.mp3", "Fichier audio corrompu ou incomplet"),
            ("EXPORT.wav", "Un MP3 du même nom existe déjà"),
        ):
            card = QFrame()
            card.setProperty("card", True)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            file_name = QLabel(name)
            file_name.setProperty("role", "subtitle")
            issue = QLabel(description)
            issue.setProperty("role", "muted")
            issue.setWordWrap(True)
            card_layout.addWidget(file_name)
            card_layout.addWidget(issue)
            layout.addWidget(card)
        layout.addStretch(1)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(dialog.reject)
        close.accepted.connect(dialog.accept)
        layout.addWidget(close)
        dialog.exec()

    def show_settings(self):
        dialog, layout = self.create_preview_dialog(
            "Aivora Studio • Paramètres",
            "620x700",
        )
        title = QLabel("Paramètres")
        title.setProperty("role", "title")
        layout.addWidget(title)
        subtitle = QLabel(
            "Thème et densité appliqués immédiatement et mémorisés pour "
            "le prochain lancement."
        )
        subtitle.setProperty("role", "muted")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        original_settings = {
            "theme": self.theme_name,
            "density": self.density_name,
            "features": dict(self.feature_toggles),
            "interval": self.preferences.value(
                "monitoring/interval_seconds",
                30,
                type=int,
            ),
        }

        body_scroll = QScrollArea()
        body_scroll.setWidgetResizable(True)
        body_scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(2, 2, 8, 2)
        body_layout.setSpacing(12)

        theme_card = QFrame()
        theme_card.setProperty("card", True)
        theme_layout = QVBoxLayout(theme_card)
        theme_layout.setContentsMargins(14, 12, 14, 12)
        theme_heading = QLabel("Apparence")
        theme_heading.setProperty("role", "subtitle")
        theme_layout.addWidget(theme_heading)
        theme_form = QFormLayout()
        self.theme_choice = QComboBox()
        self.theme_choice.addItems(tuple(THEME_PRESETS))
        self.theme_choice.setCurrentText(self.theme_name)
        self.theme_choice.currentTextChanged.connect(
            lambda name: self.apply_appearance(
                theme_name=name,
                persist=False,
            )
        )
        density_choice = QComboBox()
        density_choice.addItems(tuple(DENSITY_PRESETS))
        density_choice.setCurrentText(self.density_name)
        density_choice.currentTextChanged.connect(
            lambda name: self.apply_appearance(
                density_name=name,
                persist=False,
            )
        )
        self.density_choice = density_choice
        theme_form.addRow("Thème", self.theme_choice)
        theme_form.addRow("Densité", density_choice)
        theme_layout.addLayout(theme_form)
        body_layout.addWidget(theme_card)

        feature_card = QFrame()
        feature_card.setProperty("card", True)
        feature_layout = QVBoxLayout(feature_card)
        feature_layout.setContentsMargins(14, 12, 14, 12)
        feature_heading = QLabel("Fonctionnalités")
        feature_heading.setProperty("role", "subtitle")
        feature_layout.addWidget(feature_heading)
        routing_help = QLabel(
            "Si le déplacement est activé, après l’enregistrement d’un son "
            "ouvert depuis le rail, tu pourras choisir son dossier de destination. "
            f"Le dossier proposé sera : {config.MONITORED_FOLDER}"
        )
        routing_help.setProperty("role", "muted")
        routing_help.setWordWrap(True)
        feature_layout.addWidget(routing_help)
        self.feature_checkboxes = {}
        for label in self.FEATURE_LABELS:
            checkbox = QCheckBox(label)
            checkbox.setChecked(self.feature_toggles[label])
            checkbox.toggled.connect(
                lambda enabled, name=label: self.set_feature_enabled(
                    name,
                    enabled,
                    persist=False,
                )
            )
            self.feature_checkboxes[label] = checkbox
            feature_layout.addWidget(checkbox)
        body_layout.addWidget(feature_card)

        scan_card = QFrame()
        scan_card.setProperty("card", True)
        scan_layout = QFormLayout(scan_card)
        scan_layout.setContentsMargins(14, 12, 14, 12)
        interval = QSpinBox()
        interval.setRange(1, 3600)
        interval.setValue(original_settings["interval"])
        interval.setSuffix(" s")
        scan_layout.addRow("Intervalle de surveillance", interval)
        body_layout.addWidget(scan_card)
        body_scroll.setWidget(body)
        layout.addWidget(body_scroll, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Enregistrer")
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(
            lambda: self.save_preview_settings(dialog, interval.value())
        )
        dialog.finished.connect(
            lambda result: self.cancel_preview_settings(original_settings)
            if result != QDialog.DialogCode.Accepted
            else None
        )
        layout.addWidget(buttons)
        self.apply_density_to_widget(dialog)
        dialog.exec()

    def save_preview_settings(self, dialog, monitor_interval):

        self.preferences.setValue("appearance/theme", self.theme_name)
        self.preferences.setValue("appearance/density", self.density_name)
        for name, enabled in self.feature_toggles.items():
            self.preferences.setValue(f"features/{name}", enabled)
        self.preferences.setValue("monitoring/interval_seconds", monitor_interval)
        self.preview_status.setText(
            "Préférences de thème, densité et fonctions enregistrées pour "
            "l’aperçu."
        )
        dialog.accept()

    def cancel_preview_settings(self, original_settings):

        self.apply_appearance(
            theme_name=original_settings["theme"],
            density_name=original_settings["density"],
            persist=False,
        )
        for name, enabled in original_settings["features"].items():
            self.set_feature_enabled(name, enabled, persist=False)

    def closeEvent(self, event):
        self.media_player.stop()
        self.media_player.setSource(QUrl())
        if (
            self.audio_process
            and self.audio_process.state() != QProcess.ProcessState.NotRunning
        ):
            self.audio_process.kill()
            self.audio_process.waitForFinished(1000)
        if (
            hasattr(self, "quick_selection_scan")
            and self.quick_selection_scan.isRunning()
        ):
            self.quick_selection_scan.requestInterruption()
            self.quick_selection_scan.wait()
        super().closeEvent(event)


def main():

    application = QApplication.instance() or QApplication([])
    window = PreviewWindow()
    window.show()
    application.exec()
