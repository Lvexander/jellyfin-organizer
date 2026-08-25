# Jellyfin Anime/Movie/TV Shows Organizer

A Python script for organizing downloaded anime, movies, and TV show video files into a Jellyfin-compatible folder structure.

The script can:

- Search for a source folder by name.
- Ask for the anime title interactively.
- Automatically detect season and episode numbers.
- Optionally override the season number.
- Optionally add a season/arc title.
- Clean release metadata from filenames.
- Rename episodes to a consistent format.
- Merge into an existing anime folder when appropriate.
- Move the completed anime folder to the configured Jellyfin library.
- Automatically execute changes by default.
- Use `--review` to preview changes and require confirmation before execution.

---

## Requirements

- Python 3.10+

---

## Configuration

The repository includes a `.env.example` file containing the required configuration.

Copy it to `.env`:

```bash
cp .env.example .env
```

### `FINISHED_FOLDER_PATH`

This is the root directory where organized anime folders are stored.

For example:

```text
~/storage/videos/Anime
```

The script will create:

```text
~/storage/videos/Anime/
└── Anime Title/
    ├── Season 01/
    │   ├── Anime Title - S01E01.mkv
    │   └── Anime Title - S01E02.mkv
    └── Season 02/
        └── Anime Title - S02E01.mkv
```

### `SEARCH_PATHS`

This defines the directories where the script searches for the folder you want to organize.

For example:

```env
SEARCH_PATHS=~/shared,~/jellyfin
```

If you enter:

```text
Folder name: Sousou no Frieren
```

the script searches those locations recursively for an **exact folder name**:

```text
/home/levi/storage/downloads/Sousou no Frieren
/home/levi/Downloads/Sousou no Frieren
...
```

If multiple matching folders are found, the script asks you to select which one to process.

---

## Usage

### Normal mode

Run:

```bash
python3 ~/storage/code/jellyfin-organizer
```

The script will interactively ask:

```text
Folder name: Sousou no Frieren

Searching for exact folder name: Sousou no Frieren

Found: /home/levi/storage/downloads/Sousou no Frieren

Anime title: Sousou no Frieren

Season number [Enter = auto-detect]:

Season/arc title [Enter = none]:
```

The operation is then executed automatically.

---

## Review Mode

Use `--review` when you want to see the planned changes before anything is modified:

```bash
python3 ~/storage/code/jellyfin-organizer --review
```

In review mode, the script:

1. Finds the source folder.
2. Detects the video files.
3. Shows the planned rename/move operations.
4. Shows the destination.
5. Asks for confirmation.
6. Only executes the operation if you answer `y`.

Example:

```text
======================================================================
CONFIRMATION
======================================================================
The files above are about to be moved and renamed.

WARNING:
Only files that can be safely moved will be processed.

Existing destination files will never be overwritten.

Proceed with these changes? [y/N]:
```

Press **Enter** or enter `n` to cancel.

---

# Interactive Inputs

## Folder Name

The script asks for the folder name instead of requiring the complete path:

```text
Folder name: Frieren
```

The folder must match exactly.

For example:

```text
Frieren
```

will match:

```text
Frieren
```

but not:

```text
Frieren Season 2
Frieren (1080p)
Sousou no Frieren
```

If multiple exact matches are found, you can select the correct folder.

---

## Anime Title

Enter the title you want Jellyfin to use:

```text
Anime title: Sousou no Frieren
```

This becomes both the destination folder name and the base filename.

Example:

```text
Sousou no Frieren/
└── Season 01/
    └── Sousou no Frieren - S01E01.mkv
```

The title can be different from the original folder name.

For example:

```text
Folder name: Ichijouma Mankitsugurashi!

Anime title: Ichijyoma Mankitsu Gurashi!
```

The existing folder can therefore be renamed as part of the organization process.

---

# Season Number

The script asks:

```text
Season number [Enter = auto-detect]:
```

You can enter:

```text
1
```

or:

```text
01
```

or:

```text
Season 1
```

or:

```text
Season 01
```

or:

```text
S1
```

or:

```text
S01
```

Press **Enter** to let the script automatically detect the season.

Season `0` is used for specials/OVAs. Those files are placed in a folder named:

```text
Anime Title/
└── Season/
    └── Anime Title - S00E01.mkv
```

The folder name is `Season`, but the filename still uses Jellyfin-style `S00E##` numbering.

---

# Season / Arc Title

The script also asks:

```text
Season/arc title [Enter = none]:
```

For example:

```text
Season/arc title [Enter = none]: Yuukaku-hen
```

The resulting filename becomes:

```text
Demon Slayer - S02E01 (Yuukaku-hen).mkv
```

If no title is entered:

```text
Demon Slayer - S02E01.mkv
```

---

# Episode Detection

The script supports several common filename formats.

### S01E01

```text
Anime S01E01.mkv
```

becomes:

```text
Anime - S01E01.mkv
```

### E01

```text
Anime E01.mkv
```

becomes:

```text
Anime - S01E01.mkv
```

### EP01

```text
Anime EP01.mkv
```

becomes:

```text
Anime - S01E01.mkv
```

### Episode 01

```text
Anime Episode 01.mkv
```

