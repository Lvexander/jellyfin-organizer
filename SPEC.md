# Jellyfin Organizer Refactor Specification

## Goal

Refactor the current single-file organizer into a maintainable application that can support:

1. Rule-based organizing for anime, movies, TV shows, and manual workflows.
2. A safe `plan -> review -> execute` operation model.
3. Future Rust UI for human workflows.
4. Future Docker/API service for automated workflows.
5. Optional low-cost/local agent assistance for ambiguous cases, without making AI required.

The first implementation phase should be small and iterative. The current behavior should continue working while the internals are separated into modules.

---

## Core Product Concept

The organizer should not directly rename/move files as it discovers them.

Instead, every workflow should follow this shape:

```text
Input source files/folders
        |
        v
Selected rule + user/API variables
        |
        v
Generate operation plan
        |
        v
Review plan / detect conflicts
        |
        v
Execute safe operations
```

A plan item should describe one intended filesystem operation:

```json
{
  "source": "/downloads/Frieren/[Group] Frieren - 01.mkv",
  "destination": "/media/anime/Frieren/Season 01/Frieren - S01E01.mkv",
  "operation": "move",
  "status": "ok",
  "reason": null
}
```

The executor should only perform operations that are safe. Existing destination files must not be overwritten.

---

## Rules

The current script has anime-specific filename detection embedded directly in code. The refactor should move toward user-selectable rules.

Rules may eventually be YAML files, text templates, or UI-created configurations. For phase 1, the existing anime behavior can remain hardcoded behind an internal rule interface.

Future example rule for anime episodes:

```yaml
name: anime-season
media_type: series

variables:
  title: "Sousou no Frieren"
  season: 1

input:
  extensions:
    - mkv
    - mp4

episode:
  strategy: detect-or-ordered
  start: 1

output:
  root: "/media/anime"
  folder: "{{ title }}/Season {{ season | pad2 }}"
  filename: "{{ title }} - S{{ season | pad2 }}E{{ episode | pad2 }}{{ ext }}"
```

Future example rule for movies:

```yaml
name: movie
media_type: movie

variables:
  title: "Dune Part Two"
  year: 2024

input:
  extensions:
    - mkv
    - mp4

output:
  root: "/media/movies"
  folder: "{{ title }} ({{ year }})"
  filename: "{{ title }} ({{ year }}){{ ext }}"
```

Future manual mapping rule:

```yaml
name: manual-map

files:
  - source: "Episode 01.mkv"
    destination: "Frieren/Season 01/Frieren - S01E01.mkv"

  - source: "Episode 02.mkv"
    destination: "Frieren/Season 01/Frieren - S01E02.mkv"
```

---

## Human Workflow

The human workflow should eventually have a Rust UI. The UI should use the same core planner/executor as the CLI and server.

Recommended first UI technology: `egui`/`eframe`.

Expected UI flow:

1. Select source folder or files.
2. Select rule.
3. Fill rule variables, such as:
   - title
   - season
   - year
   - destination root
4. Generate preview plan.
5. Show conflicts and skipped files.
6. Execute the approved plan.

The UI should not implement separate organizing logic. It should call the shared core.

---

## Automated Workflow

The automated workflow should eventually run in Docker and expose an API.

Initial recommendation: REST API before gRPC/MCP because it is simpler to integrate.

Example request:

```http
POST /plans
```

```json
{
  "source": "/downloads/Frieren",
  "rule": "anime-season",
  "variables": {
    "title": "Sousou no Frieren",
    "season": 1,
    "destination_root": "/media/anime"
  },
  "dry_run": true
}
```

Example response:

```json
{
  "plan_id": "abc123",
  "operations": [
    {
      "source": "/downloads/Frieren/01.mkv",
      "destination": "/media/anime/Sousou no Frieren/Season 01/Sousou no Frieren - S01E01.mkv",
      "operation": "move",
      "status": "ok"
    }
  ]
}
```

Execute later:

```http
POST /plans/abc123/execute
```

Possible Docker layout:

```yaml
services:
  jellyfin-organizer:
    image: jellyfin-organizer
    ports:
      - "8080:8080"
    volumes:
      - /downloads:/downloads
      - /media:/media
      - ./rules:/app/rules
```

---

## Agent / LLM Usage

An agent should not be required for normal renaming. Deterministic rules should be the default.

Optional agent assistance can be useful only for ambiguous cases, such as:

- unknown episode numbering
- mixed anime/movie/OVA folders
- confusing release names
- suggesting metadata from filenames

Recommended free/local approach:

- Ollama
- small local models:
  - `qwen2.5:3b`
  - `qwen2.5:7b`
  - `llama3.2:3b`
  - `gemma2:2b`
  - `phi3:mini`

The model should receive only filenames and a small task prompt. It should return JSON suggestions. The user or server policy should still approve the final plan before execution.

---

## Safety Requirements

The refactor must preserve current safety behavior:

- Never overwrite existing destination files.
- Generate preview plans before changes in review/API dry-run mode.
- Keep source files when destination conflicts exist.
- Only remove empty source directories.
- Merge existing destination folders safely.
- Preserve unsupported files.
- Make execution idempotent where possible.

---

## Phase 1 Scope

Phase 1 should not redesign everything.

It should only split the current script into maintainable Python modules while preserving existing CLI behavior.

The most important phase 1 architectural change is introducing explicit planning objects before execution.

Phase 1 deliverable:

```text
Current behavior still works, but the code is separated into modules and filesystem operations are represented as a plan before execution.
```
