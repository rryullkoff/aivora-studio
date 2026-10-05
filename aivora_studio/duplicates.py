"""Metadata-assisted and acoustic duplicate detection for audio files."""

import hashlib
import io
import os
import re
import subprocess
from difflib import SequenceMatcher

from imageio_ffmpeg import get_ffmpeg_exe
from mutagen import File, MutagenError
from PIL import Image


SPECTRUM_SIZE = (64, 32)
SIMILARITY_THRESHOLD = 0.985
MIN_DURATION_RATIO = 0.80


def normalize_text(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def first_tag(tags, key):
    value = tags.get(key, "") if tags else ""
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    return str(value or "").strip()


def read_audio_info(path, size, modified_ns):
    audio = File(path, easy=True)
    if audio is None:
        raise ValueError("Format audio non reconnu.")

    tags = audio.tags
    filename = os.path.splitext(os.path.basename(path))[0]
    title = first_tag(tags, "title") or filename
    artist = first_tag(tags, "artist")
    album = first_tag(tags, "album")
    duration = float(getattr(getattr(audio, "info", None), "length", 0) or 0)
    return {
        "path": path,
        "filename": filename,
        "title": title,
        "artist": artist,
        "album": album,
        "duration": duration,
        "size": size,
        "modified_ns": modified_ns,
        "cache_key": os.path.normcase(os.path.abspath(path)),
    }


def fingerprint_audio(path, duration):
    ffmpeg = get_ffmpeg_exe()
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        path,
        "-map",
        "0:a:0",
        "-lavfi",
        (
            "showspectrumpic=s=256x128:legend=0:scale=log:fscale=log:"
            "color=intensity:win_func=hann:drange=80"
        ),
        "-frames:v",
        "1",
        "-an",
        "-f",
        "image2pipe",
        "-vcodec",
        "png",
        "pipe:1",
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        check=True,
        timeout=max(60, min(600, duration * 3)),
    )
    image = Image.open(io.BytesIO(result.stdout)).convert("L")
    image = image.resize(SPECTRUM_SIZE, Image.Resampling.BILINEAR)
    values = list(image.get_flattened_data())
    mean = sum(values) / len(values)
    magnitude = sum((value - mean) ** 2 for value in values) ** 0.5
    if magnitude == 0:
        raise ValueError("Le spectre audio est vide ou silencieux.")
    return tuple((value - mean) / magnitude for value in values)


def compare_fingerprints(first, second):
    return sum(left * right for left, right in zip(first, second))


def audio_similarity_candidate(first, second):
    first_duration = first["duration"]
    second_duration = second["duration"]
    if first_duration <= 0 or second_duration <= 0:
        return False
    if min(first_duration, second_duration) / max(
        first_duration,
        second_duration,
    ) < MIN_DURATION_RATIO:
        return False

    artist_similarity = SequenceMatcher(
        None,
        normalize_text(first["artist"]),
        normalize_text(second["artist"]),
    ).ratio()
    title_similarity = SequenceMatcher(
        None,
        normalize_text(first["title"]),
        normalize_text(second["title"]),
    ).ratio()
    filename_similarity = SequenceMatcher(
        None,
        normalize_text(first["filename"]),
        normalize_text(second["filename"]),
    ).ratio()
    shared_artist = (
        bool(first["artist"])
        and bool(second["artist"])
        and artist_similarity >= 0.72
    )
    return (
        title_similarity >= 0.62
        or filename_similarity >= 0.68
        or (shared_artist and title_similarity >= 0.48)
    )


def make_review_group(kind, files, similarity, reason):
    return {
        "kind": kind,
        "files": files,
        "similarity": round(max(0.0, min(1.0, similarity)) * 100, 1),
        "reason": reason,
    }


def duplicate_group_key(group):
    return tuple(
        sorted(
            (
                file_info["cache_key"],
                file_info["size"],
                file_info["modified_ns"],
            )
            for file_info in group["files"]
        )
    )


def duplicate_group_is_current(group):
    for file_info in group["files"]:
        try:
            stat = os.stat(file_info["path"], follow_symlinks=False)
        except OSError:
            return False
        if (
            stat.st_size != file_info["size"]
            or stat.st_mtime_ns != file_info["modified_ns"]
        ):
            return False
    return True


