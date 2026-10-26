# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Claude-Code-native workflow turning Daggerheart stream sessions into TikTok clip drafts: 9:16, 1080×1920, H.264/AAC, two formats (knowledge/rules.md): `short` ~8–30 s one beat, loops, no end card; `mid` ~45–100 s story arc, hook overlay 0–3 s, burned word-level subtitles (2–4 words/card, speaker colors), German primary. Claude picks, cuts, subtitles, drafts captions. A human approves and posts.

No external APIs: reasoning happens in skills + Haiku subagents; scripts are deterministic (stdlib + ffmpeg + faster-whisper/yt-dlp from pnp-crawl's env). Background brief: [handoffShortRepo.md](handoffShortRepo.md). Architecture plan: `C:\Users\noahs\.claude\plans\create-a-implementation-architecture-pla-peppy-cook.md`.

## Workflow

```
/find-clips <stem>          adapter + parallel clip-scouts -> candidates.json -> board.html (pick/maybe/skip + notes)
/cut-clip <stem> picks <f>  ingest board feedback (logged as learning) -> cut every pick
/find-clips-yt <url>        STUB: any YouTube video without pnp-crawl transcript (not implemented)
/calibrate-layout <team>    one-time facecam crop boxes -> config/layouts.toml
/cut-clip <stem> <id>       fetch window, words, speaker-check, caption, subs, render -> clips/<id>/out.mp4
                            multi-cut: <id> = scripts/<id>.edl.json (several moments, jump cuts, reaction cams, text cards)
/auto-clips <stem> [shorts=3 mids=3]  autonomous: scout, script, EDL, edge checks, render, QA for several clips in both formats; stops before /review-clip
/check-edges <stem> <id|all> clipped/missing words at cut edges, too-early ending -> lead/tail fixes in the EDL
/review-clip <stem> <id>    QA + HUMAN approve/reject -> knowledge/decisions.jsonl, examples/, out/approved/
/learn                      decisions -> knowledge/proposals/rules-<date>.md (human applies)
```

Subagents (`.claude/agents/`, all `model: haiku`): clip-scout, speaker-checker, caption-writer, qa-checker, rules-distiller.

## Commands

Python = pnp-crawl's env (3.11, has faster-whisper + yt-dlp): `$PY = C:\dev\lindo-lauts-notebook\pnp-crawl\ttrpg_env\Scripts\python.exe`. Run from repo root.

- Self-check: `& $PY scripts\test_core.py` (prints `ok`)
- Scripts: `session.py <stem>`, `candidates.py <stem>`, `board.py <stem> [--open]`, `feedback.py <feedback.json>`, `fetch.py <stem> <id>`, `words.py <stem> <id> [--apply]`, `ass.py <stem> <id>`, `render.py <stem> <id> [--bg self|map|map-teal] [--layout pip|full]` (map shots; default from style.toml = pip: map + speaker card below), `edgecheck.py <stem> <id> [--apply]` (loudness at every EDL cut edge, no GPU), `hearcheck.py <stem> <id> [--apply]` (Whisper hears each cut edge vs. subtitle text, GPU, runs without asking), `retime.py <stem> <id>` (subtitle word times for EDL clips from probe words + speech onsets; probes uncovered cuts itself; replaces words.py for multi-cut), `probe.py <stem> <start> <end> [<start> <end> ...]` (word times for EDL cut points, GPU, one model load), `mapsheet.py <stem> <id|start-end> [--step 3]` (contact sheet of the VTT map region to pick clean `cam: "map"` shots), `dice.py --check` (dice-roll insert: EDL cut `"dice": {hope, fear, adv, mod, total, label}` + `text: ""`, render.py draws it via headless Edge; check = every die face lands up)

## Layout

- `scripts/` pipeline steps; `paths.py` holds all external paths.
- `config/` speakers.toml (colors), layouts.toml (crop boxes), consent.toml (consent register).
- `learnings/` engineering learnings (EN): source quirks, tool gotchas, decisions. **Read before refactoring; add an entry whenever something surprising happens** (format in `learnings/README.md`).
- `knowledge/` clip-taste learnings, git-tracked: rules.md, decisions.jsonl, examples/{approved,rejected}/, proposals/.
- `work/` (gitignored) per-session scratch; `out/approved/` (gitignored) approved mp4 + caption.

## Sources (read-only, never edit)

- `C:\dev\lindo-lauts-notebook\pnp-crawl\transcripts_final\<stem>.json`: segments `start,end,speaker,text`, speaker = `"Person (Character)"`. Source of truth. Stem `<YYYY-MM-DD>_<Team-A|Team-B>_<youtubeId>`.
- Raw transcripts do not persist word timestamps → words.py re-transcribes only the clip window.
- No local video: fetch.py downloads the clip window from `video_url` (own YouTube channel).
- OKF bundle session summaries: `C:\dev\lindo-lauts-notebook\pnp-knowledge\knowledge\bundle\splitter_des_ewigen\sessions\<date>.md`.
- Never read `pnp-crawl\groups\voices.json` (biometric).

## Hard constraints

- No clip exported or uploaded without human approval. No auto-publishing.
- `knowledge/rules.md` changes only as a diff, only after human approval. Never edit its Legal section via /learn.
- render.py consent gate: every session participant needs a valid `config/consent.toml` entry. Never bypass.
- Daggerheart Community Gaming License: attribution, "Daggerheart™ Compatible", no trademark in titles/hooks, no official art/logos. Re-check current wording before first post.
- No voice or face profiles (DSGVO Art. 9, EU AI Act). Crop boxes are layout geometry; identities come from transcript labels or the user.
- Own material only: no third-party music, no Twitch/YouTube logos or watermarks.
- Keep licensing open for monetization: avoid non-commercial weights (e.g. DiariZen CC-BY-NC).

## Deferred

DER/cpWER benchmark (when clip-window speaker fixes exceed ~1 per clip); audio-signal candidate scoring; persisting words in pnp-crawl; OKF write-back; SQLite decision log (>1000 decisions).
