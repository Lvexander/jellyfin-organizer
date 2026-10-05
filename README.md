# Jellyfin Anime/Movie/TV Shows Organizer

A Python script for organizing downloaded anime, movies, and TV show video files into a Jellyfin-compatible folder structure.

Show title, release year, and season number are resolved automatically from **MyAnimeList** and **TMDB**, so you only enter the folder and a MyAnimeList URL or ID.

The script can:

- Find the source folder by name or by full path.
- Look up the anime on MyAnimeList and work out the season number from its prequel chain.
- Match the anime on TMDB and build a Jellyfin folder name: `Title (Year) [tmdbid-123]`.
- Automatically detect episode numbers.
- Optionally override the season number or the TMDB match.
- Clean release metadata from filenames.
- Rename episodes to a consistent format.
- Merge into an existing anime folder when appropriate.
- Move the completed anime folder to the configured Jellyfin library (can be disabled).
- Automatically execute changes by default.
- Use `--review` to preview changes and require confirmation before execution.

---

## Requirements

- Python 3.10+
- [uv](https://docs.astral.sh/uv/)
- The `requests` library, installed with uv:

```bash
uv add requests
```

If the repository has no `pyproject.toml` yet, run `uv init` first. `uv sync` installs the dependencies on a fresh clone.

- A MyAnimeList API client ID
- A TMDB API key
- Internet access (the script calls both APIs)

---

## Configuration

The repository includes a `.env.example` file containing the required configuration.

Copy it to `.env`:

```bash
cp .env.example .env
```

### `MAL_CLIENT_ID`

Your MyAnimeList API client ID. Create one at <https://myanimelist.net/apiconfig>.

### `TMDB_API_KEY`

Your TMDB API key. Get one at <https://www.themoviedb.org/settings/api>.

Both keys are required. The script exits with an error if either is missing.

### `FINISHED_FOLDER_PATH`

This is the root directory where organized anime folders are stored.

For example:

```text
~/storage/videos/Anime
```

The script will create:

```text
~/storage/videos/Anime/
└── Anime Title (2023) [tmdbid-123456]/
    ├── Season 01/
    │   ├── Anime Title (2023) - S01E01.mkv
    │   └── Anime Title (2023) - S01E02.mkv
    └── Season 02/
        └── Anime Title (2023) - S02E01.mkv
```

### `SEARCH_PATHS`

This defines the directories where the script searches for the folder you want to organize.

For example:

```env
SEARCH_PATHS=~/shared,~/jellyfin
```

If you enter:

```text
Folder name or full path: Sousou no Frieren
```

the script searches those locations recursively for an **exact folder name**:

```text
/home/levi/storage/downloads/Sousou no Frieren
/home/levi/Downloads/Sousou no Frieren
...
```

If multiple matching folders are found, the script asks you to select which one to process.

### Example `.env`

```env
FINISHED_FOLDER_PATH=~/storage/videos/Anime
SEARCH_PATHS=~/shared,~/jellyfin
MAL_CLIENT_ID=your_mal_client_id
TMDB_API_KEY=your_tmdb_api_key
```

---

## Usage

### Normal mode

From the repository directory, run:

```bash
uv run main.py
```

To run it from anywhere, use `--project` (or put it in a shell alias):

```bash
uv run --project ~/storage/code/jellyfin-organizer ~/storage/code/jellyfin-organizer/main.py
```

The script will interactively ask:

```text
Folder name or full path: Sousou no Frieren

Searching for exact folder name: Sousou no Frieren

Found: /home/levi/storage/downloads/Sousou no Frieren

MyAnimeList URL or ID: https://myanimelist.net/anime/52991/Sousou_no_Frieren

Fetching metadata...
```

The operation is then executed automatically.

### Command-line options

| Option | Description |
| --- | --- |
| `--review` | Show a preview and ask for confirmation before changing anything. |
| `--season N` | Use season `N` instead of the season detected from MyAnimeList. |
| `--tmdb-id ID` | Use this TMDB TV show ID instead of searching TMDB. |
| `--no-move` | Do not move the result to `FINISHED_FOLDER_PATH`. |

Examples:

```bash
uv run main.py --review
uv run main.py --review --tmdb-id 209867
uv run main.py --season 2 --no-move
```

---

## Review Mode

Use `--review` when you want to see the planned changes before anything is modified:

```bash
uv run main.py --review
```

In review mode, the script:

1. Finds the source folder.
2. Looks up MyAnimeList and TMDB.
3. Shows the matched metadata (MAL entry, TMDB match, season).
4. Detects the video files.
5. Shows the planned rename/move operations.
6. Shows the destination.
7. Asks for confirmation.
8. Only executes the operation if you answer `y`.

The metadata block looks like this:

```text
======================================================================
METADATA
======================================================================
MAL    : Grand Blue Season 3 (id 62542, tv)
TMDB   : Grand Blue -> Grand Blue (2018) [tmdbid-78203]
SEASON : 3 (MAL prequel chain)

If the TMDB match is wrong, answer N and rerun with --tmdb-id.
```

Confirmation prompt:

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

## Folder Name or Full Path

You can enter either the folder name or its path.

**Folder name**: the script searches `SEARCH_PATHS` for an exact match:

```text
Folder name or full path: Frieren
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

**Full or relative path**: used directly, no search. Any input containing `/` or starting with `~` or `.` is treated as a path:

```text
Folder name or full path: ~/storage/downloads/Sousou no Frieren
```

Surrounding quotes (for example, pasted from `ls` output) are ignored.

---

## MyAnimeList URL or ID

Enter either a MyAnimeList URL or the numeric ID:

```text
MyAnimeList URL or ID: https://myanimelist.net/anime/62542/Grand_Blue_Season_3
```

or:

```text
MyAnimeList URL or ID: 62542
```

Use the MAL entry of the **season you are organizing**, not the first season. The script finds the first season itself.

---

# How Title and Season Are Resolved

## Season number

The script follows the MyAnimeList **prequel** relations back to the first season.

- The season number is the number of `tv` and `ona` entries in that chain, including the entry you entered.
- Movies, OVAs, and specials in the chain are passed through but not counted.
- If the entered entry is not `tv`/`ona` (for example a movie or OVA), the season is `0`.

For example, `Grand Blue Season 3` → `Grand Blue Season 2` → `Grand Blue` gives season `3`.

The season from MyAnimeList **overrides** any season found in the filename (for example, files named `S01E05` in a Season 3 folder are renamed to `S03E05`). Files detected as specials, and files that explicitly say `S00`, stay in Season 0.

## Title and year

The first season's titles (English, then default, then Japanese) are searched on TMDB. If there are several results, the first of the top five whose first air date year matches the MyAnimeList start year is used. Otherwise the top result is used.

The result is turned into:

| Item | Format | Example |
| --- | --- | --- |
| Folder | `Title (Year) [tmdbid-ID]` | `Grand Blue (2018) [tmdbid-78203]` |
| Season folder | `Season NN` | `Season 03` |
| File | `Title (Year) - SxxExx.ext` | `Grand Blue (2018) - S03E01.mkv` |

Colons in titles are replaced with ` - ` and characters that are invalid in filenames are removed, while hyphens are kept:

```text
Kaguya-sama: Love Is War  →  Kaguya-sama - Love Is War
```

## Fixing a wrong result

- **Wrong TMDB match**: find the correct show on TMDB and rerun with `--tmdb-id <id>`.
- **Wrong season**: rerun with `--season N`. MyAnimeList and TMDB can number seasons differently (for example split cours or long-running shows).

Use `--review` so you can check the match before anything is moved.

---

# Season 0 (Specials)

Season `0` is used for specials/OVAs. Those files are placed in a folder named:

```text
Anime Title (Year) [tmdbid-123456]/
└── Season/
    └── Anime Title (Year) - S00E01.mkv
```

The folder name is `Season`, but the filename still uses Jellyfin-style `S00E##` numbering.

---

# Episode Detection

The script supports several common filename formats.

### S01E01

```text
Anime S01E01.mkv
```

becomes:

```text
Anime (Year) - S01E01.mkv
```

An explicit `SxxExx` tag always wins over keywords such as `Movie` or `Special` appearing in the title. The season number itself is then replaced by the one resolved from MyAnimeList (see above).

### E01

```text
Anime E01.mkv
```

becomes:

```text
Anime (Year) - S01E01.mkv
```

### EP01

```text
Anime EP01.mkv
```

becomes:

```text
Anime (Year) - S01E01.mkv
```

### Episode 01

```text
Anime Episode 01.mkv
```

becomes:

```text
Anime (Year) - S01E01.mkv
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

Filenames containing `OVA`, `Movie`, or `Special` (and no `SxxExx` tag) are treated as season `0` specials.

They are placed in the specials folder:

```text
Anime Title (Year) [tmdbid-123456]/
└── Season/
    ├── Anime Title (Year) - S00E01.mkv
    └── Anime Title (Year) - S00E02.mkv
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
~/storage/videos/Anime/Grand Blue (2018) [tmdbid-78203]/
└── Season 01/
    └── ...
```

You can process another folder containing Season 02, entering the MyAnimeList ID of Season 2.

The script will merge the new season into the existing anime folder:

```text
~/storage/videos/Anime/Grand Blue (2018) [tmdbid-78203]/
├── Season 01/
│   └── ...
└── Season 02/
    └── ...
```

The existing `Season 01` is preserved.

Merging works because every season of the same show resolves to the **same TMDB title, year, and ID**, and therefore the same folder name. Existing library folders that were named without `[tmdbid-...]` will not be merged automatically; they are treated as different folders.

---

# Renaming an Existing Anime Folder

The script can also rename an anime folder that is already inside `FINISHED_FOLDER_PATH`.

For example, if the existing folder is:

```text
~/storage/videos/Anime/Grand Blue Dreaming
```

enter its path (or name) and the MyAnimeList ID of the season it contains. The script moves the episodes into:

```text
~/storage/videos/Anime/Grand Blue (2018) [tmdbid-78203]/
```

The old folder is removed only after the files have been successfully processed.

If the destination already exists, the script merges the contents instead of replacing the existing folder.

If the folder holds several seasons, run the script once per season with the matching MyAnimeList ID.

---

# Existing Files

The script does not overwrite existing video files.

For example, if:

```text
Season 01/Anime (Year) - S01E01.mkv
```

already exists, that file is skipped.

The script will display:

```text
[WARNING] Destination already exists.
  SOURCE : /path/to/source-file.mkv
  DEST   : /path/to/Season 01/Anime (Year) - S01E01.mkv
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

Subtitle and other non-video files are not processed.

---

# Workflow

The overall workflow is:

```text
Start
  │
  ▼
Enter folder name or path
  │
  ├── Path ──────► Use directly
  │
  └── Name ──────► Search SEARCH_PATHS
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
Enter MyAnimeList URL or ID
  │
  ▼
Fetch MAL prequel chain ──► season number
  │
  ▼
Search TMDB ──► title, year, ID
  │
  ▼
Find video files
  │
  ▼
Detect episode numbers
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
      Show metadata + preview
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
Remove empty source
     │
     ▼
Move/merge into FINISHED_FOLDER_PATH
(skipped with --no-move)
     │
     ▼
    Done
```

---

# Recommended Usage

Anime titles are matched automatically, so a wrong TMDB match is possible. **`--review` is recommended** so you can check the metadata before anything is moved:

```bash
uv run main.py --review
```

Without `--review`, the changes run immediately and you do not get a chance to check the match.

Using `--review` is especially recommended when:

* Organizing a title for the first time.
* Renaming an existing anime.
* Moving files between existing seasons.
* Processing a folder that is already inside the Jellyfin library.
* The show has split cours, many seasons, or unusual season numbering.
* You are unsure how the episode detector will interpret the filenames.

Use `--no-move` if you only want to rename and keep the result next to the source folder.

---

# Safety Behavior

The script is designed to avoid accidental data loss:

* Existing destination files are never overwritten.
* Destination conflicts are detected.
* Source folders are only removed when they are empty and safe to delete.
* Existing anime folders are merged rather than replaced.
* `--review` provides a confirmation step before modifying files.
* Invalid inputs are rejected (empty folder, invalid MyAnimeList URL/ID).
* Unsupported files are not processed.
* API errors are reported without printing your API keys.

Despite these safeguards, **keep backups of important media before performing large-scale reorganizations**.

## License

This project is licensed under the [MIT License](LICENSE).