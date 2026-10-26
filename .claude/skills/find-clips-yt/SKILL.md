---
name: find-clips-yt
description: NOT IMPLEMENTED (stub). Second input mode - find clip candidates in any YouTube video URL without a pnp-crawl transcript. Use only when the user asks to implement or run "YT mode" / /find-clips-yt <url>; until implemented, tell the user it is a stub.
---

# /find-clips-yt <youtube-url>   — STUB, not implemented

Status: design only. Do not run. If invoked, say it is not implemented and offer to build it.

## Difference to /find-clips
| | /find-clips (session mode) | /find-clips-yt (YT mode) |
|---|---|---|
| Input | pnp-crawl stem | any YouTube URL (own material only) |
| Transcript | `pnp-crawl/transcripts_final` | must create one |
| Speakers | resolved names `Person (Character)` | unknown (`SPEAKER_XX`) or none |
| Context | OKF session file + roster | video title/description only |

## Planned steps
1. Stem: `yt_<videoId>`; `work/yt_<videoId>/`.
2. Audio: `yt-dlp -x --audio-format mp3` (ttrpg_env).
3. Transcript: faster-whisper large-v3 full video, word timestamps kept (`words` per segment).
4. Speakers: optional pyannote 3.1 (needs HF_TOKEN in ttrpg_env); user maps `SPEAKER_XX` -> names once, or skip -> `person = "speaker"` for all.
5. Write `segments.json` + `context.md` + `chunks/` in the same format as `scripts/session.py` → rest of the pipeline (`/find-clips` steps 2–5, board, `/cut-clip`) unchanged.
6. `words.py` can then reuse stored words instead of re-transcribing.

## Open before implementing
- Consent gate: roster unknown → require explicit person list from user for `consent.toml`.
- Layout calibration per channel instead of per team (`layouts.toml` key = `yt_<channel>`).
- `paths.team()` assumes `<date>_<Team>_<id>` stems → needs a mode-aware variant.
