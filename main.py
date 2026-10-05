#!/usr/bin/env python3

"""Organize downloaded Anime/Movie/TV Shows episodes for Jellyfin."""

from __future__ import annotations

import argparse
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

import requests


# ============================================================
# CONFIGURATION
# ============================================================

VIDEO_EXTENSIONS = {
    ".mkv",
    ".mp4",
    ".avi",
    ".mov",
    ".wmv",
    ".m4v",
    ".ts",
    ".webm",
    ".flv",
}

DEFAULT_FINISHED_FOLDER_PATH = "~/videos"

# Directories where the script searches for the folder name
# entered by the user. Multiple paths can be separated by commas.
#
# Example:
# SEARCH_PATHS=~/shared,~/jellyfin
#
# The script recursively searches these locations for folders
# whose name exactly matches the folder name entered by the user.
DEFAULT_SEARCH_PATHS = "~/shared,~/jellyfin"

ENV_FILENAME = ".env"

ENV_FINISHED_FOLDER_KEY = "FINISHED_FOLDER_PATH"
ENV_SEARCH_PATHS_KEY = "SEARCH_PATHS"
ENV_MAL_CLIENT_ID_KEY = "MAL_CLIENT_ID"
ENV_TMDB_API_KEY_KEY = "TMDB_API_KEY"

MAL_API_URL = "https://api.myanimelist.net/v2/anime"
TMDB_API_URL = "https://api.themoviedb.org/3"
REQUEST_TIMEOUT = 15
API_RETRY_DELAYS = (5, 30, 60)

# MAL media types counted as a regular season.
SEASON_MEDIA_TYPES = {"tv", "ona"}

RESOLUTION_PATTERN = re.compile(
    r"\b(?:"
    r"240p|360p|480p|576p|720p|900p|1080p|"
    r"1440p|2160p|4320p|4k|8k"
    r")\b",
    re.IGNORECASE,
)

METADATA_PATTERN = re.compile(
    r"\b(?:"
    r"WEB[-_. ]?DL|"
    r"WEB[-_. ]?RIP|"
    r"WEB|"
    r"Blu[-_. ]?Ray|"
    r"BluRay|"
    r"BDRip|"
    r"BRRip|"
    r"HDTV|"
    r"DVDRip|"
    r"REMASTERED|"
    r"REMUX|"
    r"x264|"
    r"x265|"
    r"H\.?264|"
    r"H\.?265|"
    r"HEVC|"
    r"AV1|"
    r"10bit|"
    r"8bit|"
    r"AAC|"
    r"FLAC|"
    r"DDP|"
    r"DD5\.1|"
    r"Atmos|"
    r"END|"
    r"FINAL|"
    r"FINALE"
    r")\b",
    re.IGNORECASE,
)

# Characters that are invalid on common filesystems.
INVALID_FILENAME_CHARS_PATTERN = re.compile(
    r'[<>:"/\\|?*]'
)


# ============================================================
# ENVIRONMENT CONFIGURATION
# ============================================================

def load_env_file() -> dict[str, str]:
    """
    Load simple KEY=VALUE pairs from the .env file located
    next to this script.

    Example:

        FINISHED_FOLDER_PATH=~/storage/videos/Anime
        SEARCH_PATHS=~/shared,~/jellyfin
    """

    env_path = (
        Path(__file__).resolve().parent
        / ENV_FILENAME
    )

    if not env_path.exists():
        return {}

    values: dict[str, str] = {}

    try:
        for line in env_path.read_text(
            encoding="utf-8"
        ).splitlines():

            line = line.strip()

            # Ignore empty lines and comments.
            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)

            key = key.strip()
            value = value.strip()

            # Remove optional surrounding quotes.
            if (
                len(value) >= 2
                and value[0] == value[-1]
                and value[0] in {"'", '"'}
            ):
                value = value[1:-1]

            values[key] = value

    except OSError as error:
        print()
        print(
            f"[WARNING] Could not read .env file: {error}"
        )

    return values


def get_finished_folder_path() -> Path:
    """
    Return the configured finished-folder destination.

    Priority:

        1. FINISHED_FOLDER_PATH from .env
        2. ~/videos
    """

    env = load_env_file()

    configured_path = env.get(
        ENV_FINISHED_FOLDER_KEY,
        DEFAULT_FINISHED_FOLDER_PATH,
    ).strip()

    if not configured_path:
        configured_path = DEFAULT_FINISHED_FOLDER_PATH

    return (
        Path(configured_path)
        .expanduser()
        .resolve()
    )


def get_search_paths() -> list[Path]:
    """
    Return directories used when searching for the source folder.

    SEARCH_PATHS is a comma-separated list in .env.

    Example:

        SEARCH_PATHS=~/shared,~/jellyfin
    """

    env = load_env_file()

    configured_paths = env.get(
        ENV_SEARCH_PATHS_KEY,
        DEFAULT_SEARCH_PATHS,
    ).strip()

    if not configured_paths:
        configured_paths = DEFAULT_SEARCH_PATHS

    paths: list[Path] = []

    for raw_path in configured_paths.split(","):
        raw_path = raw_path.strip()

        if not raw_path:
            continue

        path = (
            Path(raw_path)
            .expanduser()
            .resolve()
        )

        if path not in paths:
            paths.append(path)

    return paths


# ============================================================
# MYANIMELIST / TMDB
# ============================================================

@dataclass
class SeriesInfo:
    """Result of walking the MyAnimeList prequel chain."""

    # The MAL entry entered by the user.
    target: dict

    # First season of the series (used for the TMDB search).
    first: dict

    # Season number of target. 0 = not a regular season.
    season: int

    # True for a standalone movie (no TV/ONA entry in its chain).
    is_movie: bool = False


def get_api_key(env_key: str) -> str:
    """Return a required API key from .env, or exit."""

    value = load_env_file().get(env_key, "").strip()

    if not value:
        raise SystemExit(
            f"[ERROR] {env_key} is not set in {ENV_FILENAME}."
        )

    return value


