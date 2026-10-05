import os
import io
import re
import shutil
import struct
import subprocess
import queue
import tempfile
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import colorchooser, filedialog, messagebox, simpledialog

from tkinterdnd2 import TkinterDnD, DND_FILES
from PIL import Image, ImageDraw, ImageFilter, ImageTk

from mutagen import File
from mutagen.id3 import (
    ID3,
    ID3NoHeaderError,
    TIT2,
    TPE1,
    TALB,
    TPE2,
    TDRC,
    TCON,
    TRCK,
    TCOM,
    COMM,
    APIC,
    TBPM,
)
from mutagen.mp4 import MP4, MP4Cover
from mutagen.wave import WAVE

try:
    from imageio_ffmpeg import get_ffmpeg_exe
except ImportError:
    get_ffmpeg_exe = None


# ============================================================
