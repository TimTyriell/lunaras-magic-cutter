# Video tool references

Collected 2026-10-18 for the clip pipeline. Stars and dates come from the GitHub API (`gh`) unless marked *search* (seen in a search snippet or directory only, not verified).

Licence column: MIT / Apache-2.0 / BSD are safe to borrow code from. AGPL / GPL = study patterns only, do not copy code. NONE = no licence, do not copy. Other = read terms first.

Project constraints that drive the picks (see CLAUDE.md): local-first, no external APIs, Claude-driven, human approval before publish, monetization-compatible licences.

---

## 1. Discovery channels (how the repos were found)

Tested on 2026-10-18. "Works" means the call returned usable data.

| # | Channel | How to query | Status | Good for | Notes |
|---|---|---|---|---|---|
| 1 | GitHub search (`gh`) | `gh search repos "<q> pushed:>2026-08-01 stars:>20" --sort stars --json fullName,stargazersCount,pushedAt,license,description --jq '...'` | Works | Best recall | Qualifiers `pushed:>`, `stars:>`, `topic:` work. Use `--json` with `--jq`. Rate limit: about 15 rapid queries then 403. Pace 2–4 s. |
| 2 | GitHub topics | `gh search repos --topic video-editing --sort updated` | Works | Recent activity | Noisy. Topics `video-editing`, `ffmpeg`, `short-video`, `claude-code-skill`, `mcp-server` all returned hits. |
| 3 | GitHub GraphQL batch | `gh api graphql -f query='query{ r1: repository(owner:"X",name:"Y"){ stargazerCount pushedAt licenseInfo{name} } ... }'` | Works | Verifying 40+ repos in one call | Missing repos return `NOT_FOUND` for that alias only; the rest still come back. |
| 4 | Awesome lists (mine the README) | `gh api repos/O/R/readme -q .content \| base64 -d \| grep -oE 'https://github.com/[^ )]+'` | Works | Curated coverage | Best lists below. Mining finds links the search misses. |
| 5 | GitHub Trending | `WebFetch https://github.com/trending?since=weekly` | Works | Week's momentum | Little video this week (only HyperFrames). |
| 6 | Auto-updated Claude-skill leaderboard | `https://github.com/linny006/trending-claude-skills` (refreshes about every 15 min) | Works | Momentum in Claude skills | Ranks by momentum, not stars. Top 10 had no video repos. |
| 7 | Skill registry (skills.sh, Vercel) | `WebFetch https://skills.sh/` | Works | Demand signal (install counts) | Ranked by installs. No star counts. Strong video entries: `remotion-best-practices` (639.5k installs), HyperFrames family, `video-edit` (runcomfy, 436k). |
| 8 | Claude marketplace directory | `WebFetch https://claudemarketplaces.com/skills/<owner>/<repo>/<skill>` | Works | Per-skill installs and stars, first-seen date | No ranked leaderboard found. Category pages exist. Ad-heavy. |
| 9 | npm registry search | `WebFetch https://registry.npmjs.org/-/v1/search?text=ffmpeg%20mcp&size=25` | Works | Weekly downloads (demand) | Found `ffmpeg-skill` (about 2k/wk), `@hyperframes/engine` (about 85k/wk), `claude-skills-library` (about 1.8k/wk). |
| 10 | MCP directory (Glama) | `WebFetch https://glama.ai/mcp/servers?query=ffmpeg` | Works | Breadth of ffmpeg MCP servers | Mostly small repos (under 30 stars). "Load More" paginates. |
| 11 | PyPI search | `WebFetch https://pypi.org/search/?q=...` | Fails (JS page) | — | Use per-package JSON (`https://pypi.org/pypi/<name>/json`) instead. Not tested here. |
| 12 | Hacker News (Algolia API) | `WebFetch https://hn.algolia.com/api/v1/search_by_date?query=<q>&tags=story&hitsPerPage=40` | Works | Fresh "Show HN" launches | Good for repos launched in the last weeks. Points = early signal. Results truncate around 100k chars, so page with `offset`. |
| 13 | Product Hunt | `WebSearch` with `allowed_domains: ["producthunt.com"]` | Works | Launches and maker pages | Maker-reported claims. |
| 14 | dev.to | `WebSearch` with `allowed_domains: ["dev.to"]` | Works | Build-log tutorials, some repo links | Mixed quality. |
| 15 | Medium | `WebSearch` with `allowed_domains: ["medium.com"]` | Search works; article fetch returns 403 | Roundups | Use snippets only. |
| 16 | YouTube | `WebSearch` with `allowed_domains: ["youtube.com"]` | Works | Tutorials that name a repo | Repo links live in video descriptions, which search does not show. Treat as leads. |
| 17 | Reddit | — | Blocked (WebSearch refuses the domain, WebFetch fails) | — | Not available with these tools. |
| 18 | LinkedIn | `WebSearch` with `allowed_domains: ["linkedin.com"]` | Works, very noisy | — | Mostly OpusClip company and promo posts. Low value. |
| 19 | Official Anthropic catalog | `gh api repos/anthropics/claude-plugins-official/contents/plugins` and `.../external_plugins` | Checked | Official plugins | No video plugin in either folder. |
| 20 | Multi-agent search | `gh search` plus WebSearch | Partly rate-limited earlier | Multi-agent video repos | Coverage is thinner than the single-agent side. |