def api_get(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
) -> dict:
    """GET a JSON endpoint, retrying request failures before exiting."""

    for attempt in range(len(API_RETRY_DELAYS) + 1):
        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            return response.json()

        except requests.RequestException as error:
            if attempt < len(API_RETRY_DELAYS):
                delay = API_RETRY_DELAYS[attempt]
                print(
                    f"[WARNING] {url} API request failed. "
                    f"Retrying in {delay} seconds "
                    f"({attempt + 1}/{len(API_RETRY_DELAYS)})."
                )
                time.sleep(delay)
                continue

        status = getattr(
            error.response,
            "status_code",
            None,
        )

        detail = (
            f"HTTP {status}"
            if status
            else type(error).__name__
        )

        # Show only the underlying cause (DNS failure, timeout,
        # TLS error...). The full message contains the request
        # URL and can include the API key, so it is redacted.
        reason = ""

        if not status:

            message = re.sub(
                r"api_key=[^&\s'\")]+",
                "api_key=***",
                str(error),
            )

            cause = re.search(
                r"Caused by (.*)\)\s*$",
                message,
            )

            if cause:
                reason = f"\n        {cause.group(1)[:200]}"

        raise SystemExit(
            f"[ERROR] Request failed ({detail}): {url}{reason}"
        ) from None


def fetch_mal_anime(
    mal_id: int,
    client_id: str,
) -> dict:
    """Fetch one anime entry from MyAnimeList."""

    return api_get(
        f"{MAL_API_URL}/{mal_id}",
        params={
            "fields": (
                "alternative_titles,related_anime,"
                "media_type,start_date"
            ),
        },
        headers={"X-MAL-CLIENT-ID": client_id},
    )


def resolve_mal_series(
    mal_id: int,
    client_id: str,
) -> SeriesInfo:
    """
    Follow "prequel" relations back to the first season.

    Season number = number of tv/ona entries in the chain
    (the entered entry included). Movies/OVAs/specials in the
    chain are walked through but not counted.

    If the entered entry itself is not tv/ona, season is 0.
    """

    chain: list[dict] = []
    visited: set[int] = set()

    current = fetch_mal_anime(mal_id, client_id)

    while current["id"] not in visited:

        visited.add(current["id"])
        chain.append(current)

        prequels = [
            related["node"]["id"]
            for related in current.get("related_anime", [])
            if related["relation_type"] == "prequel"
        ]

        if not prequels:
            break

        current = fetch_mal_anime(
            prequels[0],
            client_id,
        )

    target = chain[0]

    seasons = [
        entry
        for entry in chain
        if entry.get("media_type") in SEASON_MEDIA_TYPES
    ]

    if target.get("media_type") in SEASON_MEDIA_TYPES:
        season = len(seasons)
    else:
        season = 0

    first = seasons[-1] if seasons else chain[-1]

    return SeriesInfo(
        target=target,
        first=first,
        season=season,
        is_movie=(
            target.get("media_type") == "movie"
            and not seasons
        ),
    )


def pick_tmdb_result(
    results: list[dict],
    year: str,
) -> dict:
    """
    Pick from the top 5 results.

    Prefer the first result whose first_air_date year matches
    the MAL start year, otherwise the top result.
    """

    top = results[:5]

    if year:
        for result in top:
            date = (
                result.get("first_air_date")
                or result.get("release_date")
                or ""
            )

            if date[:4] == year:
                return result

    return top[0]


def search_tmdb(
    kind: str,
    entry: dict,
    api_key: str,
) -> dict:
    """Search TMDB ("tv" or "movie") using a MAL entry's titles."""

    titles = entry.get("alternative_titles", {})
    year = (entry.get("start_date") or "")[:4]

    queries: list[str] = []

    for query in (
        titles.get("en"),
        entry.get("title"),
        titles.get("ja"),
    ):
        if query and query not in queries:
            queries.append(query)

    for query in queries:

        data = api_get(
            f"{TMDB_API_URL}/search/{kind}",
            params={
                "query": query,
                "api_key": api_key,
            },
        )

        results = data.get("results", [])

        if results:
            return pick_tmdb_result(results, year)

    raise SystemExit(
        "[ERROR] No TMDB match found. "
        "Retry with --tmdb-id <id>."
    )


def fetch_tmdb(
    kind: str,
    tmdb_id: int,
    api_key: str,
) -> dict:
    """Fetch a TMDB show ("tv") or movie ("movie") by ID."""

    return api_get(
        f"{TMDB_API_URL}/{kind}/{tmdb_id}",
        params={"api_key": api_key},
    )


def tmdb_name(tmdb: dict) -> str:
    """TV shows use "name", movies use "title"."""

    return tmdb.get("name") or tmdb.get("title") or ""


def tmdb_date(tmdb: dict) -> str:
    """TV shows use "first_air_date", movies use "release_date"."""

    return (
        tmdb.get("first_air_date")
        or tmdb.get("release_date")
        or ""
    )


def fetch_tmdb_alternative_titles(
    tmdb_id: int,
    api_key: str,
    kind: str = "tv",
) -> list[dict]:
    """
    Fetch TMDB alternative titles.

    Each item looks like:

        {"iso_3166_1": "US", "title": "Hell Mode", "type": "Short Title"}
    """

    data = api_get(
        f"{TMDB_API_URL}/{kind}/{tmdb_id}/alternative_titles",
        params={"api_key": api_key},
    )

    # TV shows return "results", movies return "titles".
    return data.get("results") or data.get("titles") or []


