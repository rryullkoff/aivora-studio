"""Artist-folder discovery and safe folder creation."""

import os

from .helpers import clean_filename


def list_artist_folder_names(monitored_root, excluded_root, should_cancel=None):
    monitored_root = os.path.abspath(monitored_root)
    excluded_root = os.path.abspath(excluded_root)
    names = set()
    errors = []

    if not os.path.isdir(monitored_root):
        return [], [(monitored_root, "Le dossier surveillé est introuvable.")]

    def is_excluded(path):
        try:
            return (
                os.path.commonpath((path, excluded_root)).casefold()
                == excluded_root.casefold()
            )
        except ValueError:
            return False

    def record_error(error):
        errors.append((getattr(error, "filename", monitored_root), str(error)))

    for directory, folders, _ in os.walk(
        monitored_root,
        topdown=True,
        onerror=record_error,
        followlinks=False,
    ):
        if should_cancel and should_cancel():
            break
        folders[:] = sorted(
            (
                folder
                for folder in folders
                if not is_excluded(os.path.join(directory, folder))
                and not os.path.islink(os.path.join(directory, folder))
            ),
            key=str.casefold,
        )
        if is_excluded(directory):
            continue
        names.update(folders)

    return sorted(names, key=str.casefold), errors


def get_or_create_artist_folder(monitored_root, artist_name):
    root = os.path.abspath(monitored_root)
    safe_name = clean_filename(artist_name or "ARTISTE INCONNU")
    if not safe_name:
        raise ValueError("Le nom du premier artiste ne permet pas de créer un dossier.")

    os.makedirs(root, exist_ok=True)
    root_real = os.path.realpath(root)
    with os.scandir(root) as entries:
        for entry in entries:
            if entry.name.casefold() != safe_name.casefold():
                continue
            if entry.is_symlink():
                raise OSError(
                    "Le dossier artiste correspondant est un lien symbolique."
                )
            if entry.is_dir(follow_symlinks=False):
                folder = os.path.abspath(entry.path)
                folder_real = os.path.realpath(folder)
                try:
                    if (
                        os.path.commonpath((root_real, folder_real)).casefold()
                        != root_real.casefold()
                    ):
                        raise OSError(
                            "Le dossier artiste se trouve hors du dossier surveillé."
                        )
                except ValueError as error:
                    raise OSError(
                        "Le dossier artiste se trouve sur un autre volume."
                    ) from error
                return folder
            raise NotADirectoryError(
                f"Un fichier portant le nom « {entry.name} » existe déjà."
            )

    folder = os.path.abspath(os.path.join(root, safe_name))
    try:
        common_path = os.path.commonpath(
            (root_real, os.path.realpath(folder))
        )
    except ValueError as error:
        raise ValueError(
            "Le dossier artiste doit rester sous le dossier surveillé."
        ) from error
    if common_path.casefold() != root_real.casefold():
        raise ValueError(
            "Le dossier artiste doit rester sous le dossier surveillé."
        )
    os.makedirs(folder, exist_ok=False)
    return folder