**Recipe (repeat monthly):**
1. Run channel 1 with 4–6 queries (video editing agent, shorts clipper, ffmpeg mcp, remotion skill, talking head, multi-agent video) and `pushed:>` set to 90 days back.
2. Mine the awesome lists in section 2 (channel 4) for links not yet in section 3.
3. Check the Show HN feed (channel 12) for launches in the last 30 days.
4. Use channels 7, 8 and 9 as demand checks: installs and weekly downloads separate real use from stars.
5. Verify the shortlist with GraphQL (channel 3): licence, pushedAt, stars.

**Quality heuristics (my judgement, not validated):**
- Pushed in the last 90 days.
- Licence MIT / Apache / BSD for code reuse.
- README shows install steps and a demo.
- 100+ stars, or a Show HN launch with a working demo and recent commits.
- Demand signal from channel 7 or 9 when available.

---

## 2. Curated lists (start here)

| List | ★ | Last push | Use |
|---|---|---|---|
| hesreallyhim/awesome-claude-code | 55,961 | 2026-10-18 | Claude Code resources, huge |
| ComposioHQ/awesome-claude-skills | 77,389 | 2026-09-18 | Claude skills |
| punkpeye/awesome-mcp-servers | 96,566 | 2026-10-18 | MCP servers (few video hits) |
| VoltAgent/awesome-claude-code-subagents | 25,832 | 2026-10-11 | Subagent patterns |
| ccplugins/awesome-claude-code-plugins | 977 | 2026-08-12 | Plugins |
| transitive-bullshit/awesome-ffmpeg | 1,195 | 2026-09-18 | ffmpeg tooling |
| devanasolver/awesome-video-editing | 2 | 2026-10-17 | Video editing tools, agent skills, assets (the best video-specific list) |
| krzemienski/awesome-video | 1,929 | 2026-07-20 | Streaming video |
| Supersynergy/awesome-ai-video-editing | 4 | 2026-07-31 | AI video editing, agent-native focus |

---

## 3. Tools by category

### 3a. Claude / agent-native editing (skills, MCP, agent-driven)