def format_file_details(file_info):
    duration = file_info["duration"]
    if duration > 0:
        total_seconds = round(duration)
        minutes, seconds = divmod(total_seconds, 60)
        duration_text = f"{minutes}:{seconds:02}"
    else:
        duration_text = "inconnue"
    return (
        f"Titre : {file_info['title'] or 'inconnu'}\n"
        f"Artiste : {file_info['artist'] or 'inconnu'}\n"
        f"Album : {file_info['album'] or 'inconnu'}\n"
        f"Durée : {duration_text} · "
        f"Taille : {file_info['size'] / (1024 * 1024):.2f} Mo\n"
        f"Fichier : {file_info['path']}"
    )


def delete_review_file(file_info):
    path = file_info["path"]
    if os.path.islink(path):
        raise OSError("La suppression d’un lien symbolique est refusée.")
    stat = os.stat(path, follow_symlinks=False)
    if (
        stat.st_size != file_info["size"]
        or stat.st_mtime_ns != file_info["modified_ns"]
    ):
        raise OSError(
            "Le fichier a changé depuis l’analyse ; relance l’analyse avant "
            "de le supprimer."
        )
    expected_digest = file_info.get("sha256")
    if expected_digest:
        digest = hashlib.sha256()
        with open(path, "rb") as audio_file:
            while True:
                chunk = audio_file.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        current_stat = os.stat(path, follow_symlinks=False)
        if (
            current_stat.st_size != file_info["size"]
            or current_stat.st_mtime_ns != file_info["modified_ns"]
            or digest.hexdigest() != expected_digest
        ):
            raise OSError(
                "Le contenu du fichier a changé depuis l’analyse ; relance "
                "l’analyse avant de le supprimer."
            )
    os.remove(path)