def pick_title(
    tmdb_name: str,
    alternative_titles: list[dict],
) -> tuple[str, str]:
    """
    Choose the title used for the folder and filenames.

    Priority:

        1. United States "Short Title"
        2. Japan "romaji" title
        3. Other Japanese title explicitly marked as romaji
        4. The regular TMDB name

    Returns (title, source label).
    """

    us_short_titles = [
        item
        for item in alternative_titles
        if (
            item.get("iso_3166_1") == "US"
            and (item.get("type") or "").strip().lower() == "short title"
            and item.get("title")
        )
    ]

    if us_short_titles:
        return us_short_titles[0]["title"], "US Short Title"

    japanese_romaji = [
        item
        for item in alternative_titles
        if (
            item.get("iso_3166_1") == "JP"
            and "romaji" in (item.get("type") or "").strip().lower()
            and item.get("title")
        )
    ]

    # Prefer the general "romaji" type over other romaji-labeled titles,
    # then prefer an unaccented spelling when TMDB provides one.
    japanese_romaji.sort(
        key=lambda item: (
            (item.get("type") or "").strip().lower() != "romaji",
            bool(re.search(r"[āēīōūĀĒĪŌŪ]", item["title"])),
        )
    )

    if japanese_romaji:
        title = japanese_romaji[0]["title"]
        # Render Japanese long vowels in plain ASCII Hepburn spelling.
        title = title.translate(str.maketrans({
            "ā": "aa", "ē": "ee", "ī": "ii", "ō": "ou", "ū": "uu",
            "Ā": "Aa", "Ē": "Ee", "Ī": "Ii", "Ō": "Ou", "Ū": "Uu",
        }))
        return title, "JP romaji"

    return tmdb_name, "TMDB name"


def sanitize_title(title: str) -> str:
    """
    Make a TMDB title filesystem-safe.

    "Kaguya-sama: Love Is War" -> "Kaguya-sama - Love Is War"
    """

    title = re.sub(r"\s*:\s*", " - ", title)
    title = re.sub(r'[<>"/\\|?*]', "", title)
    title = re.sub(r"\s+", " ", title)

    return title.strip(" .")


def build_names(
    tmdb: dict,
    title: str,
) -> tuple[str, str]:
    """
    Return (folder_name, file_title).

    folder_name: Name [tmdbid-123]
    file_title : Name

    title is the chosen display title (see pick_title).
    The ID comes from the TMDB show. The year is used for matching only.
    """

    name = sanitize_title(title)
    file_title = name

    return (
        f"{file_title} [tmdbid-{tmdb['id']}]",
        file_title,
    )


def parse_mal_id(text: str) -> int | None:
    """Accept a MyAnimeList URL or a plain numeric ID."""

    match = (
        re.search(r"myanimelist\.net/anime/(\d+)", text)
        or re.fullmatch(r"(\d+)", text.strip())
    )

    return int(match.group(1)) if match else None


def ask_for_mal_id() -> int:
    """Ask for a MyAnimeList URL or ID."""

    while True:

        answer = input(
            "MyAnimeList URL or ID: "
        ).strip()

        mal_id = parse_mal_id(answer)

        if mal_id:
            return mal_id

        print(
            "Invalid input. Examples: 62542 or "
            "https://myanimelist.net/anime/62542/Grand_Blue_Season_3"
        )


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_spaces(text: str) -> str:
    """Normalize whitespace and separators."""

    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*-\s*", " - ", text)

    return text.strip(" -. _").strip()


def clean_filename(stem: str) -> str:
    """
    Remove release metadata from a filename.

    Example:

        [Example] Sousou no Frieren - 25 END [1080p]

    becomes:

        Sousou no Frieren - 25
    """

    # --------------------------------------------------------
    # Remove everything inside square brackets.
    # --------------------------------------------------------

    stem = re.sub(
        r"\[[^\]]*\]",
        " ",
        stem,
    )

    # --------------------------------------------------------
    # Remove resolutions.
    # --------------------------------------------------------

    stem = RESOLUTION_PATTERN.sub(
        " ",
        stem,
    )

    # --------------------------------------------------------
    # Remove release metadata.
    # --------------------------------------------------------

    stem = METADATA_PATTERN.sub(
        " ",
        stem,
    )

    # --------------------------------------------------------
    # Remove empty parentheses.
    # --------------------------------------------------------

    stem = re.sub(
        r"\(\s*\)",
        " ",
        stem,
    )

    return clean_spaces(stem)


def clean_display_title(title: str) -> str:
    """
    Clean a user-provided title for use in a filename.

    Filesystem-invalid characters such as ':' are replaced
    with a safe separator.
    """

    title = INVALID_FILENAME_CHARS_PATTERN.sub(
        " - ",
        title,
    )

    title = re.sub(
        r"\s*-\s*-\s*",
        " - ",
        title,
    )

    return clean_spaces(title)


# ============================================================
# FOLDER SEARCH
# ============================================================

def find_exact_folders(
    folder_name: str,
) -> list[Path]:
    """
    Recursively search configured SEARCH_PATHS for directories
    whose name exactly matches folder_name.

    Matching is case-sensitive according to the filesystem.
    """

    search_paths = get_search_paths()

    matches: list[Path] = []

    print()
    print(
        f"Searching for exact folder name: {folder_name}"
    )

    for search_root in search_paths:

        if not search_root.exists():
            continue

        if not search_root.is_dir():
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
            print(
                f"[WARNING] Could not search {search_root}:"
            )
            print(
                f"          {error}"
            )

    matches.sort(
        key=lambda path: str(path).lower()
    )

    return matches


def ask_for_source_folder() -> Path:
    """
    Ask for a folder name and automatically search for it.

    If multiple exact matches are found, ask the user to
    select one.
    """

    while True:

        folder_name = input(
            "Folder name or full path: "
        ).strip().strip("'\"")

        if not folder_name:
            print(
                "Folder name cannot be empty."
            )
            continue

        # ----------------------------------------------------
        # Full/relative path: use it directly.
        # ----------------------------------------------------

        if "/" in folder_name or folder_name.startswith(("~", ".")):

            direct = Path(folder_name).expanduser()

            if direct.is_dir():
                resolved = direct.resolve()

                print()
                print(
                    f"Using: {resolved}"
                )

                return resolved

            print()
            print(
                "[ERROR] Folder does not exist:"
            )
            print(
                f"        {direct}"
            )
            continue

        matches = find_exact_folders(
            folder_name
        )

        if not matches:
            print()
            print(
                "[ERROR] No exact folder match found."
            )

            print()
            retry = input(
                "Try another folder name? [Y/n]: "
            ).strip().lower()

            if retry in {"", "y", "yes"}:
                continue

            raise SystemExit(1)

        # ----------------------------------------------------
        # Exactly one result.
        # ----------------------------------------------------

        if len(matches) == 1:
            print()
            print(
                f"Found: {matches[0]}"
            )

            return matches[0]

        # ----------------------------------------------------
        # Multiple results.
        # ----------------------------------------------------

        print()
        print(
            f"Found {len(matches)} matching folders:"
        )
        print()

        for index, path in enumerate(
            matches,
            start=1,
        ):
            print(
                f"  {index}. {path}"
            )

        print()

        while True:

            answer = input(
                "Select folder number: "
            ).strip()

            try:
                selected = int(answer)
            except ValueError:
                print(
                    "Please enter a valid number."
                )
                continue

            if 1 <= selected <= len(matches):
                return matches[selected - 1]

            print(
                f"Please enter a number between 1 and {len(matches)}."
            )