| Repo | ★ | Pushed | Licence | What it is | Local? | Notes |
|---|---|---|---|---|---|---|
| browser-use/video-use | 29,272 | 2026-10-08 | MIT | Claude Code skill: drop footage in a folder, chat, get final.mp4. Filler cuts, colour, subtitles, parallel animation sub-agents, self-check | Partial | Speech-to-text uses ElevenLabs (paid cloud). Swap for faster-whisper to stay local. |
| calesthio/OpenMontage | 69,505 | 2026-10-16 | AGPL-3.0 | Agentic production system: 12 pipelines, 100+ tools, works with Claude Code / Cursor / Codex | Partial | Strongest multi-agent reference. AGPL: study the design, do not copy code. |
| kajisho5/ffmpeg-skill | 1,988 | 2026-10-17 | MIT | Local video editor for coding agents: 42 FFmpeg tools with a machine-readable contract, MCP server. Cut, captions, reframe, loudness, platform exports | Yes | No cloud, no API keys. Closest to our local-first constraint. |
| bradautomates/claude-video | 18,772 | 2026-09-25 | MIT | `/watch`: downloads a video, extracts frames, transcribes, gives all to Claude | Yes | Use for QA: Claude watches a rendered clip. |
| Vincentwei1021/video-shotcraft | 12,385 | 2026-10-17 | Apache-2.0 | Claude Code and Codex skill: product videos with Remotion, 152 shot recipes | Yes | Hook-overlay and motion-graphics reference. |
| veedstudio/open-edit | 1,684 | 2026-10-07 | Apache-2.0 | Agent-driven editing pipeline: subtitles, motion graphics, slides | Partial | Check its external calls. |
| KyaniteLabs/kinocut | 210 | 2026-10-17 | Apache-2.0 | Guardrailed video-editing MCP server for agents over FFmpeg, Hyperframes, repurposing | Yes | Guardrails match the approval gate. |
| kurbaitaev/ghost-editor | 73 | 2026-10-14 | MIT | AI editor for talking-head reels: 7 styles, face-safe captions, motion scenes | Partial | Closest to our talking-head streams. Verify before use. |
| kevinbadi/open-edits | 42 | 2026-10-02 | MIT | Claude Code skills: raw talking-head clip → animated short | Partial | Newer, small. |
| howseen-ai/claude-motion-design | 574 | 2026-10-04 | MIT | Claude skill: motion design in code (HTML + Playwright + ffmpeg) | Yes | |
| haidrrrry/claude-remotion-skill | 521 | 2026-08-12 | MIT | Claude skill that teaches Claude Code / Desktop to create and edit Remotion videos | Yes | |
| remotion-dev/skills | 5,328 | 2026-10-16 | NONE | Official Remotion agent skills | Yes | No licence on the repo. Do not copy. |
| WhiteTowerAI/cut-as-code | 16 | 2026-10-07 | MIT | Agentic editing skills, pitched as an Opus Clip / CapCut alternative | Partial | |
| kmilo93sd/agent-video-editor | 6 | 2026-10-04 | MIT | Editing judgement for agents: pacing, cuts, captions, audio, colour | Yes | Small. |
| konradre/video-production-skills | 7 | 2026-10-10 | MIT | Agent skills: pre-production, cost-gated generation | Partial | |
| krusemediallc/video-editor-agent | 36 | 2026-10-17 | NONE | Claude Code skill pack for short-form editing end to end | Partial | No licence. |
| mutonby/openshorts-plugin | 1 | 2026-10-17 | MIT | Claude plugin for OpenShorts | Partial | Companion to OpenShorts. |
| vinit-agr/videopowers | 2 | 2026-09-22 | MIT | Factory for YouTube videos with Claude Code | Yes | Small. |
| mortenbrudvik/always-allow | 14 | 2026-10-13 | MIT | Production record of a music video made end to end with Claude Code | Yes | Case study. |
| 6missedcalls/video-editing-skill | 46 | 2026-02-27 | MIT | Claude Code / Codex / OpenClaw skill: trim, jump cut, captions, speed | Yes | Older. |
| Surojit16/video-editing-skill | 3 | 2026-10-14 | MIT | Natural-language edits in Claude Code | Yes | |
| dubnium0/ffmpeg-mcp | 21 | 2026-02 | MIT | FFmpeg MCP, 40+ functions | Yes | |
| video-creator/ffmpeg-mcp | 153 | 2026-05-20 | MIT | FFmpeg command-line MCP | Yes | |
| VCoder25/vugola-mcp | 7 | 2026-09-23 | MIT | Official MCP for Vugola clipping | No | Vendor service. |
| miracleweasel/katto-mcp | 3 | 2026-10-13 | MIT | MCP for Katto clipping | No | Vendor service. |
| Mavlarn/video-clip-mcp | 0 | 2026-03-20 | MIT | MCP for precise cuts, merges, splits | Yes | Small. |
| 6v17/VideoSeek | 99 | 2026-10-18 | AGPL-3.0 | Offline footage search: semantic and subtitle search, Agent API | Yes | Find moments inside long footage. AGPL. |
| VelornLabs/velorn | 504 | 2026-10-12 | GPL-3.0 | AI-native editor with MCP agent control | Yes | GPL. |
| 0xsline/OpenChatCut | 2,496 | 2026-10-18 | AGPL-3.0 | Conversational AI editor with a multi-track timeline | Yes | AGPL. |
| DonkeyCut/Donkey | 315 | 2026-10-17 | Apache-2.0 | Open-source CapCut alternative, LLM-controllable | Yes | |
| MartinDelophy/ai-video-editor | 857 | 2026-10-17 | MIT | Local-first editor where creators and agents edit the same timeline | Yes | *search* (from gh qualifier search) |
| iterative-computer/powermove | 312 | 2026-10-18 | AGPL-3.0 | "Rewrites itself" video editor | Yes | AGPL. |
| Relo-video/SynthCut | 39 | 2026-07-21 | GPL-3.0 | AI-native local-first editor | Yes | |
| thiagoalbrecht/weave | 30 | 2026-07-26 | MIT | Browser editor that renders with FFmpeg | Yes | |
| perso-ai/perso-dubbing-plugin | 39 | 2026-10-15 | MIT | Agent plugin: subtitle, translate, dub, clip | No | Uses a cloud service. |
| JimLiu/baocut | 1,059 | 2026-10-18 | Other | AI video agent with editable timeline | Partial | Read licence terms. |
| mirage-hq/Tesseract | 144 | 2026-10-13 | Other | CLI and agent skills for video | Partial | Read licence terms. |
| luoluoluo22/jianying-editor-skill | 4,245 | 2026-09-11 | Other | Agent automation for JianYing (Chinese CapCut) | Yes | Only if you use JianYing. |

