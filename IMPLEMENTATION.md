# Implementation Plan

## Phase 1: Python Refactor Without Behavior Change

Phase 1 should make the project easier to change without immediately switching languages or adding UI/API complexity.

The current `__main__.py` should be split into modules. The CLI should still behave like it does today.

---

## Target File Layout for Phase 1

```text
jellyfin-organizer/
├── __main__.py              # thin entrypoint only
├── jellyfin_organizer/
│   ├── __init__.py
│   ├── cli.py               # argparse + interactive prompts
│   ├── config.py            # env/default config loading
│   ├── constants.py         # extensions/defaults/shared constants
│   ├── models.py            # dataclasses/enums for plans and results
│   ├── scanner.py           # source folder search + video file discovery
│   ├── text.py              # filename/title cleaning helpers
│   ├── anime_rule.py        # current anime-specific detection/naming behavior
│   ├── planner.py           # converts files + rule inputs into operations
│   ├── executor.py          # executes planned filesystem operations safely
│   └── cleanup.py           # empty source cleanup + finished folder merge
├── SPEC.md
├── IMPLEMENTATION.md
└── README.md
```

This layout intentionally keeps `anime_rule.py` for the existing behavior. Later phases can replace or generalize it into YAML-backed rules.

---

## Important Design Change

Current flow is roughly:

```text
find file -> detect episode -> print -> maybe move immediately
```

Refactored flow should become:

```text
find files -> create plan -> print/review plan -> execute plan
```

This makes the future UI/API much easier because both can use the same plan object.

---

## Suggested Data Models

Use dataclasses for phase 1.

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

class OperationStatus(str, Enum):
    OK = "ok"
    SKIPPED = "skipped"
    CONFLICT = "conflict"
    ERROR = "error"

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

@dataclass
class Plan:
    source_root: Path
    destination_root: Path
    finished_folder_path: Path
    operations: list[FileOperation]
```

The plan should contain enough information for:

- CLI preview output
- future UI preview table
- future REST JSON response
- safe execution

---

## Module Responsibilities

### `constants.py`

Move constants from `__main__.py`:

- video extensions
- default finished folder
- default search paths
- env keys
- regex patterns while still needed

### `config.py`

Move:

- `load_env_file`
- `get_finished_folder_path`
- `get_search_paths`

Later this can support config files and server environment variables.

### `text.py`

Move:

- `clean_spaces`
- `clean_filename`
- `clean_display_title`

### `scanner.py`

Move:

- `find_exact_folders`
- `find_video_files`

Possibly keep interactive folder selection in `cli.py`, not `scanner.py`.

### `anime_rule.py`

Move current anime-specific functions:

- `ask_for_season` should probably stay in `cli.py`
- `detect_episode`
- `get_season_folder_name`
- `get_existing_episode_numbers`
- anime destination filename generation

This module is transitional. It represents the current hardcoded rule.

### `planner.py`

New module.

Responsible for turning source files and user inputs into a `Plan`.

It should not move files.

A first function may look like:

```python
def build_anime_plan(
    files: list[Path],
    destination_root: Path,
    anime_title: str,
    finished_folder_path: Path,
    season_override: int | None,
    season_title: str,
) -> Plan:
    ...
```

This function should perform destination conflict checks and mark operations accordingly.

### `executor.py`

New module.

Responsible for executing `Plan` operations.

Rules:

- only execute operations with `status == OK`
- never overwrite existing destination files
- create destination directories as needed
- return execution summary

### `cleanup.py`

Move:

- `cleanup_empty_source_folder`
- `move_finished_folder`

### `cli.py`

Move:

- argument parser
- interactive prompts
- header printing
- plan preview printing
- confirmation
- summary
- top-level `main()` orchestration

`__main__.py` should become very small:

```python
from jellyfin_organizer.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

---

## Phase 1 Migration Steps

### Step 1

Create package directory and move constants/config/text helpers.

Expected behavior should remain unchanged.

### Step 2

Move scanner and CLI prompt helpers.

Expected behavior should remain unchanged.

### Step 3

Introduce `models.py` with `FileOperation`, `Plan`, and summary/result dataclasses.

No behavior change yet.

### Step 4

Replace `process_file` / `process_files` preview logic with `build_anime_plan`.

The planner should generate operations for both review and automatic modes.

### Step 5

Replace direct moving inside `process_file` with `execute_plan`.

The CLI should still print similar output to the current script.

### Step 6

Run manual smoke tests:

```bash
python3 . --review
python3 .
```

If possible, add small unit tests for pure functions:

- `clean_display_title`
- `detect_episode`
- `get_season_folder_name`
- planner conflict behavior

---

## Things Not Included in Phase 1

Do not implement these yet:

- Rust UI
- Docker server
- REST/gRPC/MCP
- YAML rules
- local LLM/agent workflow
- database
- job queue

Phase 1 is only about making the current behavior maintainable enough to iterate.

---

## Success Criteria

Phase 1 is successful when:

1. `__main__.py` is only an entrypoint.
2. The current CLI workflow still works.
3. Preview/review mode is generated from a plan object.
4. Execution uses the same plan object.
5. Existing destination files are still never overwritten.
6. The code is split into understandable modules.

---

## After Phase 1

Once phase 1 works, the next likely step is phase 2:

```text
Introduce real rule definitions while keeping the current anime rule as the first built-in rule.
```

That should be based on actual usage feedback from phase 1 rather than guessing the perfect rule system too early.
