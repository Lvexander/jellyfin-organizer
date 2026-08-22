# Jellyfin Anime/Movie/TV Shows Organizer

A small Python CLI tool for organizing downloaded anime, movies, and TV episodes into a Jellyfin-compatible folder structure.

It recursively scans a source folder, detects episode numbers, cleans release metadata, renames files, and organizes them into Season folders.

## Features

* Recursively searches for supported video files.
* Supports common formats such as `.mkv`, `.mp4`, `.avi`, `.mov`, `.wmv`, `.m4v`, `.ts`, `.webm`, and `.flv`.
* Cleans common release metadata and resolutions from filenames.
* Detects common episode formats:

  * `S01E01`
  * `E01`
  * `EP01`
  * `Episode 01`
  * `Anime - 01`
* Supports optional manual season input.
* Automatically detects `OVA`, `Movie`, and `Special` content as `Season 00`.
* Automatically numbers multiple special episodes.
* Shows a preview before making changes.
* Requires explicit confirmation before moving files.
* Deletes the original source folder after successful execution.
* Prevents source deletion when a destination file conflict is detected.

## Requirements

* Python 3.10+
* No external dependencies.

The script only uses Python's standard library.

## Installation

```bash
git clone git@github.com:Lvexander/jellyfin-organizer.git
cd jellyfin-organizer
```

No package installation or virtual environment is required.

## Usage

```bash
python3 ~/Code/jellyfin-organizer/organize.py \
    "~/Downloads/[Example] Sousou no Frieren + SP" \
    "Sousou no Frieren"
```

The script will ask for an optional season:

```text
Season number/name [Enter = auto-detect]:
```

You can enter:

```text
2
02
Season 2
Season 02
S2
S02
```

Press **Enter** to use automatic season detection.

### Season behavior

If a season is manually entered, files without an explicit season use the specified season.

For example, entering `S2`:

```text
Sousou no Frieren - 01.mkv
Sousou no Frieren - 02.mkv
```

produces:

```text
Season 02/
├── Sousou no Frieren - S02E01.mkv
└── Sousou no Frieren - S02E02.mkv
```

An explicit season in the filename takes priority over the manual input:

```text
Sousou no Frieren S01E01.mkv
```

will still be placed in `Season 01` even if `S2` was entered.

## Preview and Confirmation

The script performs a preview before making any changes.

It shows:

* Source file
* Cleaned filename
* Detected season/episode
* Destination path

It then asks:

```text
Proceed with these changes? [y/N]:
```

The default is **No**. Pressing Enter cancels the operation.

There is no `--execute` flag.

After confirmation, files are moved and renamed, and the original source folder is deleted.

## Example

### Source

```text
~/Downloads/
└── [Example] Sousou no Frieren + SP/
    ├── [Example] Sousou no Frieren - 01 [1080p].mkv
    ├── [Example] Sousou no Frieren - 02 [1080p].mkv
    ├── [Example] Sousou no Frieren - 28 END.mkv
    └── Sousou no Frieren OVA.mkv
```

The script searches recursively, so files can also be inside additional subfolders.

### Result

```text
~/Downloads/
└── Sousou no Frieren/
    ├── Season 00/
    │   └── Sousou no Frieren - S00E01.mkv
    │
    └── Season 01/
        ├── Sousou no Frieren - S01E01.mkv
        ├── Sousou no Frieren - S01E02.mkv
        └── Sousou no Frieren - S01E28.mkv
```

## Special Episodes

`OVA`, `Movie`, and `Special` files are placed in `Season 00`.

For example:

```text
Sousou no Frieren OVA.mkv
```

becomes:

```text
Season 00/Sousou no Frieren - S00E01.mkv
```

Multiple special files are automatically assigned unique episode numbers:

```text
Season 00/
├── Sousou no Frieren - S00E01.mkv
├── Sousou no Frieren - S00E02.mkv
└── Sousou no Frieren - S00E03.mkv
```

## Filename Cleaning

The script removes common release information such as:

* Square-bracketed metadata
* Video resolutions
* `WEB-DL`
* `WEBRip`
* `BluRay`
* `BDRip`
* `HDTV`
* `x264`
* `x265`
* `HEVC`
* `AAC`
* `FLAC`
* `END`
* `FINAL`

For example:

```text
[Example] Sousou no Frieren - 28 [1080p].mkv
```

is normalized to:

```text
Sousou no Frieren - 28
```

and renamed to:

```text
Sousou no Frieren - S01E28.mkv
```

## Safety

The script is designed to avoid accidental data loss, but **review the preview before confirming**.

### Destination conflicts

If the destination file already exists, the file is skipped and the source folder is **not deleted**.

### Undetected episodes

Files whose episode number cannot be determined are skipped.

However, if there are no destination conflicts, the source folder can still be deleted after execution. This means skipped files are also deleted.

For example:

```text
Source/
├── Anime - 01.mkv
├── Anime - 02.mkv
└── unknown-file.mkv
```

If the first two files are processed successfully but `unknown-file.mkv` cannot be identified, `unknown-file.mkv` will also be deleted when the source folder is removed.

**Always review the preview output carefully before confirming.**

## Jellyfin Structure

The resulting structure uses the standard Season/Episode format:

```text
Sousou no Frieren/
├── Season 00/
│   └── Sousou no Frieren - S00E01.mkv
└── Season 01/
    ├── Sousou no Frieren - S01E01.mkv
    ├── Sousou no Frieren - S01E02.mkv
    └── Sousou no Frieren - S01E03.mkv
```

Standard episodes use:

```text
Anime Name - S01E01.mkv
```

Special content uses:

```text
Anime Name - S00E01.mkv
```

## License

This project is licensed under the [MIT License](LICENSE).