### 3b. Shorts clippers (long video → vertical clips)

| Repo | ★ | Pushed | Licence | What it is | Local? | Notes |
|---|---|---|---|---|---|---|
| modelscope/FunClip | 6,418 | 2026-10-08 | MIT | FunASR transcription, subtitle generation, LLM-assisted clipping | Yes (ASR) | Strong reference for clip selection. Check where the LLM call goes. |
| mutonby/openshorts | 6,811 | 2026-10-17 | MIT | Long video → 9:16 clips, AI highlight detection, subtitles, dubbing, MCP | Partial | Mature. |
| zhouxiaoka/autoclip | 9,512 | 2026-10-18 | MIT | Desktop AI clipper | Partial | Reference only. |
| Anil-matcha/AI-Youtube-Shorts-Generator | 5,455 | 2026-10-11 | MIT | LLM highlights, Whisper, auto 9:16 crop | Partial | |
| FujiwaraChoki/supoclip | 1,510 | 2026-10-18 | AGPL-3.0 | OpusClip alternative, MCP interface | Partial | AGPL. |
| fralapo/clippyme | 61 | 2026-10-14 | MIT | Self-hosted clipper | Yes | |
| ColinGPT9/clips-studio | 119 | 2026-10-18 | AGPL-3.0 | Local OpusClip alternative | Yes | AGPL. |
| BatuCani/reelferry | 0 | 2026-10-14 | Apache-2.0 | Agent-first clip tool with scheduling | Partial | New. |
| shubhankar360/clip-shorts | 0 | 2026-10-12 | MIT | Claude Code skills + MCP for scored, captioned shorts | Partial | New. |
| lopezanthonyrdzwr5534-beep/livestream-clip-pipeline | 0 | 2026-10-18 | MIT | Livestream SRT + recording → clip selection → FFmpeg cut → auto-editor | Yes | Pattern matches our stream use case. New. |
| onurozkir/stream-sentry | 0 | 2026-10-18 | MIT | Live-stream highlight clipping, 9:16 reframing, karaoke subtitles | Partial | New. Unverified. |
| ArcReel/ArcReel | 5,568 | 2026-10-18 | AGPL-3.0 | Self-hosted AI video workbench: novel → storyboard → video → JianYing draft | Partial | AGPL. Not a clipper. |
| Clypra AIEraDev/Clypra | 3,328 | 2026-10-18 | MIT | Rust/Tauri editor, sub-10 ms frame updates | Yes | Editor, not a clipper. |
| GrepCut/OpenClipper | 10 | 2026-10-18 | MIT | Local desktop Opus Clip alternative | Yes | |
| Shaarav4795/ClippedAI | 218 | 2026-09-04 | Other | OpusClip alternative | Partial | Custom licence. Read terms first. |

