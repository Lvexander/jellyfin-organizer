"""Environment/configuration loading."""

from __future__ import annotations

from pathlib import Path

from .constants import (
    DEFAULT_FINISHED_FOLDER_PATH,
    DEFAULT_SEARCH_PATHS,
    ENV_FILENAME,
    ENV_FINISHED_FOLDER_KEY,
    ENV_SEARCH_PATHS_KEY,
)


def load_env_file() -> dict[str, str]:
    """Load simple KEY=VALUE pairs from the project .env file."""

    env_path = Path(__file__).resolve().parent.parent / ENV_FILENAME

    if not env_path.exists():
        return {}

    values: dict[str, str] = {}

    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            if (
                len(value) >= 2
                and value[0] == value[-1]
                and value[0] in {"'", '"'}
            ):
                value = value[1:-1]

            values[key] = value

    except OSError as error:
        print()
        print(f"[WARNING] Could not read .env file: {error}")

    return values


def get_finished_folder_path() -> Path:
    """Return the configured finished-folder destination."""

    env = load_env_file()
    configured_path = env.get(
        ENV_FINISHED_FOLDER_KEY,
        DEFAULT_FINISHED_FOLDER_PATH,
    ).strip()

    if not configured_path:
        configured_path = DEFAULT_FINISHED_FOLDER_PATH

    return Path(configured_path).expanduser().resolve()


def get_search_paths() -> list[Path]:
    """Return directories used when searching for the source folder."""

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

        path = Path(raw_path).expanduser().resolve()

        if path not in paths:
            paths.append(path)

    return paths
