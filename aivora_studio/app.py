"""Main Tk application composed from focused feature modules."""

import queue

from . import config
from .dependencies import DND_FILES, TkinterDnD, tk
from .config import APP_NAME, BG, VERSION
from .audio_tools import AudioToolsMixin
from .covers import CoverMixin
from .editor import EditorMixin
from .interface import InterfaceMixin
from .monitoring import MonitoringMixin
from .quick_selection import QuickSelectionMixin
from .settings import SettingsMixin


class AivoraStudio(
    InterfaceMixin,
    AudioToolsMixin,
    CoverMixin,
    EditorMixin,
    MonitoringMixin,
    QuickSelectionMixin,
    SettingsMixin,
    TkinterDnD.Tk,
):

    def __init__(self):
        super().__init__()

        self.title(f"{APP_NAME} • V{VERSION}")
        self.geometry("1150x850")
        self.minsize(1000, 780)
        self.configure(bg=BG)

        self.current_file = None
        self.audio = None
        self.track_type_var = tk.StringVar(value="STUDIO")
        self.track_type_vars = {}
        self._active_palette = {
            name: getattr(config, name)
            for name in config.COLOR_SETTING_NAMES
        }

        self.cover_data = None
        self.cover_photo = None

        self.artist_entries = []
        self.monitor_queue = queue.Queue()
        self.monitor_running = False
        self._monitor_rescan_after_id = None
        self.last_monitor_issues = []

        self.setup_styles()
        self.build_interface()

        self.drop_zone.drop_target_register(DND_FILES)
        self.drop_zone.dnd_bind("<<Drop>>", self.handle_drop)

        self.add_artist_field()
        self.apply_feature_settings()
        self.start_folder_monitoring()