### 3c. Conventional and AI-assisted editors (GUI)

| Repo | ★ | Pushed | Licence | Notes |
|---|---|---|---|---|
| OpenCut-app/OpenCut | 95,231 | 2026-09-24 | MIT | CapCut alternative, manual editing. Largest. |
| storytold/filmcraft | 14,812 | 2026-10-18 | Apache-2.0 | Non-linear editor in Rust. |
| palmier-io/palmier-pro | 14,597 | 2026-10-05 | GPL-3.0 | macOS editor built for AI. Mac only. |
| krillinai/OpenCreator | 13,687 | 2026-10-18 | Apache-2.0 | Formerly KrillinAI: translation and dubbing workspace. |
| veedstudio/open-edit | 1,684 | 2026-10-07 | Apache-2.0 | (also in 3a) |
| diffusionstudio/editor | 3,341 | 2026-10-17 | MPL-2.0 | "VS Code of video editing, built for agents." |
| getopenscreen/openscreen | 4,519 | 2026-10-18 | MIT | Screen-recording demo editor. Not a clipper. |
| JimLiu/baocut | 1,059 | 2026-10-18 | Other | (also in 3a) |
| nodetool-ai/nodetool | 571 | 2026-10-18 | AGPL-3.0 | Agent-first creative workspace. |
| shdwfruit/convkit | 21 | 2026-10-17 | Apache-2.0 | One-command conversion wrapping ffmpeg and ImageMagick. |

### 3d. Rendering frameworks and building blocks

| Repo | ★ | Pushed | Licence | Use |
|---|---|---|---|---|
| heygen-com/hyperframes | 66,655 | 2026-10-18 | Apache-2.0 | HTML → video for agents. Candidate for 0–3 s hook overlays. |
| remotion-dev/remotion | 64,994 | 2026-10-18 | Other | React → video. Read its licence for company use. |
| dmtrKovalenko/fframes | 2,847 | 2026-10-18 | MIT | Fast Rust programmatic renderer. |
| mifi/editly | 5,528 | 2025-05-12 | MIT | Declarative JSON editing. Stale. |
| WyattBlue/auto-editor | 5,552 | 2026-10-18 | Unlicense | Cuts silence and low-motion sections. Good for filler/dead-air cuts. |
| m-bain/whisperX | 24,653 | 2026-10-18 | BSD-2 | Word-level timestamps and diarisation. Reference for words.py. |
| smacke/ffsubsync | 7,906 | 2026-07-24 | MIT | Subtitle sync to video. |
| Breakthrough/PySceneDetect | 5,255 | 2026-10-18 | BSD-3 | Scene detection. |
| Zulko/moviepy | ~15k | 2026-08 | MIT | Python editing library. |
| ffmpeg (ecosystem) | — | — | — | ffmpeg-static (9.8M/mo downloads), @ffmpeg-installer (4.9M/mo). Packaging only. |

### 3e. Multi-agent video orchestration

