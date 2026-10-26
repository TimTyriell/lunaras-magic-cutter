---
name: review-clip
description: QA and human approval gate for a rendered clip; logs the decision as a learning. Use when the user says /review-clip <stem> <id>, or wants to approve/reject a rendered clip.
---

# /review-clip <stem> <id>

`D` = `work/<stem>/clips/<id>/`. Needs `D/out.mp4`.

0. Edges (multi-cut): `& $PY scripts\edgecheck.py <stem> <id>` and `& $PY scripts\hearcheck.py <stem> <id>`. Any CUT/DROP/END or hearcheck finding = QA FAIL → redo via skill `check-edges` before the human decision. LISTEN items go into step 4 as "listen at @…s" for the human.
1. Frames: duration via ffprobe; extract at 0.5 s, 2 s, 25 %, 50 %, 75 %, end−0.5 s:
   `ffmpeg -v error -y -ss <t> -i D/out.mp4 -frames:v 1 D/frames/f_<t>.png`
   Safe-zone frames at 1 s and 50 % (platform UI bands in red; any hook/subtitle text inside = FAIL):
   `ffmpeg -v error -y -ss <t> -i D/out.mp4 -frames:v 1 -vf "drawbox=y=0:w=iw:h=270:color=red@0.4:t=fill,drawbox=y=1500:w=iw:h=420:color=red@0.4:t=fill,drawbox=x=960:w=120:h=ih:color=red@0.3:t=fill" D/frames/safezone_<t>.png`
2. ffprobe summary: `ffprobe -v error -show_entries stream=codec_name,width,height:format=duration -of compact D/out.mp4`.
3. Spawn `qa-checker` with paths: frames, `D/subs.ass`, `D/meta.json`, `D/shots.json`, `D/words.json`, `knowledge/rules.md`, plus the ffprobe output in the prompt.
4. Show the user: path to `out.mp4` (they watch it), QA checklist, hook, caption + hashtags + attribution, speaker corrections.
5. **Ask for a decision. Never decide yourself.** approve | reject | redo (+ what to change). Ask for a short reason either way — that reason is the learning signal.
6. Log (all verdicts): append one line to `knowledge/decisions.jsonl`:
   `{"ts": "<ISO>", "stem", "id", "window": [start, end], "type", "score", "verdict", "reason", "qa": "PASS|FAIL", "hook", "caption_final", "speaker_fixes": <n>}`
   For approve/reject also write `knowledge/examples/<approved|rejected>/<stem>__<id>.md` (format in `knowledge/examples/README.md`; transcript excerpt from `D/words.json` grouped by person).
7. approve → copy `D/out.mp4` to `out/approved/<stem>__<id>.mp4`; write `out/approved/<stem>__<id>.caption.txt` (caption, hashtags, attribution). Remind: human posts manually; re-check CGL wording before first post.
   redo → apply the requested change (edit meta.json hook / corrections.json / layouts) and rerun the relevant `/cut-clip` steps.
8. Every 5 new decisions since last proposal → suggest `/learn`.
