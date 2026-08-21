# Jellyfin Anime/Movie/TV Shows Organizer

A small Python CLI tool for organizing downloaded anime episodes into a
[Jellyfin](https://jellyfin.org/) compatible folder structure.

It recursively scans a target folder, detects episode numbers, cleans release
metadata from filenames, renames the files, and organizes them into Season
folders.

## Features

- Recursively searches for video files.
- Supports common video extensions:
  - `.mkv`
  - `.mp4`
  - `.avi`
  - `.mov`
  - `.wmv`
  - `.m4v`
  - `.ts`
  - `.webm`
  - `.flv`
- Removes everything inside square brackets, including the brackets.
- Removes common video resolutions:
  - `240p`
  - `360p`
  - `480p`
  - `576p`
  - `720p`
  - `900p`
  - `1080p`
  - `1440p`
  - `2160p`
  - `4320p`
  - `4K`
  - `8K`
- Removes common release metadata such as:
  - `WEB-DL`
  - `WEBRip`
  - `BluRay`
  - `BDRip`
  - `HDTV`
  - `x264`
  - `x265`
  - `HEVC`
  - `AAC`
  - `FLAC`
  - `Atmos`
  - `END`
  - `FINAL`
- Detects several episode naming formats:
  - `S01E01`
  - `E01`
  - `EP01`
  - `Episode 01`
  - `Anime - 01`
  - `Anime - 01 END`
- Automatically places `OVA`, `Movie`, and `Special` files into `Season 00`.
- Automatically numbers multiple special episodes.
- Shows the planned operations before making changes.
- Requires explicit user confirmation before modifying files.
- Moves organized files into a new anime folder.
- Deletes the original source folder after successful execution.
- Protects against deleting the source folder when a destination file already
  exists.

## Requirements

- Python 3.10 or newer
- No external Python dependencies

The script only uses Python's standard library.

## Installation

Clone the repository:

```bash
git clone git@github.com:Lvexander/jellyfin-organizer.git
cd jellyfin-organizer
````

No package installation or virtual environment is required.

## Usage

The repository directory can be passed directly to Python.

For example:

```bash
python3 ~/Code/jellyfin-organizer \
    "~/Downloads/[Example] Sousou no Frieren + SP" \
    "Sousou no Frieren"
```

The script first performs a dry run.

It will:

1. Find all supported video files.
2. Clean their filenames.
3. Detect their season and episode numbers.
4. Show the planned destination for every file.
5. Ask for confirmation before making any changes.

Example confirmation:

```text
======================================================================
CONFIRMATION
======================================================================
The files above are about to be moved and renamed.

WARNING:
The entire original source folder will be deleted
after processing, including any files that were skipped.

This deletion cannot be undone.

Proceed with these changes? [y/N]:
```

The default answer is **No**. Pressing Enter without typing `y` or `yes`
cancels the operation.

### Execute

If everything looks correct, type:

```text
y
```

at the confirmation prompt.

There is no `--execute` flag.

Once confirmed, the script moves and renames the files and then deletes the
original source folder.

## Example

### Source

Downloaded files may look like:

```text
~/Downloads/
└── [Example] Sousou no Frieren + SP/
    ├── [Example] Sousou no Frieren - 01.mkv
    ├── [Example] Sousou no Frieren - 02.mkv
    ├── [Example] Sousou no Frieren - 28 END.mkv
    └── [Example] Sousou no Frieren OVA.mkv
```

The source may also contain arbitrary nested folders:

```text
~/Downloads/
└── [Example] Sousou no Frieren + SP/
    └── random-folder/
        ├── [Example] Sousou no Frieren - 01 [1080p].mkv
        ├── [Example] Sousou no Frieren - 02 [1080p].mkv
        └── Sousou no Frieren OVA.mkv
```

The script searches recursively, so the additional folder structure does not
matter.

### Result

After confirmation and execution:

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

The original source directory is removed after processing.

## Episode Detection

### Standard season and episode

```text
Sousou no Frieren S01E05.mkv
```

becomes:

```text
Sousou no Frieren - S01E05.mkv
```

### Episode number only

```text
Sousou no Frieren - 05.mkv
```

becomes:

```text
Sousou no Frieren - S01E05.mkv
```

If no season is detected, `Season 01` is assumed.

### `END`

```text
Sousou no Frieren - 28 END.mkv
```

is detected as episode 28:

```text
Sousou no Frieren - S01E28.mkv
```

`END`, `FINAL`, and similar release metadata are removed during filename
cleaning without affecting the episode number.

### OVA

```text
Sousou no Frieren OVA.mkv
```

becomes:

```text
Season 00/Sousou no Frieren - S00E01.mkv
```

### Movie

```text
Sousou no Frieren Movie.mkv
```

is placed in:

```text
Season 00/
```

### Special

```text
Sousou no Frieren Special.mkv
```

is placed in:

```text
Season 00/
```

Multiple OVA, Movie, and Special files are automatically assigned different
episode numbers:

```text
Season 00/
├── Sousou no Frieren - S00E01.mkv
├── Sousou no Frieren - S00E02.mkv
└── Sousou no Frieren - S00E03.mkv
```

## Filename Cleaning

The script removes everything inside square brackets, including the brackets.

For example:

```text
[Example] Sousou no Frieren - 28 [1080p].mkv
```

is cleaned to:

```text
Sousou no Frieren - 28
```

It also removes common release information such as:

```text
WEB-DL
WEBRip
BluRay
1080p
x264
HEVC
AAC
END
FINAL
```

This allows filenames from different release sources to be normalized into a
consistent Jellyfin naming format.

## Safety

The script does **not** immediately modify anything.

It first shows the planned operations and asks for confirmation.

The default answer is:

```text
[y/N]
```

Pressing Enter cancels the operation.

### Destination conflicts

A destination conflict such as:

```text
Sousou no Frieren - S01E28.mkv
```

already existing will cause that file to be skipped.

If a destination conflict occurs, the source folder will **not** be deleted.

This prevents the original source file from being accidentally destroyed when
the intended destination already contains a file.

### Undetected episodes

Files for which the episode number cannot be determined are skipped.

However, if the operation proceeds and there are no destination conflicts, the
**entire source folder is still deleted afterward**.

This means skipped files are also deleted.

For example:

```text
~/Downloads/
└── [Example] Sousou no Frieren + SP/
    ├── Sousou no Frieren - 01.mkv
    ├── Sousou no Frieren - 02.mkv
    └── unknown-file.mkv
```

If the first two files are successfully processed but `unknown-file.mkv`
cannot be identified, the `unknown-file.mkv` file will also be deleted when
the source folder is removed.

**Always review the output carefully before confirming.**

## Jellyfin Structure

The resulting structure follows the typical Jellyfin TV/anime organization:

```text
Sousou no Frieren/
├── Season 00/
│   └── Sousou no Frieren - S00E01.mkv
└── Season 01/
    ├── Sousou no Frieren - S01E01.mkv
    ├── Sousou no Frieren - S01E02.mkv
    └── Sousou no Frieren - S01E03.mkv
```

The filename format is:

```text
Anime Name - S01E01.mkv
```

Special content uses:

```text
Anime Name - S00E01.mkv
```

where `Season 00` is used for OVA, Movie, and Special content.

````

One other small correction I made: the README now uses your actual repository name consistently:

```bash
git clone git@github.com:Lvexander/jellyfin-organizer.git
cd jellyfin-organizer
````

and the examples use **`Sousou no Frieren`** and **`[Example]`** rather than the real download-site name.

## License

This project is licensed under the [MIT License](LICENSE).