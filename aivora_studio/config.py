"""Application settings and supported audio types."""

import json
import logging
import os
import re
import sys
import tempfile

APP_NAME = "Aivora Studio"

VERSION = "1.0"

BG = "#101218"

CARD = "#181b22"

CARD_2 = "#20242d"

TEXT = "#F3F4F6"

MUTED = "#9CA3AF"

ACCENT = "#7957FF"

ACCENT_HOVER = "#9278FF"

DANGER = "#E05252"

DANGER_HOVER = "#EF6969"

BORDER = "#303541"

SUCCESS = "#55C98A"

WARNING = "#E0A84E"

MONITORED_FOLDER = os.path.join(
    os.path.expanduser("~"),
    "Desktop",
    "iCloudDrive",
    "LEAK.BM31K",
)

EXCLUDED_FOLDER = os.path.join(MONITORED_FOLDER, "⛔️⛔️⛔️")

MONITOR_INTERVAL_MS = 30000

FEATURE_SETTING_NAMES = (
    "ENABLE_QUICK_SELECTION",
    "ENABLE_COVER_EDITOR",
    "ENABLE_AUDIO_ANALYSIS",
    "ENABLE_FOLDER_MONITORING",
    "ENABLE_AUDIO_CONVERSION",
    "ENABLE_AUDIO_REPAIR",
    "ENABLE_FILE_RENAMING",
    "ENABLE_ARTIST_FOLDER_CHECK",
    "ENABLE_TRACK_TYPE",
    "ENABLE_AUTO_UPPERCASE",
)

ENABLE_QUICK_SELECTION = True
ENABLE_COVER_EDITOR = True
ENABLE_AUDIO_ANALYSIS = True
ENABLE_FOLDER_MONITORING = True
ENABLE_AUDIO_CONVERSION = True
ENABLE_AUDIO_REPAIR = True
ENABLE_FILE_RENAMING = True
ENABLE_ARTIST_FOLDER_CHECK = True
ENABLE_TRACK_TYPE = True
ENABLE_AUTO_UPPERCASE = True

AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".flac", ".m4a", ".mp4", ".ogg", ".opus",
}

TRACK_TYPES = ("LIVE", "STUDIO", "EXTRAIT", "MAP")

COLOR_SETTING_NAMES = (
    "BG",
    "CARD",
    "CARD_2",
    "TEXT",
    "MUTED",
    "ACCENT",
    "ACCENT_HOVER",
    "DANGER",
    "DANGER_HOVER",
    "BORDER",
    "SUCCESS",
    "WARNING",
)

SETTINGS_PATH = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")),
    "Aivora Studio",
    "settings.json",
)


def get_settings():

    settings = {
        name: globals()[name]
        for name in COLOR_SETTING_NAMES
    }
    settings.update(
        {
            "MONITORED_FOLDER": MONITORED_FOLDER,
            "EXCLUDED_FOLDER": EXCLUDED_FOLDER,
            "MONITOR_INTERVAL_MS": MONITOR_INTERVAL_MS,
        }
    )
    settings.update(
        {
            name: globals()[name]
            for name in FEATURE_SETTING_NAMES
        }
    )
    return settings


DEFAULT_SETTINGS = get_settings()


