"""Standalone PySide6 interface prototype for the upcoming 1.1 redesign."""

import math

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
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
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .qt_theme import THEME, build_stylesheet


class WaveformWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
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
            envelope = 0.18 + 0.82 * abs(
                math.sin(index * 0.19) * math.cos(index * 0.047)
            )
            height = max(3, envelope * (self.height() - 12))
            x = index * 7 + 2
            painter.setPen(QPen(gradient, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
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


class PreviewWindow(QMainWindow):

    TRACK_TYPES = ("LIVE", "STUDIO", "EXTRAIT", "MAP")

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aivora Studio • Aperçu PySide6")
        self.resize(1100, 820)
        self.setMinimumSize(900, 680)
        self.setStyleSheet(build_stylesheet())
        self.selected_types = set()

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
        subtitle = QLabel("Aperçu du nouveau système visuel prévu pour 1.1")
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
        version_badge = QLabel("APERÇU • PYSIDE6")
        version_badge.setAlignment(Qt.AlignmentFlag.AlignRight)
        version_badge.setProperty("role", "eyebrow")
        header_actions.addWidget(version_badge)
        header.addLayout(header_actions)
        layout.addLayout(header)

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

        columns = QHBoxLayout()
        columns.setSpacing(16)
        metadata = QFrame()
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
        cover_preview = QLabel("♪\n\nAUCUNE POCHETTE")
        cover_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_preview.setMinimumHeight(220)
        cover_preview.setStyleSheet(
            f"background: {THEME['surface_raised']}; border-radius: 12px; "
            f"color: {THEME['muted']}; font-weight: 600;"
        )
        cover_layout.addWidget(cover_preview, 1)
        cover_layout.addWidget(QPushButton("Remplacer la pochette"))
        waveform_card = QFrame()
        waveform_card.setProperty("card", True)
        waveform_layout = QVBoxLayout(waveform_card)
        waveform_layout.setContentsMargins(18, 14, 18, 14)
        waveform_header = QHBoxLayout()
        waveform_title = QLabel("Forme d’onde")
        waveform_title.setStyleSheet("font-weight: 700;")
        waveform_header.addWidget(waveform_title)
        waveform_header.addStretch(1)
        waveform_header.addWidget(QLabel("00:00 / 03:24"))
        waveform_layout.addLayout(waveform_header)
        self.waveform = WaveformWidget()
        waveform_layout.addWidget(self.waveform)
        playback = QHBoxLayout()
        playback.addWidget(QPushButton("▶  Lecture"))
        playback.addStretch(1)
        bpm_badge = QLabel("BPM · 124")
        bpm_badge.setProperty("role", "eyebrow")
        playback.addWidget(bpm_badge)
        waveform_layout.addLayout(playback)
        columns.addWidget(metadata, 3)
        columns.addWidget(cover, 2)
        layout.addLayout(columns, 1)
        layout.addWidget(waveform_card)

        footer = QHBoxLayout()
        self.save_status = QLabel(
            "Aperçu visuel · les métadonnées ne sont pas encore enregistrées."
        )
        self.save_status.setProperty("role", "muted")
        footer.addWidget(self.save_status)
        footer.addStretch(1)
        self.save_button = QPushButton("Enregistrer les modifications")
        self.save_button.setProperty("primary", True)
        self.save_button.clicked.connect(self.save_preview)
        footer.addWidget(self.save_button)
        layout.addLayout(footer)

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
        self.file_label.setText(path)
        self.save_status.setText(
            "Fichier chargé dans l’aperçu · les modifications ne sont pas "
            "écrites dans le fichier."
        )

    def save_preview(self):
        self.save_status.setText(
            "Maquette uniquement · l’enregistrement audio sera relié pendant "
            "la migration 1.1."
        )

    def create_preview_dialog(self, title, size="540x420"):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumSize(480, 360)
        dialog.resize(*map(int, size.split("x")))
        dialog.setStyleSheet(build_stylesheet())
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)
        return dialog, layout

    def show_versions(self):
        dialog, layout = self.create_preview_dialog("Aivora Studio • Versions")
        title = QLabel("Guide des versions")
        title.setStyleSheet("font-size: 19pt; font-weight: 700;")
        layout.addWidget(title)
        subtitle = QLabel("La version principale reste en 1.0.002.")
        subtitle.setProperty("role", "muted")
        layout.addWidget(subtitle)

        for heading, detail in (
            ("Petits correctifs · 1.0.xxx", "Un patch isolé à la fois, au fil des jours."),
            ("Évolutions majeures · 1.1.000", "Regrouper les nouvelles fonctions dans la livraison hebdomadaire."),
            ("Refonte visuelle", "Prototype PySide6 en préparation ; l’éditeur complet reste à migrer."),
        ):
            card = QFrame()
            card.setProperty("card", True)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_heading = QLabel(heading)
            card_heading.setStyleSheet("font-weight: 700;")
            card_detail = QLabel(detail)
            card_detail.setProperty("role", "muted")
            card_detail.setWordWrap(True)
            card_layout.addWidget(card_heading)
            card_layout.addWidget(card_detail)
            layout.addWidget(card)
        layout.addStretch(1)
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
        title.setStyleSheet("font-size: 19pt; font-weight: 700;")
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
            file_name.setStyleSheet("font-weight: 700;")
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
            "580x560",
        )
        title = QLabel("Paramètres")
        title.setStyleSheet("font-size: 19pt; font-weight: 700;")
        layout.addWidget(title)
        subtitle = QLabel(
            "Maquette des réglages — les choix ne sont pas encore enregistrés."
        )
        subtitle.setProperty("role", "muted")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        theme_card = QFrame()
        theme_card.setProperty("card", True)
        theme_layout = QVBoxLayout(theme_card)
        theme_layout.setContentsMargins(14, 12, 14, 12)
        theme_heading = QLabel("Apparence")
        theme_heading.setStyleSheet("font-weight: 700;")
        theme_layout.addWidget(theme_heading)
        theme_form = QFormLayout()
        accent_choice = QComboBox()
        accent_choice.addItems(("Violet", "Bleu", "Vert", "Orange"))
        density_choice = QComboBox()
        density_choice.addItems(("Confortable", "Compact"))
        theme_form.addRow("Couleur d’accent", accent_choice)
        theme_form.addRow("Densité", density_choice)
        theme_layout.addLayout(theme_form)
        layout.addWidget(theme_card)

        feature_card = QFrame()
        feature_card.setProperty("card", True)
        feature_layout = QVBoxLayout(feature_card)
        feature_layout.setContentsMargins(14, 12, 14, 12)
        feature_heading = QLabel("Fonctionnalités")
        feature_heading.setStyleSheet("font-weight: 700;")
        feature_layout.addWidget(feature_heading)
        for label in (
            "Forme d’onde et BPM",
            "Gestion des pochettes",
            "Surveillance automatique",
            "Sélection rapide",
        ):
            feature_layout.addWidget(QCheckBox(label))
        layout.addWidget(feature_card)

        scan_card = QFrame()
        scan_card.setProperty("card", True)
        scan_layout = QFormLayout(scan_card)
        scan_layout.setContentsMargins(14, 12, 14, 12)
        interval = QSpinBox()
        interval.setRange(1, 3600)
        interval.setValue(30)
        interval.setSuffix(" s")
        scan_layout.addRow("Intervalle de surveillance", interval)
        layout.addWidget(scan_card)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Annuler")
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Enregistrer")
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()


def main():

    application = QApplication.instance() or QApplication([])
    window = PreviewWindow()
    window.show()
    application.exec()