| Repo | ★ | Pushed | Licence | Pattern |
|---|---|---|---|---|
| calesthio/OpenMontage | 69,505 | 2026-10-16 | AGPL-3.0 | Coding agent as coordinator over 12 pipelines, spec-checked stages |
| HKUDS/VideoAgent | 1,954 | 2026-07-22 | MIT | Agentic framework for understanding and editing (EMNLP 2026) |
| GVCLab/CutClaw | 987 | 2026-04-17 | NONE | Planner / Editor / Reviewer agents for long-footage editing |
| galanime/short-video-studio-lite | 0 | 2026-07-02 | NONE | 9-state job machine with a human approval gate (pattern reference) |
| avi5129/kanban-video-orchestrator | 0 | 2026-09-27 | MIT | 7-role Kanban crew, all local (Manim, FFmpeg, TTS) |
| RavindranShanmugam/langgraph-video-agent | 0 | 2026-09-11 | NONE | LangGraph nodes: transcribe, select, cut |
| ChristopheZhao/MuseCraft | 1 | 2026-10-13 | MIT | Generation, not editing |

### 3f. Official and catalogue sources

| Source | ★ | Licence | Finding |
|---|---|---|---|
| anthropics/claude-plugins-official | 42,605 | Apache-2.0 | Official plugin catalogue. No video plugin in `plugins/` or `external_plugins/`. |
| anthropics/skills | 181,977 | NONE in gh | Not checked for video content. |
| 777genius/agent-teams-ai | 2,275 | AGPL-3.0 | Multi-agent team UI, not video. |
| the911fund/skill-of-skills | 79 | MIT | "Quality-ranked discovery engine" for skills, plugins and MCP. Not evaluated. |

---

## 4. Shortlist for this project

Ranked for fit to CLAUDE.md constraints (local, Claude-driven, human gate, licence).

| Rank | Repo | Why | Action |
|---|---|---|---|
| 1 | kajisho5/ffmpeg-skill (MIT, 1,988★) | Local, no API keys, captions, reframe, loudness, platform exports, MCP. Matches the render step. | Read its tool contract vs. `scripts/render.py` and `ass.py`. |
| 2 | browser-use/video-use (MIT, 29,272★) | Most-used Claude-native editing flow. Filler cuts, parallel sub-agents, self-check. | Study the sub-agent split and cut-list format. Replace ElevenLabs with faster-whisper. |
| 3 | bradautomates/claude-video (MIT, 18,772★) | Claude watches the rendered clip (frames + transcript). | Candidate QA step for `review-clip` / `qa-checker`. |
| 4 | modelscope/FunClip (MIT, 6,418★) | LLM-assisted clip selection with subtitles, local ASR. | Read the clip-selection prompt and output schema. Confirm where the LLM call goes. |
| 5 | kurbaitaev/ghost-editor (MIT, 73★) | Talking-head reels with face-safe captions. Closest to talking-head streams. | Verify code quality before using. Small project. |

**Honourable mentions:** kevinbadi/open-edits (MIT, 42★, talking-head → animated short), Vincentwei1021/video-shotcraft (Apache-2.0, 12,385★, Remotion hook overlays), veedstudio/open-edit (Apache-2.0, 1,684★, agent-driven subtitles and motion graphics), WhiteTowerAI/cut-as-code (MIT, 16★).

**Reference only (copyleft):** calesthio/OpenMontage (AGPL-3.0, best multi-agent design), supoclip, OpenChatCut, VideoSeek, ArcReel (all AGPL-3.0).

**Avoid for borrowing:** remotion-dev/skills and krusemediallc/video-editor-agent (no licence).

---

## 5. Known gaps

- Reddit: not reachable with the available tools.
- LinkedIn: search only, low signal.
- Medium: snippets only, article fetch blocked.
- Multi-agent coverage is thinner than single-agent coverage (rate limits earlier).
- PyPI search page did not render. Use the per-package JSON API.
- Star counts for repos under 10 stars are noise.
- Claude-native and local-first labels are from descriptions and READMEs seen in this session, not from reading code.
- The installs (skills.sh) and downloads (npm) figures are demand signals, not quality.
