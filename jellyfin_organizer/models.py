"""Planning/execution data models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class OperationStatus(str, Enum):
    OK = "ok"
    SKIPPED = "skipped"
    CONFLICT = "conflict"


class OperationType(str, Enum):
    MOVE = "move"
    NOOP = "noop"


@dataclass(frozen=True)
class FileOperation:
    source: Path
    destination: Path | None
    operation: OperationType
    status: OperationStatus
    reason: str | None = None
    cleaned_name: str | None = None
    media_kind: str | None = None
    season: int | None = None
    episode: int | None = None
    special_type: str | None = None
    season_title: str = ""


@dataclass(frozen=True)
class Plan:
    source_root: Path
    destination_root: Path
    finished_folder_path: Path
    operations: list[FileOperation]


@dataclass(frozen=True)
class PlanSummary:
    processed: int
    skipped: int
    safe_to_delete_source: bool