becomes:

```text
Anime - S01E01.mkv
```

### Number-based filenames

The script also handles filenames such as:

```text
Anime - 01.mkv
Anime - 02.mkv
Anime 03.mkv
Anime.04.mkv
```

### Specials / OVAs / Movies

Filenames containing `OVA`, `Movie`, or `Special` are treated as season `0` specials.

They are placed in the specials folder:

```text
Anime Title/
└── Season/
    ├── Anime Title - S00E01.mkv
    └── Anime Title - S00E02.mkv
```

If existing special episode numbers are already present, the script chooses the next available `S00E##` number.

---

# Release Metadata Cleaning

The script removes common release information from filenames.

For example:

```text
[Group] Sousou no Frieren - 25 [1080p][WEB-DL][x264][AAC].mkv
```

is cleaned to:

```text
Sousou no Frieren - 25
```

The final filename is then generated using the detected episode number.

Common metadata removed includes:

* `1080p`
* `2160p`
* `4K`
* `WEB-DL`
* `WEBRip`
* `BluRay`
* `BDRip`
* `HDTV`
* `REMUX`
* `x264`
* `x265`
* `H.264`
* `H.265`
* `HEVC`
* `AV1`
* `10bit`
* `AAC`
* `FLAC`
* `DDP`
* `Atmos`
* `END`
* `FINAL`
* `FINALE`

Text inside square brackets is also removed.

---

# Existing Anime Folders

The script supports adding new seasons to an anime that already exists in the Jellyfin library.

For example:

```text
~/storage/videos/Anime/Iya na Kao sare nagara Opantsu Misete Moraitai/
└── Season 01/
    └── ...
```

You can process another folder containing Season 02.

The script will merge the new season into the existing anime folder:

```text
~/storage/videos/Anime/Iya na Kao sare nagara Opantsu Misete Moraitai/
├── Season 01/
│   └── ...
└── Season 02/
    └── ...
```

The existing `Season 01` is preserved.

---

# Renaming an Existing Anime Folder

The script can also rename an anime folder that is already inside `FINISHED_FOLDER_PATH`.

For example, if the existing folder is:

```text
~/storage/videos/Anime/Ichijouma Mankitsugurashi!
```

and you enter:

```text
Anime title: Ichijyoma Mankitsu Gurashi!
```

the script moves the episodes into:

```text
~/storage/videos/Anime/Ichijyoma Mankitsu Gurashi!/
```

The old folder is removed only after the files have been successfully processed.

If the destination already exists, the script merges the contents instead of replacing the existing folder.

---

# Existing Files

The script does not overwrite existing video files.

For example, if:

```text
Season 01/Anime - S01E01.mkv
```

already exists, that file is skipped.

The script will display:

```text
[WARNING] Destination already exists.
  SOURCE : /path/to/source-file.mkv
  DEST   : /path/to/Season 01/Anime - S01E01.mkv
  SKIPPING SOURCE FILE.
```

This prevents accidental overwriting. Source files with destination conflicts are left untouched.

---

# Supported Video Formats

The following extensions are supported:

```text
.mkv
.mp4
.avi
.mov
.wmv
.m4v
.ts
.webm
.flv
```

The search is recursive, so files inside subdirectories are also detected.

---

# Workflow

The overall workflow is:

```text
Start
  │
  ▼
Enter folder name
  │
  ▼
Search SEARCH_PATHS
  │
  ├── No match ──► Error
  │
  ├── One match ─► Continue
  │
  └── Multiple matches
          │
          ▼
       Select folder
          │
          ▼
Enter anime title
          │
          ▼
Enter season
          │
          ▼
Enter season/arc title
          │
          ▼
Find video files
          │
          ▼
Detect season/episode
          │
          ▼
Generate destination filenames
          │
          ├── Normal mode
          │       │
          │       ▼
          │    Execute
          │
          └── --review
                  │
                  ▼
              Show preview
                  │
                  ▼
              Confirmation
                  │
             ┌────┴────┐
             │         │
            Yes        No
             │         │
             ▼         ▼
          Execute    Cancel
             │
             ▼
      Merge destination
             │
             ▼
      Remove old source
             │
             ▼
            Done
```

---

# Recommended Usage

For normal downloads:

```bash
python3 ~/storage/code/jellyfin-organizer
```

For potentially risky operations, such as reorganizing an existing Jellyfin library:

```bash
python3 ~/storage/code/jellyfin-organizer --review
```

Using `--review` is recommended when:

* Renaming an existing anime.
* Moving files between existing seasons.
* Processing a folder that is already inside the Jellyfin library.
* You are unsure how the episode detector will interpret the filenames.

---

# Safety Behavior

The script is designed to avoid accidental data loss:

* Existing destination files are never overwritten.
* Destination conflicts are detected.
* Source folders are only removed when they are empty and safe to delete.
* Existing anime folders are merged rather than replaced.
* `--review` provides a confirmation step before modifying files.
* Empty or invalid inputs are rejected.
* Unsupported files are not processed.

Despite these safeguards, **keep backups of important media before performing large-scale reorganizations**.

## License

This project is licensed under the [MIT License](LICENSE).