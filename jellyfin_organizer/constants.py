"""Shared constants for Jellyfin Organizer."""

from __future__ import annotations

import re

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
DEFAULT_SEARCH_PATHS = "~/shared,~/jellyfin"

ENV_FILENAME = ".env"
ENV_FINISHED_FOLDER_KEY = "FINISHED_FOLDER_PATH"
ENV_SEARCH_PATHS_KEY = "SEARCH_PATHS"

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

INVALID_FILENAME_CHARS_PATTERN = re.compile(r'[<>:"/\\|?*]')
