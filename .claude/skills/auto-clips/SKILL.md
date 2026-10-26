---
name: auto-clips
description: Fully autonomous clip run for one Daggerheart session, as done by hand for Folge 9. Scouts moments, writes clip scripts and multi-cut EDLs for several clips in both formats (short + mid), cuts, edge-checks, renders and QA-checks them, then stops at the human gate. Use when the user says /auto-clips <stem> [shorts=N mids=M], "mach mir Clips aus der Folge", "Clip-Vorschläge", "wie bei Folge 9".
---

# /auto-clips <stem> [shorts=3 mids=3]

Goal: from one transcript stem to N `short` + M `mid` finished **drafts** in `work/<session>/clips/<id>/out.mp4`, without the user in the loop. Nothing is exported, approved or published (CLAUDE.md hard constraints); the run ends with a list for `/review-clip`.
`$PY` = `PY` from `.env`, from repo root. `S` = session dir `work/<session name>/` (printed by `session.py`). Pre-conditions: transcript exists (else report and stop), consent entries for the roster (render gate: stop and list missing persons, never bypass), `source.mp4` cached or `fetch.py` can download it.
Read first: `knowledge/rules.md`, `learnings/pipeline.md` (at least "Cut ends clip words", "Map shots", "Bleep", "Subtitle timing"), memories (taste: fast emotional reaction cuts, no obscene punchlines, map shots in every clip). In Folge 9 every one of these cost a manual review round; this skill builds them in.

## 1. Scout (as /find-clips steps 1–5)
`session.py`, parallel `clip-scout` per chunk, `candidates.py`. Do not open the board. Wanted pool: ≥ 2× the requested clips, so rejects have a replacement.

## 2. Pick
Rank candidates by score and variety; choose M `mid` arcs and N `short` beats.
- No two clips from the same 3 minutes unless one is the `short` peak of the other `mid` (allowed, rules.md Formats).
- Mix types (funny / epic / roleplay / crit / fail). Drop: rules lookups, out-of-game talk, an obscene payoff (memory "No obscene punchlines"; only mild swears get bleeped), moments needing > 10 s of build-up for a `short`.
- Resolve what the ASR garbles by reading `context.md` / the OKF session summary (Folge 9: "Zebras" = Zebros). Write each clip's `id` (kebab-case slug, German keyword).

## 3. Script each clip (parallel, one `general-purpose` agent per clip, or inline for ≤ 3)
Per clip write `S/scripts/<id>.md` (Folge 9 format: source, format, arc, focus, hook ≤ 6 words without spoiler, table: session time · speaker (corrected) · text · picture). Rules the script must follow:
- `short` 1–4 cuts, ends right on the payoff so it loops, no end card, hook can carry the context. `mid` setup → escalation → payoff, 45–100 s, cold open allowed.
- Cut filler and stutters, never story beats. Keep a player's emotional peak as a short insert on their cam; **cam follows the voice** otherwise. Speaker labels from pnp-crawl are unreliable (player lines absorbed into GM): `person` comes from reading the context, not from the label.
- 1–2 map shots per `mid`, 1 per `short`: `& $PY scripts\mapsheet.py <stem> <start>-<end>` first, skip spans with VTT editor panels, only on narration/scene lines.
- Hook / story reviewer pass before cutting (the Folge 9 reviews found 6–7/10 first drafts): one agent reads the script cold and answers "is the payoff understood without campaign knowledge, what is the weakest second". Apply what it finds; a clip below 6/10 after one revision is dropped and replaced from the pool.

## 4. Exact times (GPU, automatic)
One call for all clips: `& $PY scripts\probe.py <stem> <a1> <b1> <a2> <b2> …` (windows = script spans ±1.5 s, one model load) appended to `S/scripts/probe_<run>.txt` (edgecheck, hearcheck and retime read every `probe*.txt`; retime probes missing cuts itself into `probe_auto.txt`). Whisper word starts run 0.3–0.9 s early: they say which word is where, not where the cut goes. Cut points sit on speech islands: use `edgecheck.py` / `hearcheck.py` (step 5) rather than hand-snapping, and never at "the deepest dip near the last word" (long words have internal dips).
Write `S/scripts/<id>.edl.json`: `{"id","type","format","hook","cuts":[{"start","end","person","cam"?,"card"?,"text","join"?,"bleep"?}]}`. `text` = what is audibly said in that cut (the subtitles come from it), censored form for bleeps. Do **not** write `"lead": 0, "tail": 0` (fetch pads 0.2/0.3 s; zero tails clipped words in every Folge 9 clip). Cam switch inside a line: split at a word boundary, second half `"join": true`.

## 5. Edge checks (per EDL, before any render)
`& $PY scripts\edgecheck.py <stem> <id> --apply` (repeat until no CUT/DROP/END/TIGHT, max 3), then `& $PY scripts\hearcheck.py <stem> <id> --apply`. Procedure and meaning of every level: skill `check-edges`. A `CONNECTED` edge: move the cut to another phrase end or add the following words to `text`, rerun. Residual unresolved edges after two tries → drop that cut if it is not a story beat, else report the clip as "needs human ear" with the `@…s` times.

## 6. Build (per clip, as /cut-clip steps 1–6)
`fetch.py` → `retime.py <stem> <id>` (GPU only for cuts no probe window covers; EDL persons; replaces words.py for EDL clips) → `speaker-checker` only for cuts without `person` → `caption-writer` (pass the EDL hook as preferred hook; German, attribution line) → `meta.json` → `ass.py` → `render.py`. A `CONSENT GATE` exit stops that clip and is reported. Several clips in a row: run the CPU/ffmpeg steps of clip k while words.py of clip k+1 uses the GPU.
Check the `<-- check` lines of `retime.py` (under 60 % of a cut's words heard = subtitle timing interpolated there): re-probe a wider window, or shorten the cut.

## 7. QA (per clip)
`edgecheck.py` + `hearcheck.py` once more on the final EDL (must be clean), then the `qa-checker` agent (frames, subtitle sync, VTT chrome on map shots, safe zones). Fix and re-render at most twice (old `out.mp4` → `out_v<N>.mp4` first), then flag.

## 8. Report and stop
Table per clip: id · format · length · hook · type · QA result · open `@…s` listen points. Plus: what was dropped and why. Next step for the user: `/review-clip <stem> <id>` per clip (human approval). Log surprises in `learnings/pipeline.md`; do not edit `knowledge/rules.md` (use `/learn`).

## Limits
- Both GPU steps (probe, words, hearcheck) are short jobs; run them without asking (user 2026-10-22). Do not start pnp-crawl transcription.
- No auto-publish, no export, no consent bypass, no rules.md edits.
- A run with N+M clips costs real tokens: scouts (Haiku) and checkers are cheap, the clip scripts and the reviewer pass are the expensive part. This is intended: the manual review rounds it replaces were the bigger cost.
