"""Filesystem scanning helpers."""

from __future__ import annotations

from pathlib import Path

from .config import get_search_paths
from .constants import VIDEO_EXTENSIONS


def find_exact_folders(folder_name: str) -> list[Path]:
    """Recursively search configured SEARCH_PATHS for exact folder matches."""

    search_paths = get_search_paths()
    matches: list[Path] = []

    print()
    print(f"Searching for exact folder name: {folder_name}")

    for search_root in search_paths:
        if not search_root.exists() or not search_root.is_dir():
            continue

        try:
            for path in search_root.rglob("*"):
                if not path.is_dir():
                    continue

                if path.name != folder_name:
                    continue

                resolved = path.resolve()

                if resolved not in matches:
                    matches.append(resolved)

        except OSError as error:
            print()
            print(f"[WARNING] Could not search {search_root}:")
            print(f"          {error}")

    matches.sort(key=lambda path: str(path).lower())
    return matches


def find_video_files(source_root: Path) -> list[Path]:
    """Recursively find supported video files."""

    return [
        path
        for path in source_root.rglob("*")
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    ]