# ============================================================
# SEASON INPUT
# ============================================================

def ask_for_season() -> int | None:
    """
    Ask the user for an optional season number.

    Accepted formats:

        0
        00
        2
        02
        Season 0
        Season 2
        Season 02
        S0
        S02

    Empty input preserves automatic detection.

    Season 0 uses the folder name "Season" for specials/OVAs,
    while filenames still use S00E##.
    """

    while True:

        answer = input(
            "Season number [Enter = auto-detect]: "
        ).strip()

        if not answer:
            return None

        match = re.fullmatch(
            r"(?:season\s*|s\s*)?(\d{1,2})",
            answer,
            flags=re.IGNORECASE,
        )

        if match:
            return int(match.group(1))

        print(
            "Invalid season. Examples: 0, 2, Season 2, or S02."
        )


def ask_for_season_title() -> str:
    """
    Ask for an optional season/arc title.

    Examples:

        Mugen Ressha-hen
        Yuukaku-hen
        Hajirai Ippai

    Empty input means no subtitle will be added
    to the filename.
    """

    answer = input(
        "Season/arc title [Enter = none]: "
    ).strip()

    if not answer:
        return ""

    return clean_display_title(answer)


# ============================================================
# EPISODE DETECTION
# ============================================================

def detect_episode(
    filename: str,
) -> tuple[
    int | None,
    int | None,
    str | None,
]:
    """
    Detect season and episode information.

    Returns:

        (season, episode, special_type)
    """

    stem = Path(filename).stem

    # ========================================================
    # SPECIAL / OVA / MOVIE
    # ========================================================

    special_match = re.search(
        r"\b(OVA|Movie|Special)\b",
        stem,
        flags=re.IGNORECASE,
    )

    # An explicit S01E01 tag wins over keywords in the title.
    if special_match and not re.search(
        r"[Ss]\d{1,2}[Ee]\d{1,3}",
        stem,
    ):
        return (
            0,
            None,
            special_match.group(1),
        )

    # ========================================================
    # STANDARD S01E01
    # ========================================================

    match = re.search(
        r"[Ss](\d{1,2})[Ee](\d{1,3})",
        stem,
    )

    if match:
        return (
            int(match.group(1)),
            int(match.group(2)),
            None,
        )

    # ========================================================
    # E01 / EP01 / Episode 01
    # ========================================================

    match = re.search(
        r"(?:episode|ep|e)"
        r"\s*[-_. ]?\s*"
        r"(\d{1,3})"
        r"\b",
        stem,
        flags=re.IGNORECASE,
    )

    if match:
        return (
            None,
            int(match.group(1)),
            None,
        )

    # ========================================================
    # NUMBER AFTER A SEPARATOR
    #
    # Handles:
    #
    # Anime - 01
    # Anime - 25 END
    # Anime 25 something
    # Anime.25
    # ========================================================

    match = re.search(
        r"(?:^|[\s._-])(\d{1,3})(?=$|[\s._-])",
        stem,
    )

    if match:
        return (
            None,
            int(match.group(1)),
            None,
        )

    # ========================================================
    # NOTHING FOUND
    # ========================================================

    return None, None, None


# ============================================================
# FIND VIDEO FILES
# ============================================================

def find_video_files(
    source_root: Path,
) -> list[Path]:
    """Recursively find supported video files."""

    return [
        path
        for path in source_root.rglob("*")
        if (
            path.is_file()
            and path.suffix.lower()
            in VIDEO_EXTENSIONS
        )
    ]


# ============================================================
# SEASON FOLDER NAMES
# ============================================================

def get_season_folder_name(
    season: int,
) -> str:
    """Return the Jellyfin season folder name."""

    if season == 0:
        return "Season"

    return f"Season {season:02d}"


# ============================================================
# EXISTING EPISODE NUMBERS
# ============================================================

def get_existing_episode_numbers(
    season_dir: Path,
) -> set[int]:
    """Return existing episode numbers in a season folder."""

    if not season_dir.exists():
        return set()

    numbers: set[int] = set()

    for file in season_dir.iterdir():

        if not file.is_file():
            continue

        match = re.search(
            r"[Ss]\d{2}[Ee](\d{2,3})",
            file.stem,
        )

        if match:
            numbers.add(
                int(match.group(1))
            )

    return numbers


# ============================================================
# PROCESS ONE FILE
# ============================================================

