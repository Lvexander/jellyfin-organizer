"""Command-line interface for Jellyfin Organizer."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from .anime_rule import get_season_folder_name
from .cleanup import cleanup_empty_source_folder, move_finished_folder
from .config import get_finished_folder_path
from .executor import execute_plan, summarize_plan
from .models import FileOperation, OperationStatus, Plan
from .planner import build_anime_plan
from .scanner import find_exact_folders, find_video_files
from .text import clean_display_title


def ask_for_source_folder() -> Path:
    """Ask for a folder name and automatically search for it."""

    while True:
        folder_name = input("Folder name: ").strip()

        if not folder_name:
            print("Folder name cannot be empty.")
            continue

        matches = find_exact_folders(folder_name)

        if not matches:
            print()
            print("[ERROR] No exact folder match found.")
            print()
            retry = input("Try another folder name? [Y/n]: ").strip().lower()

            if retry in {"", "y", "yes"}:
                continue

            raise SystemExit(1)

        if len(matches) == 1:
            print()
            print(f"Found: {matches[0]}")
            return matches[0]

        print()
        print(f"Found {len(matches)} matching folders:")
        print()

        for index, path in enumerate(matches, start=1):
            print(f"  {index}. {path}")

        print()

        while True:
            answer = input("Select folder number: ").strip()

            try:
                selected = int(answer)
            except ValueError:
                print("Please enter a valid number.")
                continue

            if 1 <= selected <= len(matches):
                return matches[selected - 1]

            print(f"Please enter a number between 1 and {len(matches)}.")


def ask_for_season() -> int | None:
    """Ask the user for an optional season number."""

    while True:
        answer = input("Season number [Enter = auto-detect]: ").strip()

        if not answer:
            return None

        match = re.fullmatch(
            r"(?:season\s*|s\s*)?(\d{1,2})",
            answer,
            flags=re.IGNORECASE,
        )

        if match:
            return int(match.group(1))

        print("Invalid season. Examples: 0, 2, Season 2, or S02.")


def ask_for_season_title() -> str:
    """Ask for an optional season/arc title."""

    answer = input("Season/arc title [Enter = none]: ").strip()

    if not answer:
        return ""

    return clean_display_title(answer)


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""

    parser = argparse.ArgumentParser(
        description="Organize anime files into a Jellyfin-compatible folder structure."
    )

    parser.add_argument(
        "--review",
        action="store_true",
        help="Show a preview and ask for confirmation before executing changes.",
    )

    return parser


def validate_inputs(source_root: Path, anime_title: str) -> str | None:
    """Return an error message if inputs are invalid."""

    if not source_root.exists():
        return f"ERROR: Target folder does not exist:\n       {source_root}"

    if not source_root.is_dir():
        return f"ERROR: Target is not a directory:\n       {source_root}"

    if not anime_title:
        return "ERROR: Anime title cannot be empty."

    return None


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
    print(f"Source folder      : {source_root}")
    print(f"Anime title        : {anime_title}")

    if season_override is None:
        print("Season             : Auto-detect")
    else:
        print(f"Season             : Season {season_override:02d}")

    if season_title:
        print(f"Season/arc title   : {season_title}")
    else:
        print("Season/arc title   : None")

    print(f"Destination folder : {destination_root}")
    print(f"Finished folder    : {finished_folder_path}")
    print()

    if review:
        print("MODE               : REVIEW")
        print()
        print("Nothing will be changed until you confirm.")
    else:
        print("MODE               : AUTOMATIC")
        print()
        print("Changes will be executed automatically.")

    print()


def print_operation(operation: FileOperation) -> None:
    """Print one planned operation in the legacy CLI style."""

    if operation.status == OperationStatus.SKIPPED:
        print()
        print("[SKIP] Could not determine episode:")
        print(f"       {operation.source}")
        print(f"       Cleaned: {operation.cleaned_name}")
        return

    if operation.status == OperationStatus.CONFLICT:
        print()
        print("[WARNING] Destination already exists.")
        print(f"  SOURCE : {operation.source}")
        print(f"  DEST   : {operation.destination}")
        print("  SKIPPING SOURCE FILE.")
        return

    print()
    print(f"SOURCE : {operation.source}")
    print(f"CLEANED: {operation.cleaned_name}")

    if operation.special_type:
        season = operation.season if operation.season is not None else 0
        print(f"TYPE   : {operation.special_type} -> {get_season_folder_name(season)}")
    else:
        print(f"TYPE   : {operation.media_kind}")

    if operation.season_title:
        print(f"TITLE  : {operation.season_title}")

    print(f"DEST   : {operation.destination}")

    if operation.reason == "Already correctly named":
        print("STATUS : Already correctly named.")


def print_plan(plan: Plan) -> None:
    """Print all operations in a plan."""

    for operation in plan.operations:
        print_operation(operation)


def print_summary(processed: int, skipped: int) -> None:
    """Print processing counts."""

    print()
    print("=" * 70)
    print(f"Processed : {processed}")
    print(f"Skipped   : {skipped}")


def ask_for_confirmation() -> bool:
    """Ask the user whether planned operations should be performed."""

    print()
    print("=" * 70)
    print("CONFIRMATION")
    print("=" * 70)
    print("The files above are about to be moved and renamed.")
    print()
    print("WARNING:")
    print("Only files that can be safely moved will be processed.")
    print("Existing destination files will never be overwritten.")
    print()

    while True:
        answer = input("Proceed with these changes? [y/N]: ").strip().lower()

        if not answer:
            return False

        if answer in {"y", "yes"}:
            return True

        if answer in {"n", "no"}:
            return False

        print("Please answer 'y' or 'n'.")


def main() -> int:
    """Run the organizer."""

    args = build_parser().parse_args()

    source_root = ask_for_source_folder()

    while True:
        raw_anime_title = input("Anime title: ").strip()
        anime_title = clean_display_title(raw_anime_title)

        if anime_title:
            break

        print("Anime title cannot be empty.")

    season_override = ask_for_season()
    season_title = ask_for_season_title()
    finished_folder_path = get_finished_folder_path()
    destination_root = source_root.parent / anime_title

    error_message = validate_inputs(source_root, anime_title)

    if error_message:
        print()
        print(error_message)
        return 1

    print_header(
        source_root,
        anime_title,
        destination_root,
        season_override,
        season_title,
        finished_folder_path,
        args.review,
    )

    files = find_video_files(source_root)

    if not files:
        print()
        print("No supported video files found.")
        return 0

    print()
    print(f"Found {len(files)} video file(s).")

    plan = build_anime_plan(
        files=files,
        source_root=source_root,
        destination_root=destination_root,
        finished_folder_path=finished_folder_path,
        anime_title=anime_title,
        season_override=season_override,
        season_title=season_title,
    )

    preview_summary = summarize_plan(plan)

    if args.review:
        print()
        print("=" * 70)
        print("PREVIEW")
        print("=" * 70)
        print_plan(plan)
        print_summary(preview_summary.processed, preview_summary.skipped)

        if not preview_summary.safe_to_delete_source:
            print()
            print("=" * 70)
            print("WARNING")
            print("=" * 70)
            print("At least one destination file already exists.")
            print("Those source files will remain untouched.")

        if preview_summary.processed == 0:
            print()
            print("Nothing can be processed.")
            return 1

        if not ask_for_confirmation():
            print()
            print("=" * 70)
            print("CANCELLED")
            print("=" * 70)
            print("No files or folders were changed.")
            return 0

    print()
    print("=" * 70)
    print("EXECUTING")
    print("=" * 70)

    if not args.review:
        print_plan(plan)

    execution_summary = execute_plan(plan)
    print_summary(execution_summary.processed, execution_summary.skipped)

    print()
    print("FILE PROCESSING COMPLETE.")

    if execution_summary.safe_to_delete_source:
        source_cleanup_success = cleanup_empty_source_folder(
            source_root,
            destination_root,
        )
    else:
        source_cleanup_success = False
        print()
        print("=" * 70)
        print("SOURCE FOLDER WAS NOT DELETED")
        print("=" * 70)
        print("At least one source file could not be moved")
        print("because its destination already exists.")
        print(f"Review: {source_root}")

    print()
    print("=" * 70)
    print("FINISHED FOLDER")
    print("=" * 70)

    finished_move_success = move_finished_folder(
        finished_folder=destination_root,
        destination_root=finished_folder_path,
    )

    print()
    print("=" * 70)
    print("DONE.")
    print("=" * 70)
    print(f"Anime folder: {destination_root}")

    if not source_cleanup_success:
        print()
        print("[WARNING] Some source files remain.")

    if not finished_move_success:
        print()
        print("[WARNING] Finished folder could not be completely moved.")

    if not source_cleanup_success or not finished_move_success:
        return 1

    return 0
