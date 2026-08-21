#!/usr/bin/env python3

"""Organize downloaded Anime/Movie/TV Shows episodes for Jellyfin."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


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


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_spaces(text: str) -> str:
    """Normalize whitespace and separators."""

    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*-\s*", " - ", text)

    return text.strip(" -._").strip()


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


# ============================================================
# EPISODE DETECTION
# ============================================================

def detect_episode(
    filename: str,
) -> tuple[int | None, int | None, str | None]:
    """
    Detect season and episode information.

    Returns:

        (season, episode, special_type)

    Examples:

        Sousou no Frieren - 25
            -> (None, 25, None)

        Sousou no Frieren - 25 END
            -> (None, 25, None)

        Sousou no Frieren S01E25
            -> (1, 25, None)

        Sousou no Frieren Episode 25
            -> (None, 25, None)

        Sousou no Frieren OVA
            -> (0, None, "OVA")

        Sousou no Frieren Movie
            -> (0, None, "Movie")

        Sousou no Frieren Special
            -> (0, None, "Special")
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

    if special_match:
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
            and path.suffix.lower() in VIDEO_EXTENSIONS
        )
    ]


# ============================================================
# SPECIAL EPISODE NUMBERING
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
) -> tuple[bool, bool]:
    """
    Process one video file.

    Returns:

        (success, safe_to_delete_source)

    safe_to_delete_source is False when a destination
    conflict occurs.
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

    # ========================================================
    # SPECIAL / OVA / MOVIE
    # ========================================================

    if special_type:

        season = 0

        season_dir = (
            destination_root
            / "Season 00"
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
            / f"Season {season:02d}"
        )

    # ========================================================
    # FINAL FILENAME
    # ========================================================

    new_filename = (
        f"{anime_title} - "
        f"S{season:02d}"
        f"E{episode:02d}"
        f"{file_path.suffix.lower()}"
    )

    destination = (
        season_dir
        / new_filename
    )

    # ========================================================
    # SAFETY CHECK
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
            "  SKIPPING."
        )

        # Do NOT delete the source folder if there
        # is a destination conflict.

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
            f"TYPE   : "
            f"{special_type} -> Season 00"
        )

    else:

        print(
            f"TYPE   : "
            f"Episode -> Season {season:02d}"
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
# DELETE SOURCE FOLDER
# ============================================================

def delete_source_folder(
    source_root: Path,
) -> bool:
    """Delete the original source folder and everything inside."""

    if not source_root.exists():
        return True

    print()
    print("=" * 70)
    print("REMOVING SOURCE FOLDER")
    print("=" * 70)

    print(
        f"Deleting: {source_root}"
    )

    try:

        shutil.rmtree(
            source_root
        )

        print(
            "Source folder deleted."
        )

        return True

    except OSError as error:

        print(
            "ERROR: Could not delete source folder."
        )

        print(
            f"       {error}"
        )

        return False


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
        "The entire original source folder will be deleted"
    )
    print(
        "after processing, including any files that were skipped."
    )

    print()
    print(
        "This deletion cannot be undone."
    )

    print()

    while True:

        answer = input(
            "Proceed with these changes? [y/N]: "
        ).strip().lower()

        # Empty input means NO.

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
        "target_folder",
        help=(
            "Folder containing anime files; "
            "subfolders are searched recursively."
        ),
    )

    parser.add_argument(
        "anime_title",
        help=(
            "Show title used for the destination "
            "folder and filenames."
        ),
    )

    return parser


# ============================================================
# INPUT VALIDATION
# ============================================================

def validate_inputs(
    source_root: Path,
    anime_title: str,
    destination_root: Path,
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

    if source_root == destination_root:

        return (
            "ERROR: Source and destination "
            "are identical."
        )

    return None


# ============================================================
# PROCESS FILES
# ============================================================

def process_files(
    files: list[Path],
    destination_root: Path,
    anime_title: str,
    execute: bool,
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

    # Used to give multiple OVA/Movie/Special files
    # unique episode numbers during this run.

    used_special_numbers: set[int] = set()

    for file_path in files:

        success, safe = process_file(
            file_path=file_path,
            destination_root=destination_root,
            anime_title=anime_title,
            execute=execute,
            used_special_numbers=used_special_numbers,
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


# ============================================================
# HEADER
# ============================================================

def print_header(
    source_root: Path,
    anime_title: str,
    destination_root: Path,
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

    print(
        f"Destination folder : {destination_root}"
    )

    print()
    print(
        "MODE               : CONFIRM BEFORE EXECUTION"
    )

    print()
    print(
        "Nothing will be changed until you confirm."
    )

    print(
        "Press Enter at the confirmation prompt to cancel."
    )

    print()
    print("-" * 70)


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
    """Run the organizer command."""

    args = (
        build_parser()
        .parse_args()
    )

    source_root = (
        Path(args.target_folder)
        .expanduser()
        .resolve()
    )

    anime_title = clean_spaces(
        args.anime_title
    )

    destination_root = (
        source_root.parent
        / anime_title
    )

    # --------------------------------------------------------
    # Validate inputs.
    # --------------------------------------------------------

    error_message = validate_inputs(
        source_root,
        anime_title,
        destination_root,
    )

    if error_message:

        print(
            error_message
        )

        return 1

    # --------------------------------------------------------
    # Header.
    # --------------------------------------------------------

    print_header(
        source_root,
        anime_title,
        destination_root,
    )

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

    # --------------------------------------------------------
    # PREVIEW
    #
    # First pass only displays what will happen.
    # No files are modified.
    # --------------------------------------------------------

    (
        preview_processed,
        preview_skipped,
        preview_safe,
    ) = process_files(
        files=files,
        destination_root=destination_root,
        anime_title=anime_title,
        execute=False,
    )

    print_summary(
        preview_processed,
        preview_skipped,
    )

    # --------------------------------------------------------
    # If there is a destination conflict, don't allow the
    # user to proceed because deleting the source folder
    # could destroy the conflicting source file.
    # --------------------------------------------------------

    if not preview_safe:

        print()
        print("=" * 70)
        print("OPERATION CANCELLED")
        print("=" * 70)

        print(
            "At least one destination file already exists."
        )

        print(
            "The source folder will NOT be deleted."
        )

        return 1

    # --------------------------------------------------------
    # If nothing can be processed, don't ask for confirmation.
    # --------------------------------------------------------

    if preview_processed == 0:

        print()
        print(
            "Nothing can be processed."
        )

        print(
            "Source folder was NOT deleted."
        )

        return 1

    # --------------------------------------------------------
    # Ask for confirmation.
    # --------------------------------------------------------

    if not ask_for_confirmation():

        print()
        print("=" * 70)
        print("CANCELLED")
        print("=" * 70)

        print(
            "No files or folders were changed."
        )

        return 0

    # --------------------------------------------------------
    # Execute the operation.
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("EXECUTING")
    print("=" * 70)

    (
        processed,
        skipped,
        safe_to_delete_source,
    ) = process_files(
        files=files,
        destination_root=destination_root,
        anime_title=anime_title,
        execute=True,
    )

    # --------------------------------------------------------
    # Summary.
    # --------------------------------------------------------

    print_summary(
        processed,
        skipped,
    )

    # --------------------------------------------------------
    # Delete source folder.
    # --------------------------------------------------------

    print()
    print(
        "FILE PROCESSING COMPLETE."
    )

    if safe_to_delete_source:

        delete_source_folder(
            source_root
        )

    else:

        print()
        print("=" * 70)
        print(
            "SOURCE FOLDER WAS NOT DELETED"
        )
        print("=" * 70)

        print(
            "At least one destination file "
            "already existed."
        )

        print(
            f"Review: {source_root}"
        )

    # --------------------------------------------------------
    # Done.
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("DONE.")
    print("=" * 70)

    print(
        f"Anime folder: {destination_root}"
    )

    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    raise SystemExit(
        main()
    )