def process_file(
    file_path: Path,
    destination_root: Path,
    anime_title: str,
    execute: bool,
    used_special_numbers: set[int],
    season_override: int | None,
    season_title: str,
) -> tuple[bool, bool]:
    """
    Process one video file.

    Returns:

        (success, safe_to_delete_source)

    success:
        True when the file was moved/renamed successfully,
        or when it already has the correct destination.

    safe_to_delete_source:
        True when this particular source file does not need
        to remain because of a destination conflict.
    """

    original_stem = file_path.stem

    # --------------------------------------------------------
    # Clean filename.
    # --------------------------------------------------------

    cleaned_stem = clean_filename(
        original_stem
    )

    # --------------------------------------------------------
    # Detect episode.
    # --------------------------------------------------------

    season, episode, special_type = detect_episode(
        cleaned_stem
    )

    # --------------------------------------------------------
    # Apply season from MyAnimeList (or --season).
    #
    # Overrides the season in the filename, except for
    # specials and explicit S00 files, which stay in Season 0.
    # --------------------------------------------------------

    if (
        season_override is not None
        and special_type is None
        and season != 0
    ):
        season = season_override

    # ========================================================
    # SPECIAL / OVA / MOVIE
    # ========================================================

    if special_type:

        season = 0

        season_dir = (
            destination_root
            / get_season_folder_name(season)
        )

        existing_numbers = (
            get_existing_episode_numbers(
                season_dir
            )
        )

        used_numbers = (
            existing_numbers
            | used_special_numbers
        )

        episode = 1

        while episode in used_numbers:
            episode += 1

        used_special_numbers.add(
            episode
        )

    # ========================================================
    # NORMAL EPISODE
    # ========================================================

    else:

        if season is None:
            season = 1

        if episode is None:

            print()
            print(
                "[SKIP] Could not determine episode:"
            )
            print(
                f"       {file_path}"
            )
            print(
                f"       Cleaned: {cleaned_stem}"
            )

            return False, True

        season_dir = (
            destination_root
            / get_season_folder_name(season)
        )

    # ========================================================
    # FINAL FILENAME
    # ========================================================

    new_filename = (
        f"{anime_title} - "
        f"S{season:02d}"
        f"E{episode:02d}"
    )

    # Add season/arc title when supplied.
    if season_title:
        new_filename += (
            f" ({season_title})"
        )

    new_filename += (
        file_path.suffix.lower()
    )

    destination = (
        season_dir
        / new_filename
    )

    # ========================================================
    # SOURCE == DESTINATION
    #
    # This happens when the user is simply correcting the
    # anime title of an existing Jellyfin folder.
    #
    # Example:
    #
    # Ichijouma Mankitsugurashi!
    # ->
    # Ichijyoma Mankitsu Gurashi!
    #
    # The parent folder may be the destination itself.
    # ========================================================

    try:
        same_file = (
            file_path.resolve()
            == destination.resolve()
        )
    except OSError:
        same_file = (
            file_path == destination
        )

    if same_file:

        print()
        print(
            f"SOURCE : {file_path}"
        )
        print(
            f"CLEANED: {cleaned_stem}"
        )

        if special_type:
            print(
                f"TYPE   : {special_type} -> {get_season_folder_name(season)}"
            )
        else:
            print(
                f"TYPE   : Episode -> {get_season_folder_name(season)}"
            )

        if season_title:
            print(
                f"TITLE  : {season_title}"
            )

        print(
            f"DEST   : {destination}"
        )
        print(
            "STATUS : Already correctly named."
        )

        return True, True

    # ========================================================
    # DESTINATION CONFLICT
    # ========================================================

    if destination.exists():

        print()
        print(
            "[WARNING] Destination already exists."
        )
        print(
            f"  SOURCE : {file_path}"
        )
        print(
            f"  DEST   : {destination}"
        )
        print(
            "  SKIPPING SOURCE FILE."
        )

        # Important:
        # The source file must remain because we did not move it.
        return False, False

    # ========================================================
    # SHOW OPERATION
    # ========================================================

    print()
    print(
        f"SOURCE : {file_path}"
    )
    print(
        f"CLEANED: {cleaned_stem}"
    )

    if special_type:
        print(
            f"TYPE   : {special_type} -> {get_season_folder_name(season)}"
        )
    else:
        print(
            f"TYPE   : Episode -> {get_season_folder_name(season)}"
        )

    if season_title:
        print(
            f"TITLE  : {season_title}"
        )

    print(
        f"DEST   : {destination}"
    )

    # ========================================================
    # MOVE
    # ========================================================

    if execute:

        season_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.move(
            str(file_path),
            str(destination),
        )

    return True, True


# ============================================================
# PROCESS FILES
# ============================================================

def process_files(
    files: list[Path],
    destination_root: Path,
    anime_title: str,
    execute: bool,
    season_override: int | None,
    season_title: str,
) -> tuple[int, int, bool]:
    """
    Process all files.

    Returns:

        processed
        skipped
        safe_to_delete_source
    """

    processed = 0
    skipped = 0
    safe_to_delete_source = True

    used_special_numbers: set[int] = set()

    for file_path in files:

        success, safe = process_file(
            file_path=file_path,
            destination_root=destination_root,
            anime_title=anime_title,
            execute=execute,
            used_special_numbers=used_special_numbers,
            season_override=season_override,
            season_title=season_title,
        )

        if success:
            processed += 1
        else:
            skipped += 1

        if not safe:
            safe_to_delete_source = False

    return (
        processed,
        skipped,
        safe_to_delete_source,
    )


def process_movie_files(
    files: list[Path],
    destination_root: Path,
    file_title: str,
    execute: bool,
) -> tuple[int, int, bool]:
    """
    Name a standalone movie for Jellyfin:

        Title [tmdbid-ID]/Title.ext

    Only the largest video file is treated as the movie.
    Any other video files are left untouched.

    Returns:

        processed
        skipped
        safe_to_delete_source
    """

    ordered = sorted(
        files,
        key=lambda path: path.stat().st_size,
        reverse=True,
    )

    processed = 0
    skipped = 0
    safe_to_delete_source = True

    for index, file_path in enumerate(ordered):

        if index > 0:

            print()
            print(
                "[SKIP] Extra video file "
                "(only the largest file is the movie):"
            )
            print(
                f"       {file_path}"
            )

            skipped += 1

            continue

        destination = (
            destination_root
            / f"{file_title}{file_path.suffix.lower()}"
        )

        print()
        print(
            f"SOURCE : {file_path}"
        )
        print(
            "TYPE   : Movie"
        )
        print(
            f"DEST   : {destination}"
        )

        try:
            same_file = (
                file_path.resolve()
                == destination.resolve()
            )
        except OSError:
            same_file = (
                file_path == destination
            )

        if same_file:

            print(
                "STATUS : Already correctly named."
            )

            processed += 1

            continue

        if destination.exists():

            print()
            print(
                "[WARNING] Destination already exists."
            )
            print(
                "  SKIPPING SOURCE FILE."
            )

            skipped += 1
            safe_to_delete_source = False

            continue

        if execute:

            destination_root.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.move(
                str(file_path),
                str(destination),
            )

        processed += 1

    return (
        processed,
        skipped,
        safe_to_delete_source,
    )


