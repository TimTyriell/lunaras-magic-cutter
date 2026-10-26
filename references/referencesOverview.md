# References overview: what to test for our pipeline

Short version of [video-tools.md](video-tools.md) (full list, sources and discovery methods). Data as of 2026-10-18.

Platform and audience evidence for clip decisions (signals, length, safe zones, TTRPG reach): [short-form-research.md](short-form-research.md), as of 2026-10-20.

## Verdict

Our design already matches the mainstream 2026 approach:
- transcript-first clip scouting by LLM
- word-level ASS subtitles
- layout-box facecam crop
- deterministic ffmpeg render
- human approval gate

**Don't replace the pipeline. Borrow single pieces where a tool is better at one step.** Every pick below is MIT / Apache / BSD / Unlicense and runs locally.

## Test list (in order)

| # | Tool | Stage | What to test | Keep if | Cost |
|---|---|---|---|---|---|
| 1 | [Kein-chronicle/ffmpeg-video-qa-gates](https://github.com/Kein-chronicle/ffmpeg-video-qa-gates) (MIT, new, 0★) | `/review-clip` | Run its gates on 2–3 rendered `out.mp4`: frozen frames, dead air, loudness, true peak, busy opening, subtitle timing | It catches a real defect that `qa-checker` misses, or the check logic is worth porting as a deterministic pre-check | CPU, minutes. Tiny repo: read the code first or port the checks. |
| 2 | [kajisho5/ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill) (MIT, 1,988★) | `render.py` | Compare its reframe, caption, loudness and TikTok export presets with our filtergraph (`crop` → `FIT` → `ass` → `loudnorm I=-14`) | Better export settings or a cleaner tool contract to copy | CPU, read + 1 render |
| 3 | [WyattBlue/auto-editor](https://github.com/WyattBlue/auto-editor) (Unlicense, 5,552★) | between `words.py` and `render.py` | Tighten dead air inside a 20–60 s clip window; compare pacing before and after | Clips feel tighter and subtitles stay in sync after cuts | CPU. Cuts shift word timings, so `ass.py` would have to remap them. |
| 4 | [m-bain/whisperX](https://github.com/m-bain/whisperX) (BSD-2, 24,653★) | `words.py` | Word alignment only (no diarisation) on the same window as faster-whisper large-v3; compare word-boundary drift on cards | Visibly tighter subtitle cards on fast German crosstalk | **GPU. Ask the user before running.** Diarisation pulls in pyannote models: skip it (consent and voice-profile constraints). |
| 5 | [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) (Apache-2.0, 66,655★) | hook overlay 0–3 s | Render one hook card as HTML → transparent video and overlay it in ffmpeg | Hook looks clearly better than the ASS hook and the render stays deterministic | Adds Node + Chromium. Only worth it if hooks matter for retention. |

## Read-only design study (no install)

| Repo | Look at | Why |
|---|---|---|
| [browser-use/video-use](https://github.com/browser-use/video-use) (MIT, 29,272★) | SKILL.md, `helpers/`, cut-list format, self-evaluation at each cut boundary, `project.md` session memory | Most-used Claude-native editor. Its "self-check before showing the human" step would fit `/cut-clip`. Skip its ElevenLabs speech-to-text. |
| [modelscope/FunClip](https://github.com/modelscope/FunClip) (MIT, 6,418★) | LLM clip-selection prompt and output schema | Compare with the `clip-scout` prompt and `candidates.json`. |
| [bradautomates/claude-video](https://github.com/bradautomates/claude-video) (MIT, 18,772★) | Frame-sampling plus transcript hand-off to Claude | `qa-checker` already does frames + subs. Only take the sampling density if better. |
| [kurbaitaev/ghost-editor](https://github.com/kurbaitaev/ghost-editor) (MIT, 73★) | "Face-safe captions" placement logic | Our subtitles must not cover facecam crops. Compare with `layouts.toml` boxes. |
| [calesthio/OpenMontage](https://github.com/calesthio/OpenMontage) (AGPL-3.0, 69,505★) | Agent guide, spec-checked stages | Best multi-agent design reference. **AGPL: ideas only, no code.** |
| [GVCLab/CutClaw](https://github.com/GVCLab/CutClaw) (no licence, 987★) | Reviewer-agent role | Pattern for a reviewer agent before render. No licence: ideas only. |

## Don't adopt

- **Hosted clippers and vendor MCPs** (OpusClip-style SaaS, Vugola, Katto, ClipSpeed): cloud API, which our no-external-API rule forbids.
- **Remotion and remotion-dev/skills**: licence is "Other" or missing, and it adds a React stack. HyperFrames covers the same need under Apache-2.0.
- **AGPL / GPL editors** (OpenChatCut, supoclip, VideoSeek, ArcReel, Velorn, palmier-pro): copyleft. Patterns only.
- **Generative video and B-roll** (MoneyPrinterTurbo, OpenCreator, video generators): not our use case, and Daggerheart licence risk with generated art.
- **Full GUI editors** (OpenCut, FilmCraft, Clypra): manual editing, nothing for an automated pipeline.

## Next step

1. Tests 1–3 (CPU only) can start now.
2. Test 4 needs a GPU run, so it waits for your go.
3. Log any surprise in `learnings/` as usual.
