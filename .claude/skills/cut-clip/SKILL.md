---
name: cut-clip
description: Cut and render one candidate clip to a 9:16 TikTok mp4 with word-level subtitles, hook overlay and speaker-following facecam shots. Use when the user says /cut-clip <stem> <id> or picks candidates to cut. Requires candidates.json from /find-clips.
---

# /cut-clip <stem> <id>

`$PY` = `PY` from `.env`. Clip dir `D` = `work/<stem>/clips/<id>/`.
Only for candidates the user picked. Output is a draft; nothing leaves the machine.

0. **Board feedback** (`/cut-clip <stem> picks <feedback.json path>`): `& $PY scripts\feedback.py <path>` logs every verdict to `knowledge/decisions.jsonl` (learning signal), applies window tweaks, prints picked ids. Run steps 1–7 for each pick; respect each pick's note (e.g. hook wish) when prompting caption-writer.
**Multi-cut mode** (storytelling from several moments): if `work/<session>/scripts/<id>.edl.json` exists, `<id>` is the EDL id, not a candidate. EDL = `{"id","type","format","hook","cuts":[{"start","end","person","cam"?,"card"?,"text"}]}`, session seconds, in playback order. `person` = speaker (hand-corrected, wins over pnp-crawl labels), `cam` = facecam to show (reaction shot), `card` = text overlay at cut start. `format` = `short` | `mid` (rules.md Formats; `short` renders without end card so it loops, also for single-window candidates). Optional `endcard_audio: 0` = silent end card. Write the EDL from a clip script (`scripts/<id>.md`); length follows the story (rules.md), cut filler not story beats. Steps below stay the same: fetch downloads each cut and joins them, words uses EDL persons, render cuts one shot per EDL cut. speaker-checker only matters for cuts without `person`. caption-writer: pass the EDL hook as preferred hook.
**Map shots** (user wish, 2026-10-21): give every clip 1–2 cuts with `"cam": "map"` (shorts: 1; pip = VTT map on top + the cut's `person` as speaker card below) so the screen switches away from a single face. Pick them with `& $PY scripts\mapsheet.py <stem> <id>` (contact sheet of the map region; skip spans where the VTT editor panels are open), put them on narration / scene-setting / chat read-out lines where the map shows what is said, keep faces for punchline and emotion. Switch mid-line by splitting a cut at a word boundary and marking the second half `"join": true`. Details: learnings/pipeline.md "Map shots in every clip".

0b. **Edges** (multi-cut): after every EDL change, before fetch: `& $PY scripts\edgecheck.py <stem> <id> --apply`, then `& $PY scripts\hearcheck.py <stem> <id> --apply` (Whisper hears each edge, GPU, no need to ask). Only CONNECTED edges need a manual cut move (skill `check-edges`). Do not write `"lead": 0, "tail": 0` by default: fetch pads 0.2/0.3 s, edgecheck sets per-cut values (Folge 9: zero tails on silencedetect -35 dB ends clipped words in every clip). Never set a cut end at "the deepest RMS dip near the last word": long words have internal dips ("Verdamm|nis"), the cut lands inside the word. End cuts at a real pause and keep every cut >= ~0.6 s of speech: cuts inside connected speech come back from hearcheck as CONNECTED and need a manual move.
1. **Fetch** `& $PY scripts\fetch.py <stem> <id>` → `D/src.mp4` (window ±2 s), `D/window.json`.
   On failure: report the yt-dlp error, stop. (Fallback = full download, ask user first.)
2. **Words** single-window: `& $PY scripts\words.py <stem> <id>` → `D/words.json` (GPU, ~10–30 s). Multi-cut (EDL): `& $PY scripts\retime.py <stem> <id>` instead (probe words snapped to speech onsets, probes uncovered cuts itself; words.py is 0.3–0.8 s off on jump cuts). Watch for `<-- check` lines: under 60 % of a cut's words heard.
3. **Speakers** spawn `speaker-checker` with paths: `D/words.json`, `work/<stem>/context.md`, `work/<stem>/segments.json` (tell it the window `t0`/`t1` from window.json to find surrounding lines).
   Write its JSON to `D/corrections.json`. If corrections non-empty: `& $PY scripts\words.py <stem> <id> --apply`.
4. **Caption** spawn `caption-writer` with paths: `D/words.json`, `D/window.json`, `work/<stem>/context.md`, `knowledge/rules.md`, approved examples.
   Write `D/meta.json` = its JSON + `"speaker_check": <corrections.json content>`.
5. **Subs** `& $PY scripts\ass.py <stem> <id>` → `D/subs.ass`.
6. **Render** `& $PY scripts\render.py <stem> <id>` → `D/out.mp4`, `D/shots.json`.
   Exit message `CONSENT GATE` → stop, tell user which persons need entries in `config/consent.toml`. Never bypass.
   If `config/layouts.toml` has no boxes for the team, all shots are wide; suggest `/calibrate-layout <team>`.
7. Report: path to `out.mp4`, length, shot list (person + seconds), hook, caption, speaker corrections. Next: `/review-clip <stem> <id>`.
