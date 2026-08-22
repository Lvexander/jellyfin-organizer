# Jellyfin Anime/Movie/TV Shows Organizer

A small Python CLI tool for organizing downloaded anime, movies, and TV episodes into a Jellyfin-compatible folder structure.

It recursively scans a folder, detects episodes, cleans release metadata, renames files, and organizes them into Season folders.

## Features

- Recursively finds video files.
- Supports common formats such as `.mkv`, `.mp4`, `.avi`, `.mov`, `.wmv`, `.m4v`, `.ts`, `.webm`, and `.flv`.
- Cleans release metadata and resolutions from filenames.
- Detects common episode formats such as `S01E01`, `E01`, `EP01`, `Episode 01`, and `Anime - 01`.
- Optional manual season override.
- Supports season input such as `2`, `Season 2`, `S2`, or `S02`.
- Detects `OVA`, `Movie`, and `Special` as `Season 00`.
- Automatically numbers multiple special episodes.
- Shows a preview before making changes.
- Requires confirmation before modifying files.
- Deletes the original source folder after successful processing.
- Prevents source deletion when a destination conflict is detected.
- Optionally moves the finished anime folder to another location.

## Requirements

- Python 3.10+
- No external dependencies.

## Installation

```bash
git clone git@github.com:Lvexander/jellyfin-organizer.git
cd jellyfin-organizer
````

No installation or virtual environment is required.

## Usage

```bash
python3 ~/Code/jellyfin-organizer/organize.py \
    "~/Downloads/[Example] Sousou no Frieren + SP" \
    "Sousou no Frieren"
```

The script first asks for an optional season:

```text
Season number/name [Enter = auto-detect]:
```

You can enter:

```text
2
Season 2
S2
S02
```

Press `Enter` to use automatic season detection.

If a season is specified, files without an explicit season will use it.

For example, entering `S2`:

```text
Sousou no Frieren - 01.mkv
```

becomes:

```text
Season 02/Sousou no Frieren - S02E01.mkv
```

An explicit season in the filename takes priority. For example, `S01E01` remains in `Season 01` even if `S2` was entered.

## Finished Folder

After processing, the script can optionally move the completed anime folder to another location.

Default:

```text
~/videos
```

For example:

```text
~/videos/
└── Sousou no Frieren/
    ├── Season 00/
    └── Season 01/
```

The script asks:

```text
Move finished folder to another location? [y/N]:
```

The default is `No`.

### Custom location

Create a `.env` file next to `organize.py`:

```env
FINISHED_FOLDER_PATH=~/videos
```

You can change it to any location, for example:

```env
FINISHED_FOLDER_PATH=~/storage/videos
```

If the destination folder already exists, the script will not overwrite or merge into it.

## Example

### Input

```text
~/Downloads/
└── [Example] Sousou no Frieren + SP/
    ├── [Example] Sousou no Frieren - 01 [1080p].mkv
    ├── [Example] Sousou no Frieren - 02 [1080p].mkv
    ├── [Example] Sousou no Frieren - 28 END.mkv
    └── Sousou no Frieren OVA.mkv
```

### Output

```text
Sousou no Frieren/
├── Season 00/
│   └── Sousou no Frieren - S00E01.mkv
└── Season 01/
    ├── Sousou no Frieren - S01E01.mkv
    ├── Sousou no Frieren - S01E02.mkv
    └── Sousou no Frieren - S01E28.mkv
```

`OVA`, `Movie`, and `Special` files are placed in `Season 00`.

## Safety

The script shows a preview before making changes:

```text
Proceed with these changes? [y/N]:
```

Pressing `Enter` cancels the operation.

**Review the preview carefully before confirming.**

If a destination file already exists, the operation is cancelled and the source folder is not deleted.

Files whose episode number cannot be detected are skipped. However, skipped files may still be deleted when the source folder is removed, so always review the preview before confirming.

## License

This project is licensed under the [MIT License](LICENSE).