---
name: check-edges
description: Review cut edges for clipped audio - a word the subtitles/caption show is cut off or missing in the sound, or the clip ends too early. Use when the user says /check-edges <stem> <id|all>, "Ton abgeschnitten", "Wort fehlt", "Schluss zu früh", and as a gate in /cut-clip and /review-clip for multi-cut (EDL) clips.
---

# /check-edges <stem> <id|all>

`$PY` = `PY` from `.env`, run from `scripts\`. `all` = every `work/<session>/scripts/<id>.edl.json`.
Why: subtitles come from the EDL text, the sound from the cut points. A wrong cut point shows a card nobody hears (Folge 9: "Sag das bitte niemandem." without "niemandem"; the clip ending on "Verdamm-"). Pattern and numbers: learnings/pipeline.md "Cut ends clip words" and "Hear-check".

Two checks, they cover different failures. Run both, in this order:
- `edgecheck.py` (loudness, no GPU): word tails fading out at a pause (Whisper misses those: "erkennt" decays 0.56 s past the cut, Whisper still hears the word), too little room, the 0.5 s settle at the end of the clip.
- `hearcheck.py` (Whisper large-v3, GPU, runs without asking, user 2026-10-22): connected speech without a pause, where edgecheck can only say LISTEN. It transcribes the first/last 3 s of exactly the audio the clip plays and compares with the EDL text: MISSING / TRUNC (fragment) / EXTRA (next phrase leaks in).

1. **Ask** before touching clips: check `HANDOFF.md` ("nicht anfassen") and EDL mtimes (another session may be editing).
2. **Fix** per clip:
   `& $PY edgecheck.py <stem> <id> --apply` (repeat until it reports no CUT/DROP/END/TIGHT, max 3 passes)
   `& $PY hearcheck.py <stem> <id> --apply`
   Both write lead/tail into the EDL (old EDL → `.edl.v<N>.json`).
3. **Rebuild**: `fetch.py` → `retime.py <stem> <id>` (repo script; probes cuts no probe window covers, snaps subtitle starts to speech onsets) → `ass.py` → `render.py` (copy the old `out.mp4` to the next `out_v<N>.mp4` first).
4. **Re-check** both scripts. Done when hearcheck reports `0 hard`. hearcheck levels: `FIX` (extends the edge, with --apply), `HARD` (CONNECTED: no clean edge within 1 s), `NOTE` (listen-only: leaked/misheard word, an edge that edgecheck finds clean, a lone-word cut Whisper cannot hear, or words inside a cut that differ from the subtitles - fix the EDL text). NOTEs do not block; list them in the report. An edgecheck LISTEN at an edge that hearcheck hears clean needs no human.
5. **Left for the human** only:
   - hearcheck `HARD` (CONNECTED): no clean cut within 1 s, the next phrase follows without a gap. Move the cut to another phrase end in the EDL (or add the following words to `text`), then repeat 2-4. Never extend into obscene words (memory "No obscene punchlines").
   - edgecheck `LISTEN` "text ends mid-sentence" / "ending: next sound …": story decision about the last line.
   Report these with their `@…s` out.mp4 times.
6. A new failure kind or a wrong fix → entry in `learnings/pipeline.md`, tune the constants at the top of the script, keep `test_core.py` passing.
