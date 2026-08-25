"""Text and filename cleanup helpers."""

from __future__ import annotations

import re

from .constants import (
    INVALID_FILENAME_CHARS_PATTERN,
    METADATA_PATTERN,
    RESOLUTION_PATTERN,
)


def clean_spaces(text: str) -> str:
    """Normalize whitespace and separators."""

    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*-\s*", " - ", text)

    return text.strip(" -. _").strip()


def clean_filename(stem: str) -> str:
    """Remove release metadata from a filename."""

    stem = re.sub(r"\[[^\]]*\]", " ", stem)
    stem = RESOLUTION_PATTERN.sub(" ", stem)
    stem = METADATA_PATTERN.sub(" ", stem)
    stem = re.sub(r"\(\s*\)", " ", stem)

    return clean_spaces(stem)


def clean_display_title(title: str) -> str:
    """Clean a user-provided title for use in a filename."""

    title = INVALID_FILENAME_CHARS_PATTERN.sub(" - ", title)
    title = re.sub(r"\s*-\s*-\s*", " - ", title)

    return clean_spaces(title)
