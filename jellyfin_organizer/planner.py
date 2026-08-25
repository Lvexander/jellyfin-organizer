"""Build filesystem operation plans."""

from __future__ import annotations

from pathlib import Path

from .anime_rule import (
    detect_episode,
    get_existing_episode_numbers,
    get_season_folder_name,
)
from .models import FileOperation, OperationStatus, OperationType, Plan
from .text import clean_filename


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left == right


def build_anime_plan(
    files: list[Path],
    source_root: Path,
    destination_root: Path,
    finished_folder_path: Path,
    anime_title: str,
    season_override: int | None,
    season_title: str,
) -> Plan:
    """Build a plan using the current anime-specific organizing behavior."""

    operations: list[FileOperation] = []
    used_special_numbers: set[int] = set()

    for file_path in files:
        cleaned_stem = clean_filename(file_path.stem)
        season, episode, special_type = detect_episode(cleaned_stem)

        if (
            season_override is not None
            and season is None
            and special_type is None
        ):
            season = season_override

        if special_type:
            season = 0
            season_dir = destination_root / get_season_folder_name(season)
            existing_numbers = get_existing_episode_numbers(season_dir)
            used_numbers = existing_numbers | used_special_numbers
            episode = 1

            while episode in used_numbers:
                episode += 1

            used_special_numbers.add(episode)
            media_kind = f"{special_type} -> {get_season_folder_name(season)}"

        else:
            if season is None:
                season = 1

            if episode is None:
                operations.append(
                    FileOperation(
                        source=file_path,
                        destination=None,
                        operation=OperationType.NOOP,
                        status=OperationStatus.SKIPPED,
                        reason="Could not determine episode",
                        cleaned_name=cleaned_stem,
                        media_kind="Episode",
                        season=season,
                        episode=None,
                        season_title=season_title,
                    )
                )
                continue

            season_dir = destination_root / get_season_folder_name(season)
            media_kind = f"Episode -> {get_season_folder_name(season)}"

        new_filename = f"{anime_title} - S{season:02d}E{episode:02d}"

        if season_title:
            new_filename += f" ({season_title})"

        new_filename += file_path.suffix.lower()
        destination = season_dir / new_filename

        if _same_path(file_path, destination):
            operations.append(
                FileOperation(
                    source=file_path,
                    destination=destination,
                    operation=OperationType.NOOP,
                    status=OperationStatus.OK,
                    reason="Already correctly named",
                    cleaned_name=cleaned_stem,
                    media_kind=media_kind,
                    season=season,
                    episode=episode,
                    special_type=special_type,
                    season_title=season_title,
                )
            )
            continue

        if destination.exists():
            operations.append(
                FileOperation(
                    source=file_path,
                    destination=destination,
                    operation=OperationType.NOOP,
                    status=OperationStatus.CONFLICT,
                    reason="Destination already exists",
                    cleaned_name=cleaned_stem,
                    media_kind=media_kind,
                    season=season,
                    episode=episode,
                    special_type=special_type,
                    season_title=season_title,
                )
            )
            continue

        operations.append(
            FileOperation(
                source=file_path,
                destination=destination,
                operation=OperationType.MOVE,
                status=OperationStatus.OK,
                cleaned_name=cleaned_stem,
                media_kind=media_kind,
                season=season,
                episode=episode,
                special_type=special_type,
                season_title=season_title,
            )
        )

    return Plan(
        source_root=source_root,
        destination_root=destination_root,
        finished_folder_path=finished_folder_path,
        operations=operations,
    )
