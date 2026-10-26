---
name: find-clips
description: Find TikTok clip candidates in one Daggerheart session. Use when the user says /find-clips <stem>, "find clips", "Kandidaten suchen" for a session. Runs the adapter, fans out Haiku clip-scouts per 15-min chunk, merges to work/<stem>/candidates.json.
---

# /find-clips <stem>

`<stem>` = pnp-crawl transcript stem, e.g. `2026-09-22_Team-A_zXVsTYYR8M4`. List options: `ls <PNP_ROOT>\pnp-crawl\transcripts_final\*.json`.
`$PY` = `PY` from `.env` (run from repo root).

1. `& $PY scripts\session.py <stem>` → `work/<stem>/segments.json`, `context.md`, `chunks/chunk_NN.txt`.
2. Collect example paths: newest ≤5 in `knowledge/examples/approved/`, ≤3 in `rejected/`.
3. Spawn one `clip-scout` agent per chunk, **all in one message (parallel)**. Prompt each with absolute paths: its chunk file, `knowledge/rules.md`, `work/<stem>/context.md`, the example files.
4. Save each scout's JSON array verbatim to `work/<stem>/scouts/chunk_NN.json` (normalize unknown `type` to the nearest allowed one).
5. `& $PY scripts\candidates.py <stem>` → `candidates.json` (20–90 s filter, overlap dedup, ids c01… by score).
6. `& $PY scripts\screens.py <stem>` (3 stills per candidate via stream seek; needs YouTube cookies, see `paths.ytdlp_auth`; on failure skip, board works without).
   `& $PY scripts\board.py <stem> --open` → `work/<stem>/board.html` opens in browser.
7. Show top 10 as table: id · HH:MM:SS · length · type · score · hook_line. Tell user: judge in the board (pick/maybe/skip + note, optional window tweak), click "Feedback exportieren", then give me the file path → `/cut-clip <stem> picks <path>`.

Do not render or download anything here.
