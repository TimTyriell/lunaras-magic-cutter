# Lunara's Magic Cutter

Claude Code workflow that turns tabletop RPG livestream sessions (Daggerheart) into short-form vertical clip drafts for TikTok (9:16, 1080×1920, H.264/AAC, burned-in word-level subtitles).

Claude does the scouting, selection, cutting plan, subtitles and caption drafts. A human reviews every clip and decides what gets published. Nothing is uploaded automatically.

## How it works

```
/find-clips <session>        parallel scouting per transcript chunk -> candidates -> review board (HTML)
/cut-clip <session> picks    cut and render every approved candidate
/auto-clips <session>        autonomous run: scout, script, cut, edge checks, render, QA
/check-edges <session> <id>  find clipped words or early endings at cut points
/review-clip <session> <id>  QA report and human approve / reject, logged as a learning
/learn                       turn logged decisions into a proposed rules change (human applies)
/calibrate-layout <team>     one-time facecam crop boxes per stream layout
```

- **Skills** (`.claude/skills/`) define each workflow step.
- **Subagents** (`.claude/agents/`, Haiku) handle scouting, speaker checks, captions, QA and rule distillation.
- **Scripts** (`scripts/`) are deterministic steps: ffmpeg rendering, ASS subtitles, edge and speech checks, consent gate.
- **Rules** (`knowledge/rules.md`) are human-curated and changed only through reviewed diffs.

## Requirements

- Windows or Linux, Python 3.11
- ffmpeg and ffprobe on `PATH`
- faster-whisper and yt-dlp (GPU optional, used for word timing and hearing checks)
- Source transcripts and stream VODs from the session pipeline. They are not part of this repository.

Run the self-check from the repository root:

```
python scripts/test_core.py
```

## Constraints

- No clip is exported without human approval.
- Every person in a clip needs a valid consent entry; rendering refuses otherwise.
- Only own material is used: no third-party music, logos or watermarks.
- Daggerheart is used under the Daggerheart Community Gaming License ("Daggerheart™ Compatible" attribution, no trademark in titles or hooks).
- No voice or face profiles are built. Crop boxes are layout geometry only.

## Repository layout

| Path | Contents |
|---|---|
| `scripts/` | Pipeline steps and self-check |
| `.claude/` | Skills, subagents and project settings |
| `config/` | Layout geometry, visual style, subtitle colors |
| `knowledge/` | Clip rules |
| `learnings/` | Engineering notes on source quirks and tool behavior |
| `references/` | Research notes on formats and tooling |
| `assets/` | Dice-roll renderer and vendored Three.js (MIT) |

Private working data (`work/`, `out/`, consent register, reviewed examples) is excluded via `.gitignore`.