# ============================================================
# SOURCE FOLDER CLEANUP
# ============================================================

def cleanup_empty_source_folder(
    source_root: Path,
    destination_root: Path,
) -> bool:
    """
    Remove empty source directories after processing.

    Important safety behavior:

    - Never delete destination_root.
    - Never delete a source folder that still contains files.
    - Remove only empty directories.
    - If source_root == destination_root, do nothing.

    Returns:

        True  -> source is gone or intentionally preserved
        False -> source still contains files/directories
    """

    try:
        source_resolved = source_root.resolve()
        destination_resolved = destination_root.resolve()
    except OSError:
        source_resolved = source_root
        destination_resolved = destination_root

    # --------------------------------------------------------
    # Source and destination are the same folder.
    #
    # This is an intentional in-place rename operation.
    # --------------------------------------------------------

    if source_resolved == destination_resolved:

        print()
        print(
            "SOURCE AND DESTINATION ARE THE SAME FOLDER."
        )
        print(
            "The folder will be preserved."
        )

        return True

    if not source_root.exists():
        return True

    # --------------------------------------------------------
    # Remove empty subdirectories from deepest to shallowest.
    # --------------------------------------------------------

    directories = []

    try:
        for path in source_root.rglob("*"):
            if path.is_dir():
                directories.append(path)

    except OSError:
        pass

    directories.sort(
        key=lambda path: len(path.parts),
        reverse=True,
    )

    for directory in directories:

        try:
            directory.rmdir()

            print(
                f"Removed empty folder: {directory}"
            )

        except OSError:
            # Directory is not empty or cannot be removed.
            pass

    # --------------------------------------------------------
    # Finally remove source root if empty.
    # --------------------------------------------------------

    try:
        source_root.rmdir()

        print()
        print(
            "Source folder deleted because it is empty."
        )

        return True

    except OSError:
        print()
        print(
            "Source folder still contains files."
        )
        print(
            "It was not deleted."
        )

        return False


# ============================================================
# MOVE FINISHED FOLDER
# ============================================================

def move_finished_folder(
    finished_folder: Path,
    destination_root: Path,
) -> bool:
    """
    Move the finished anime folder into destination_root.

    If destination already exists, the contents are merged
    safely instead of replacing the existing anime folder.

    Existing files are never overwritten.

    Returns:

        True  when everything was moved or already merged.
        False when files remain in the source folder.
    """

    if not finished_folder.exists():

        print()
        print(
            "[ERROR] Finished folder does not exist:"
        )
        print(
            f"        {finished_folder}"
        )

        return False

    if not finished_folder.is_dir():

        print()
        print(
            "[ERROR] Finished path is not a directory:"
        )
        print(
            f"        {finished_folder}"
        )

        return False

    destination_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = (
        destination_root
        / finished_folder.name
    )

    # ========================================================
    # SAME DIRECTORY
    # ========================================================

    try:
        same_directory = (
            finished_folder.resolve()
            == destination.resolve()
        )
    except OSError:
        same_directory = (
            finished_folder == destination
        )

    if same_directory:

        print()
        print(
            "Finished folder is already in the destination."
        )
        print(
            f"LOCATION: {finished_folder}"
        )

        return True

    # ========================================================
    # DESTINATION DOES NOT EXIST
    #
    # Move the entire folder directly.
    # ========================================================

    if not destination.exists():

        print()
        print("=" * 70)
        print("MOVING FINISHED FOLDER")
        print("=" * 70)
        print(
            f"SOURCE      : {finished_folder}"
        )
        print(
            f"DESTINATION : {destination}"
        )

        try:

            shutil.move(
                str(finished_folder),
                str(destination),
            )

            print()
            print(
                "Finished folder moved successfully."
            )

            return True

        except OSError as error:

            print()
            print(
                "[ERROR] Could not move finished folder."
            )
            print(
                f"        {error}"
            )

            return False

    # ========================================================
    # DESTINATION EXISTS
    #
    # Merge its contents instead of failing.
    # ========================================================

    print()
    print("=" * 70)
    print("MERGING FINISHED FOLDER")
    print("=" * 70)
    print(
        "The destination folder already exists."
    )
    print(
        "Its contents will be merged instead of replacing it."
    )
    print()
    print(
        f"SOURCE      : {finished_folder}"
    )
    print(
        f"DESTINATION : {destination}"
    )

    source_files_remaining = False

    # --------------------------------------------------------
    # Walk through everything under the source folder.
    # --------------------------------------------------------

    source_items = list(
        finished_folder.rglob("*")
    )

    source_items.sort(
        key=lambda path: (
            not path.is_dir(),
            len(path.parts),
        )
    )

    for source_item in source_items:

        relative_path = (
            source_item.relative_to(
                finished_folder
            )
        )

        destination_item = (
            destination
            / relative_path
        )

        # ----------------------------------------------------
        # Directory
        # ----------------------------------------------------

        if source_item.is_dir():

            try:
                destination_item.mkdir(
                    parents=True,
                    exist_ok=True,
                )

            except OSError as error:

                print()
                print(
                    "[WARNING] Could not create directory:"
                )
                print(
                    f"          {destination_item}"
                )
                print(
                    f"          {error}"
                )

            continue

        # ----------------------------------------------------
        # File
        # ----------------------------------------------------

        destination_item.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if destination_item.exists():

            print()
            print(
                "[WARNING] Destination already exists:"
            )
            print(
                f"          {destination_item}"
            )
            print(
                "          Skipping source file."
            )

            source_files_remaining = True

            continue

        print()
        print(
            f"MOVE FILE : {source_item}"
        )
        print(
            f"         -> {destination_item}"
        )

        try:

            shutil.move(
                str(source_item),
                str(destination_item),
            )

        except OSError as error:

            print()
            print(
                "[WARNING] Could not move file:"
            )
            print(
                f"          {source_item}"
            )
            print(
                f"          {error}"
            )

            source_files_remaining = True

    # --------------------------------------------------------
    # Remove empty source directories.
    # --------------------------------------------------------

    directories = []

    try:
        for path in finished_folder.rglob("*"):
            if path.is_dir():
                directories.append(path)

    except OSError:
        pass

    directories.sort(
        key=lambda path: len(path.parts),
        reverse=True,
    )

    for directory in directories:

        try:
            directory.rmdir()
        except OSError:
            pass

    # --------------------------------------------------------
    # Remove source root if empty.
    # --------------------------------------------------------

    try:
        finished_folder.rmdir()

    except OSError:
        source_files_remaining = True

    # --------------------------------------------------------
    # Final result.
    # --------------------------------------------------------

    if source_files_remaining:

        print()
        print(
            "Finished folder still contains files."
        )
        print(
            "It was not deleted."
        )

        return False

    print()
    print(
        "Finished folder merged successfully."
    )

    return True