def validate_settings(settings):

    values = {**get_settings(), **settings}

    for name in COLOR_SETTING_NAMES:
        color = values.get(name)
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            raise ValueError(f"COULEUR INVALIDE POUR {name} : {color}")
        values[name] = color.upper()

    for name in ("MONITORED_FOLDER", "EXCLUDED_FOLDER"):
        folder = values.get(name)
        if not isinstance(folder, str) or not folder.strip():
            raise ValueError(f"LE DOSSIER {name} NE PEUT PAS ÊTRE VIDE.")
        values[name] = os.path.abspath(os.path.expanduser(folder.strip()))

    monitored_folder = os.path.normcase(values["MONITORED_FOLDER"])
    excluded_folder = os.path.normcase(values["EXCLUDED_FOLDER"])
    try:
        excluded_common_path = os.path.commonpath(
            [monitored_folder, excluded_folder]
        )
    except ValueError:
        excluded_common_path = None

    if excluded_common_path == excluded_folder:
        raise ValueError(
            "LE DOSSIER EXCLU NE PEUT PAS ÊTRE LE DOSSIER SURVEILLÉ "
            "NI UN DE SES DOSSIERS PARENTS."
        )

    try:
        interval = int(values.get("MONITOR_INTERVAL_MS"))
    except (TypeError, ValueError) as error:
        raise ValueError("L'INTERVALLE DE SURVEILLANCE DOIT ÊTRE UN NOMBRE.") from error

    if not 1000 <= interval <= 3600000:
        raise ValueError(
            "L'INTERVALLE DE SURVEILLANCE DOIT ÊTRE ENTRE 1 ET 3600 SECONDES."
        )

    values["MONITOR_INTERVAL_MS"] = interval

    for name in FEATURE_SETTING_NAMES:
        if not isinstance(values.get(name), bool):
            raise ValueError(f"LE RÉGLAGE {name} DOIT ÊTRE ACTIVÉ OU DÉSACTIVÉ.")

    return values


def apply_runtime_settings(settings):

    global MONITORED_FOLDER, EXCLUDED_FOLDER, MONITOR_INTERVAL_MS
    global ENABLE_QUICK_SELECTION, ENABLE_COVER_EDITOR
    global ENABLE_AUDIO_ANALYSIS, ENABLE_FOLDER_MONITORING
    global ENABLE_AUDIO_CONVERSION, ENABLE_AUDIO_REPAIR
    global ENABLE_FILE_RENAMING, ENABLE_ARTIST_FOLDER_CHECK
    global ENABLE_TRACK_TYPE, ENABLE_AUTO_UPPERCASE

    values = validate_settings(settings)
    for name in COLOR_SETTING_NAMES:
        globals()[name] = values[name]

    MONITORED_FOLDER = values["MONITORED_FOLDER"]
    EXCLUDED_FOLDER = values["EXCLUDED_FOLDER"]
    MONITOR_INTERVAL_MS = values["MONITOR_INTERVAL_MS"]
    for name in FEATURE_SETTING_NAMES:
        globals()[name] = values[name]

    module_names = (
        "aivora_studio.app",
        "aivora_studio.interface",
        "aivora_studio.audio_tools",
        "aivora_studio.covers",
        "aivora_studio.editor",
        "aivora_studio.monitoring",
        "aivora_studio.settings",
    )
    for module_name in module_names:
        module = sys.modules.get(module_name)
        if module is None:
            continue
        for name in COLOR_SETTING_NAMES:
            if hasattr(module, name):
                setattr(module, name, values[name])

    monitoring_module = sys.modules.get("aivora_studio.monitoring")
    if monitoring_module is not None:
        monitoring_module.MONITORED_FOLDER = MONITORED_FOLDER
        monitoring_module.EXCLUDED_FOLDER = EXCLUDED_FOLDER
        monitoring_module.MONITOR_INTERVAL_MS = MONITOR_INTERVAL_MS

    return values


def save_settings(settings):

    values = validate_settings(settings)
    directory = os.path.dirname(SETTINGS_PATH)
    temporary_path = None

    try:
        os.makedirs(directory, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            prefix=".settings-",
            suffix=".json",
            delete=False,
        ) as settings_file:
            json.dump(values, settings_file, ensure_ascii=False, indent=2)
            settings_file.write("\n")
            temporary_path = settings_file.name

        os.replace(temporary_path, SETTINGS_PATH)
    except OSError:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)
        raise

    return apply_runtime_settings(values)


def load_settings():

    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as settings_file:
            stored_settings = json.load(settings_file)
        if not isinstance(stored_settings, dict):
            raise ValueError("Le fichier de paramètres doit contenir un objet JSON.")
        apply_runtime_settings({**get_settings(), **stored_settings})
    except FileNotFoundError:
        return
    except (OSError, ValueError, json.JSONDecodeError) as error:
        logging.warning("Impossible de charger les paramètres Aivora Studio : %s", error)


load_settings()
