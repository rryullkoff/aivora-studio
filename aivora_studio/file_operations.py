"""File operations shared by the Tkinter and PySide6 editors."""

import os
import shutil
import tempfile

from mutagen import File


def move_file_to_folder(source, destination_folder):
    source = os.path.abspath(source)
    destination_folder = os.path.abspath(destination_folder)
    os.makedirs(destination_folder, exist_ok=True)

    if os.path.normcase(os.path.dirname(source)) == os.path.normcase(
        destination_folder
    ):
        return source

    filename = os.path.basename(source)
    base, extension = os.path.splitext(filename)
    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            prefix=".aivora-move-",
            suffix=extension,
            dir=destination_folder,
            delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name

        shutil.copy2(source, temporary_path)
        index = 1
        while True:
            candidate_name = (
                filename if index == 1 else f"{base} ({index}){extension}"
            )
            destination = os.path.join(destination_folder, candidate_name)
            try:
                os.rename(temporary_path, destination)
                temporary_path = None
                break
            except FileExistsError:
                index += 1

        os.remove(source)
        return destination
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)


def remove_audio_metadata_atomically(path):
    path = os.path.abspath(path)
    folder = os.path.dirname(path)
    extension = os.path.splitext(path)[1]
    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            prefix=".aivora-metadata-",
            suffix=extension,
            dir=folder,
            delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name

        shutil.copy2(path, temporary_path)
        audio = File(temporary_path, easy=False)
        if audio is None:
            raise ValueError("Format audio non reconnu par Mutagen.")
        audio.delete()
        os.replace(temporary_path, path)
        temporary_path = None
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)