# ============================================================
# CONFIRMATION
# ============================================================

def ask_for_confirmation() -> bool:
    """
    Ask the user whether the planned operation
    should actually be performed.

    Default answer is No.
    """

    print()
    print("=" * 70)
    print("CONFIRMATION")
    print("=" * 70)

    print(
        "The files above are about to be moved and renamed."
    )

    print()
    print(
        "WARNING:"
    )

    print(
        "Only files that can be safely moved will be processed."
    )

    print(
        "Existing destination files will never be overwritten."
    )

    print()

    while True:

        answer = input(
            "Proceed with these changes? [y/N]: "
        ).strip().lower()

        if not answer:
            return False

        if answer in {"y", "yes"}:
            return True

        if answer in {"n", "no"}:
            return False

        print(
            "Please answer 'y' or 'n'."
        )


# ============================================================
# ARGUMENT PARSER
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Organize anime files into a "
            "Jellyfin-compatible folder structure."
        )
    )

    parser.add_argument(
        "--review",
        action="store_true",
        help=(
            "Show a preview and ask for confirmation "
            "before executing changes."
        ),
    )

    parser.add_argument(
        "--season",
        type=int,
        help=(
            "Override the season number "
            "detected from MyAnimeList."
        ),
    )

    parser.add_argument(
        "--tmdb-id",
        type=int,
        help=(
            "Use this TMDB ID (TV show, or movie for "
            "standalone movies) instead of searching."
        ),
    )

    parser.add_argument(
        "--no-move",
        action="store_true",
        help=(
            "Do not move the result to "
            "FINISHED_FOLDER_PATH."
        ),
    )

    return parser


# ============================================================
# INPUT VALIDATION
# ============================================================

def validate_inputs(
    source_root: Path,
    anime_title: str,
) -> str | None:
    """Return an error message if inputs are invalid."""

    if not source_root.exists():

        return (
            "ERROR: Target folder does not exist:\n"
            f"       {source_root}"
        )

    if not source_root.is_dir():

        return (
            "ERROR: Target is not a directory:\n"
            f"       {source_root}"
        )

    if not anime_title:

        return (
            "ERROR: Anime title cannot be empty."
        )

    return None


# ============================================================
# HEADER
# ============================================================

def print_header(
    source_root: Path,
    anime_title: str,
    destination_root: Path,
    season_override: int | None,
    season_title: str,
    finished_folder_path: Path,
    review: bool,
) -> None:
    """Print operation settings."""

    print()
    print("=" * 70)
    print("JELLYFIN Anime/Movie/TV Shows ORGANIZER")
    print("=" * 70)

    print(
        f"Source folder      : {source_root}"
    )

    print(
        f"Anime title        : {anime_title}"
    )

    if season_override is None:

        print(
            "Season             : n/a (movie)"
        )

    else:

        print(
            f"Season             : Season {season_override:02d}"
        )

    if season_title:

        print(
            f"Season/arc title   : {season_title}"
        )

    else:

        print(
            "Season/arc title   : None"
        )

    print(
        f"Destination folder : {destination_root}"
    )

    print(
        f"Finished folder    : {finished_folder_path}"
    )

    print()

    if review:

        print(
            "MODE               : REVIEW"
        )
        print()
        print(
            "Nothing will be changed until you confirm."
        )

    else:

        print(
            "MODE               : AUTOMATIC"
        )
        print()
        print(
            "Changes will be executed automatically."
        )

    print()


# ============================================================
# SUMMARY
# ============================================================

def print_summary(
    processed: int,
    skipped: int,
) -> None:
    """Print processing counts."""

    print()
    print("=" * 70)

    print(
        f"Processed : {processed}"
    )

    print(
        f"Skipped   : {skipped}"
    )


# ============================================================
# MAIN
# ============================================================

