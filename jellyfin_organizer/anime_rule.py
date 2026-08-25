"""Current built-in anime organizing behavior.

This module is transitional. Later phases can replace it with user-selected
YAML/template-backed rules.
"""

from __future__ import annotations

import re
from pathlib import Path


def detect_episode(filename: str) -> tuple[int | None, int | None, str | None]:
    """Detect season and episode information.

    Returns `(season, episode, special_type)`.
    """

    stem = Path(filename).stem

    special_match = re.search(
        r"\b(OVA|Movie|Special)\b",
        stem,
        flags=re.IGNORECASE,
    )

    if special_match:
        return 0, None, special_match.group(1)

    match = re.search(r"[Ss](\d{1,2})[Ee](\d{1,3})", stem)

    if match:
        return int(match.group(1)), int(match.group(2)), None

    match = re.search(
        r"(?:episode|ep|e)"
        r"\s*[-_. ]?\s*"
        r"(\d{1,3})"
        r"\b",
        stem,
        flags=re.IGNORECASE,
    )

    if match:
        return None, int(match.group(1)), None

    match = re.search(r"(?:^|[\s._-])(\d{1,3})(?=$|[\s._-])", stem)

    if match:
        return None, int(match.group(1)), None

    return None, None, None


def get_season_folder_name(season: int) -> str:
    """Return the Jellyfin season folder name."""

    if season == 0:
        return "Season"

    return f"Season {season:02d}"


def get_existing_episode_numbers(season_dir: Path) -> set[int]:
    """Return existing episode numbers in a season folder."""

    if not season_dir.exists():
        return set()

    numbers: set[int] = set()

    for file in season_dir.iterdir():
        if not file.is_file():
            continue

        match = re.search(r"[Ss]\d{2}[Ee](\d{2,3})", file.stem)

        if match:
            numbers.add(int(match.group(1)))

    return numbers