def find_audio_duplicates(
    root,
    excluded_root,
    extensions,
    should_cancel=None,
    hash_cache=None,
    fingerprint_cache=None,
):
    root = os.path.abspath(root)
    excluded_root = os.path.abspath(excluded_root)
    extension_set = {extension.lower() for extension in extensions}
    hash_cache = hash_cache if hash_cache is not None else {}
    size_groups = {}
    infos = []
    errors = []
    active_cache_keys = set()

    if not os.path.isdir(root):
        return [], [(root, f"Le dossier à analyser est introuvable : {root}")]

    def is_cancelled():
        return bool(should_cancel and should_cancel())

    def is_excluded(path):
        try:
            return (
                os.path.commonpath((path, excluded_root)).casefold()
                == excluded_root.casefold()
            )
        except ValueError:
            return False

    def record_walk_error(error):
        errors.append((getattr(error, "filename", root) or root, str(error)))

    for directory, folders, filenames in os.walk(
        root,
        onerror=record_walk_error,
        followlinks=False,
    ):
        if is_cancelled():
            return [], errors
        folders[:] = sorted(
            (
                folder
                for folder in folders
                if not is_excluded(os.path.join(directory, folder))
            ),
            key=str.casefold,
        )
        if is_excluded(directory):
            continue

        for filename in filenames:
            if os.path.splitext(filename)[1].lower() not in extension_set:
                continue
            path = os.path.join(directory, filename)
            if os.path.islink(path):
                continue
            try:
                stat = os.stat(path, follow_symlinks=False)
                info = read_audio_info(path, stat.st_size, stat.st_mtime_ns)
            except (
                OSError,
                RuntimeError,
                ValueError,
                TypeError,
                AttributeError,
                MutagenError,
            ) as error:
                errors.append((path, str(error)))
                continue

            cache_key = info["cache_key"]
            active_cache_keys.add(cache_key)
            infos.append(info)
            size_groups.setdefault(stat.st_size, []).append(info)

    exact_groups = []
    exact_pairs = set()
    for candidates in size_groups.values():
        if len(candidates) < 2:
            continue

        digests = {}
        for info in candidates:
            if is_cancelled():
                return exact_groups, errors
            path = info["path"]
            cache_key = info["cache_key"]
            size = info["size"]
            modified_ns = info["modified_ns"]
            cached = hash_cache.get(cache_key) if hash_cache is not None else None
            if cached and cached[:2] == (size, modified_ns):
                digests.setdefault(cached[2], []).append(info)
                continue

            digest = hashlib.sha256()
            try:
                with open(path, "rb") as audio_file:
                    while True:
                        if is_cancelled():
                            return exact_groups, errors
                        chunk = audio_file.read(1024 * 1024)
                        if not chunk:
                            break
                        digest.update(chunk)
                current_stat = os.stat(path, follow_symlinks=False)
                if (
                    current_stat.st_size != size
                    or current_stat.st_mtime_ns != modified_ns
                ):
                    raise OSError("Le fichier a changé pendant l’analyse.")
                digest_value = digest.digest()
                if hash_cache is not None:
                    hash_cache[cache_key] = (size, modified_ns, digest_value)
                digests.setdefault(digest_value, []).append(info)
            except OSError as error:
                errors.append((path, str(error)))

        for digest_value, group in digests.items():
            if len(group) < 2:
                continue
            group.sort(key=lambda info: info["path"].casefold())
            for info in group:
                info["sha256"] = digest_value.hex()
            exact_groups.append(
                make_review_group(
                    "exact",
                    group,
                    1.0,
                    "Contenu binaire identique (SHA-256).",
                )
            )
            for index, first in enumerate(group):
                for second in group[index + 1 :]:
                    exact_pairs.add(
                        frozenset((first["cache_key"], second["cache_key"]))
                    )

    fingerprint_cache = fingerprint_cache if fingerprint_cache is not None else {}
    fingerprints = {}

    def get_fingerprint(info):
        if is_cancelled():
            return None
        key = info["cache_key"]
        cached = fingerprint_cache.get(key)
        stat_key = (info["size"], info["modified_ns"])
        if cached and cached[:2] == stat_key:
            return cached[2]
        try:
            value = fingerprint_audio(info["path"], info["duration"])
            current_stat = os.stat(info["path"], follow_symlinks=False)
            if (
                current_stat.st_size != info["size"]
                or current_stat.st_mtime_ns != info["modified_ns"]
            ):
                raise OSError("Le fichier a changé pendant l’analyse.")
            fingerprint_cache[key] = (*stat_key, value)
            return value
        except (
            OSError,
            RuntimeError,
            ValueError,
            TypeError,
            subprocess.SubprocessError,
            Image.DecompressionBombError,
        ) as error:
            errors.append((info["path"], f"Empreinte sonore impossible : {error}"))
            return None

    similar_groups = []
    sorted_infos = sorted(
        infos,
        key=lambda info: (info["duration"], info["path"].casefold()),
    )
    for index, first in enumerate(sorted_infos):
        if is_cancelled():
            break
        for second in sorted_infos[index + 1 :]:
            if is_cancelled():
                break
            if first["duration"] <= 0 or second["duration"] <= 0:
                continue
            if first["duration"] / second["duration"] < MIN_DURATION_RATIO:
                break
            pair = frozenset((first["cache_key"], second["cache_key"]))
            if pair in exact_pairs or not audio_similarity_candidate(first, second):
                continue

            first_fingerprint = fingerprints.get(first["cache_key"])
            if first_fingerprint is None:
                first_fingerprint = get_fingerprint(first)
                fingerprints[first["cache_key"]] = first_fingerprint
            second_fingerprint = fingerprints.get(second["cache_key"])
            if second_fingerprint is None:
                second_fingerprint = get_fingerprint(second)
                fingerprints[second["cache_key"]] = second_fingerprint
            if first_fingerprint is None or second_fingerprint is None:
                continue

            similarity = compare_fingerprints(
                first_fingerprint,
                second_fingerprint,
            )
            if similarity >= SIMILARITY_THRESHOLD:
                try:
                    for info in (first, second):
                        if "sha256" in info:
                            continue
                        digest = hashlib.sha256()
                        with open(info["path"], "rb") as audio_file:
                            while True:
                                chunk = audio_file.read(1024 * 1024)
                                if not chunk:
                                    break
                                digest.update(chunk)
                        current_stat = os.stat(
                            info["path"],
                            follow_symlinks=False,
                        )
                        if (
                            current_stat.st_size != info["size"]
                            or current_stat.st_mtime_ns
                            != info["modified_ns"]
                        ):
                            raise OSError(
                                "Le fichier a changé pendant l’analyse."
                            )
                        info["sha256"] = digest.hexdigest()
                except OSError as error:
                    errors.append((info["path"], str(error)))
                    continue
                similar_groups.append(
                    make_review_group(
                        "similar",
                        [first, second],
                        similarity,
                        "Spectres audio très proches et noms/tags similaires.",
                    )
                )

    all_groups = exact_groups + similar_groups
    all_groups.sort(
        key=lambda group: (
            group["files"][0]["path"].casefold(),
            group["kind"],
        )
    )

    if not is_cancelled():
        for cache in (hash_cache, fingerprint_cache):
            if cache is not None:
                for cache_key in set(cache).difference(active_cache_keys):
                    del cache[cache_key]

    return all_groups, errors