def main() -> int:
    """Run the organizer."""

    args = (
        build_parser()
        .parse_args()
    )

    # --------------------------------------------------------
    # Ask for source folder.
    # --------------------------------------------------------

    source_root = ask_for_source_folder()

    # --------------------------------------------------------
    # Ask for MyAnimeList URL / ID.
    # --------------------------------------------------------

    mal_id = ask_for_mal_id()

    # --------------------------------------------------------
    # Look up MyAnimeList + TMDB.
    # --------------------------------------------------------

    mal_client_id = get_api_key(ENV_MAL_CLIENT_ID_KEY)
    tmdb_api_key = get_api_key(ENV_TMDB_API_KEY_KEY)

    print()
    print("Fetching metadata...")

    series = resolve_mal_series(
        mal_id,
        mal_client_id,
    )

    # Standalone movies are searched as TMDB movies,
    # everything else as TMDB TV shows.
    kind = "movie" if series.is_movie else "tv"

    if args.tmdb_id:
        tmdb = fetch_tmdb(
            kind,
            args.tmdb_id,
            tmdb_api_key,
        )
    else:
        tmdb = search_tmdb(
            kind,
            series.target if series.is_movie else series.first,
            tmdb_api_key,
        )

    title, title_source = pick_title(
        tmdb_name(tmdb),
        fetch_tmdb_alternative_titles(
            tmdb["id"],
            tmdb_api_key,
            kind,
        ),
    )

    folder_name, anime_title = build_names(
        tmdb,
        title,
    )

    if series.is_movie:
        season_override = None
        season_source = "n/a (movie)"
    elif args.season is not None:
        season_override = args.season
        season_source = "--season"
    else:
        season_override = series.season
        season_source = "MAL prequel chain"

    # Season/arc titles are no longer used.
    season_title = ""

    # --------------------------------------------------------
    # Load configuration.
    # --------------------------------------------------------

    finished_folder_path = (
        get_finished_folder_path()
    )

    # --------------------------------------------------------
    # Destination is based on the source folder's parent.
    #
    # Example:
    #
    # /home/levi/storage/downloads/My Anime
    #
    # becomes:
    #
    # /home/levi/storage/downloads/New Anime
    #
    # It can then be moved into FINISHED_FOLDER_PATH.
    # --------------------------------------------------------

    destination_root = (
        source_root.parent
        / folder_name
    )

    # --------------------------------------------------------
    # Validate inputs.
    # --------------------------------------------------------

    error_message = validate_inputs(
        source_root,
        anime_title,
    )

    if error_message:

        print()
        print(error_message)

        return 1

    # --------------------------------------------------------
    # Header.
    # --------------------------------------------------------

    print_header(
        source_root,
        anime_title,
        destination_root,
        season_override,
        season_title,
        finished_folder_path,
        args.review,
    )

    # --------------------------------------------------------
    # Metadata used for the rename.
    # --------------------------------------------------------

    print("=" * 70)
    print("METADATA")
    print("=" * 70)

    print(
        f"MAL    : {series.target['title']} "
        f"(id {mal_id}, "
        f"{series.target.get('media_type', '?')})"
    )
    print(
        f"TMDB   : {tmdb_name(tmdb)} (id {tmdb['id']}, {kind})"
    )
    print(
        f"TITLE  : {title} [{title_source}]"
    )
    print(
        f"FOLDER : {folder_name}"
    )
    if series.is_movie:
        print(
            "TYPE   : Movie (standalone, no season folder)"
        )
    else:
        print(
            f"SEASON : {season_override} ({season_source})"
        )

    if args.review:
        print()
        print(
            "If the TMDB match is wrong, answer N and "
            "rerun with --tmdb-id."
        )

    print()

    # --------------------------------------------------------
    # Find video files.
    # --------------------------------------------------------

    files = find_video_files(
        source_root
    )

    if not files:

        print()
        print(
            "No supported video files found."
        )

        return 0

    print()
    print(
        f"Found {len(files)} video file(s)."
    )

    def run(execute: bool) -> tuple[int, int, bool]:
        """Process the files as a movie or as series episodes."""

        if series.is_movie:
            return process_movie_files(
                files=files,
                destination_root=destination_root,
                file_title=anime_title,
                execute=execute,
            )

        return process_files(
            files=files,
            destination_root=destination_root,
            anime_title=anime_title,
            execute=execute,
            season_override=season_override,
            season_title=season_title,
        )

    # ========================================================
    # REVIEW MODE
    # ========================================================

    if args.review:

        print()
        print("=" * 70)
        print("PREVIEW")
        print("=" * 70)

        (
            preview_processed,
            preview_skipped,
            preview_safe,
        ) = run(False)

        print_summary(
            preview_processed,
            preview_skipped,
        )

        if not preview_safe:

            print()
            print("=" * 70)
            print("WARNING")
            print("=" * 70)

            print(
                "At least one destination file already exists."
            )

            print(
                "Those source files will remain untouched."
            )

        if preview_processed == 0:

            print()
            print(
                "Nothing can be processed."
            )

            return 1

        if not ask_for_confirmation():

            print()
            print("=" * 70)
            print("CANCELLED")
            print("=" * 70)

            print(
                "No files or folders were changed."
            )

            return 0

    # ========================================================
    # EXECUTION
    # ========================================================

    print()
    print("=" * 70)
    print("EXECUTING")
    print("=" * 70)

    (
        processed,
        skipped,
        safe_to_delete_source,
    ) = run(True)

    # --------------------------------------------------------
    # Summary.
    # --------------------------------------------------------

    print_summary(
        processed,
        skipped,
    )

    # --------------------------------------------------------
    # File processing complete.
    # --------------------------------------------------------

    print()
    print(
        "FILE PROCESSING COMPLETE."
    )

    # ========================================================
    # SOURCE CLEANUP
    # ========================================================

    if safe_to_delete_source:

        source_cleanup_success = (
            cleanup_empty_source_folder(
                source_root,
                destination_root,
            )
        )

    else:

        source_cleanup_success = False

        print()
        print("=" * 70)
        print(
            "SOURCE FOLDER WAS NOT DELETED"
        )
        print("=" * 70)

        print(
            "At least one source file could not be moved"
        )
        print(
            "because its destination already exists."
        )

        print(
            f"Review: {source_root}"
        )

    # ========================================================
    # FINISHED FOLDER
    #
    # IMPORTANT:
    #
    # There is NO separate y/N prompt here.
    #
    # Normal mode:
    #     automatically move/merge.
    #
    # --review:
    #     confirmation above controls the entire operation.
    # ========================================================

    print()
    print("=" * 70)
    print("FINISHED FOLDER")
    print("=" * 70)

    if args.no_move:

        finished_move_success = True

        print()
        print(
            "Skipped (--no-move)."
        )

    else:

        finished_move_success = (
            move_finished_folder(
                finished_folder=destination_root,
                destination_root=finished_folder_path,
            )
        )

    # ========================================================
    # FINAL STATUS
    # ========================================================

    print()
    print("=" * 70)
    print("DONE.")
    print("=" * 70)

    print(
        f"Anime folder: {destination_root}"
    )

    if not source_cleanup_success:

        print()
        print(
            "[WARNING] Some source files remain."
        )

    if not finished_move_success:

        print()
        print(
            "[WARNING] Finished folder could not be completely moved."
        )

    # Return non-zero when something could not be completed.
    if (
        not source_cleanup_success
        or not finished_move_success
    ):
        return 1

    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    raise SystemExit(
        main()
    )
