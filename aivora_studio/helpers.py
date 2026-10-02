"""Shared text, path, and image helpers."""

import io
import os
import re

from .dependencies import Image
from . import config

def uppercase_text(value):
    if not value:
        return ""
    value = str(value).strip()
    if config.ENABLE_AUTO_UPPERCASE:
        return value.upper()
    return value

def clean_filename(value):
    value = uppercase_text(value)

    # Caractères interdits sous Windows
    value = re.sub(r'[<>:"/\\|?*]', "", value)

    # Espaces multiples
    value = re.sub(r"\s+", " ", value)

    # Nettoyage final
    value = value.strip().rstrip(".")

    # Noms réservés Windows
    reserved = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    }

    if value.upper() in reserved:
        value = f"_{value}"

    return value

def get_extension(path):
    return os.path.splitext(path)[1].lower()

def image_to_jpeg(data):
    """Convertit n'importe quelle pochette compatible en JPEG."""
    image = Image.open(io.BytesIO(data))

    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()
