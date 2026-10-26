# Pipeline learnings

## Sources (pnp-crawl, pnp-knowledge)

### Raw transcripts do not store word timestamps  (2026-10-18, verified)
- Observed: `transcripts_raw/*.json` segments have `start,end,text,speaker`. No `words` key in any file.
- Cause: `pnp-crawl/02_transcribe.py:161` builds `words`, but the merge step drops them before saving.
- Action: `scripts/words.py` re-transcribes only the clip window. Alternative (not done): patch pnp-crawl to persist words. That edits a foreign repo, and old sessions would still lack them.

### Final transcript segments are coarse  (2026-10-18, verified)
- Observed: Folge 8 has 546 segments over ~2 h. Some segments are 30+ s long.
- Cause: the pnp-crawl export merges same-speaker lines within 2 s.
- Action: speaker per word comes from max time-overlap with these segments (`words.assign`). Turn boundaries inside a long segment are invisible, so shot switching is only as fine as the segments.

### Final speaker labels are already resolved  (2026-10-18, verified)
- Observed: `"Tim (Lindo Laut)"`, `"Deniz (GM)"`. Some legacy labels are `"Spieler 2 (Kipp)"`.
- Action: `session.py` parses `Person (Character)`. Person key = lowercase name. Consent, colors and layouts are keyed by it.

### Player lines get absorbed into the GM label  (2026-10-19, verified by reading)
- Observed: Folge 10, 1:25–1:31: Tim's in-character Lindo Laut lines ("Ja, ich kauf die.", "hi, na? Wart ihr auch erfolgreich?", "Wir sollten jetzt mal ganz dringend Gunther suchen") are labelled `deniz`. Long `deniz` segments mix GM narration and player speech. In Folge 8, tim had only 25 of 546 segments.
- Likely cause: pnp-crawl `gm_key()` folds surplus clusters into the GM, and the 2 s same-speaker merge glues neighbouring lines together.
- Action: never trust labels for subtitle colors or cam switching without `speaker-checker`. For scripts, correct speakers by content. Candidate for the DER benchmark.

### No local video, only MP3  (2026-10-18, verified)
- Observed: `pnp-crawl/audio/<stem>/<stem>.mp3` + `.meta.json`. No mp4/mkv anywhere in the monorepo.
- Action: video comes from YouTube per clip window (`fetch.py`, `yt-dlp --download-sections`).

### Files are UTF-8; PowerShell shows mojibake  (2026-10-18, verified)
- Observed: OKF session files show `â€ž`, `Ã¼` in `Get-Content` output.
- Action: always read with `encoding="utf-8"` (Python) / `-Encoding utf8` (PowerShell). The files are fine.

### New episodes may have audio but no transcript  (2026-10-18, verified)
- Observed: Folge 10 (`2026-10-14_Team-A_o_cAcqq0Sk0`) had its MP3 downloaded but no `transcripts_final` entry.
- Action: user runs the pnp-crawl pipeline. Check `transcripts_final/<stem>.json` before `/find-clips`.

### Fresh episodes have no OKF session summary yet  (2026-10-19, verified)
- Observed: Folge 10 transcribed, but `pnp-knowledge/.../sessions/2026-10-14.md` missing (`session.py` printed `okf=no`).
- Cause: the OKF bundle is filled by a later pnp-knowledge step (session report → ingest).
- Action: scouts run on transcript + roster only. Context is weaker for "needs campaign knowledge" judgements; re-run `/find-clips` after the OKF file exists if picks look off.

### ASR spellings leak into OKF and EDL text  (2026-10-20, unverified)
- Observed: kraken payoff subtitle reads "Trollschlechter". OKF `characters/dodo.md` uses the same spelling ("Dodo der treue Schlechter" bzw. „Trollschlechter“), so the KB copied the ASR output. The intended word is most likely "Trollschlächter". Also the roll: the segment says "eine 20 mit Hope", the EDL says "21 mit Hope".
- Action: check names, titles and numbers in EDL text by ear before render. The KB is no spelling authority.

### ASR place names mislead scouts  (2026-10-21, unverified)
- Observed: Folge 9 c16. The transcript says Liam answers "Zebras". The scout read it as a non-sequitur joke. KB `locations/berge_von_zebros.md` lists the alias "Berg Zebras": it is the place Zebros, a dramatic reveal (Lunara had just said "Ich hab ein Berg gesehen").
- Action: when writing a script, grep odd words against the OKF bundle (`aliases:`) before judging the beat's type.

## YouTube / yt-dlp

### Bot check blocks anonymous access  (2026-10-18, verified)
- Observed: `ERROR: [youtube] <id>: Sign in to confirm you're not a bot. Use --cookies-from-browser or --cookies`.
- Action: `paths.ytdlp_auth()` passes `config/cookies.txt` (gitignored) if present, else `--cookies-from-browser firefox` (override via env `YTDLP_BROWSER`). User chose Firefox. Chrome/Edge cookie extraction is often broken on Windows (app-bound encryption).

### Cookies alone are not enough: JS challenge  (2026-10-18, unverified fix)
- Observed: with Firefox cookies, `WARNING: Only images are available for download` and `Requested format is not available`. Message points to the yt-dlp EJS wiki (JavaScript runtime + challenge solver).
- Cause: yt-dlp 2026.08.19 needs a JS runtime to solve signatures. By default it only uses deno. Node (`C:\Program Files\nodejs\node.exe`) and `yt-dlp-ejs 0.8.0` are installed.
- Action: `ytdlp_auth()` adds `--js-runtimes node`. Not yet tested (run was interrupted).

### Cookies + node solve the bot check  (2026-10-19, verified)
- Observed: with `--cookies-from-browser firefox --js-runtimes node`, yt-dlp resolved googlevideo stream URLs for Folge 10.
- Status: supersedes the "unverified fix" entry above.

### Section downloads stall: cache the full episode instead  (2026-10-19, verified)
- Observed: `--download-sections` made ffmpeg seek to 5419 s inside a 1.6 GB stream over HTTP. Nothing was written for >10 min and ffmpeg used ~2 s of CPU.
- Cause: googlevideo throttles range-seeking ffmpeg reads. yt-dlp's own chunked downloader is fast.
- Action: `fetch.source()` downloads the full episode once to `work/<session>/source.mp4` (1080p60 avc1, ~2.8 GB), then cuts locally with `-ss` before `-i` (fast and frame-accurate on re-encode). `screens.py` has the same seek problem; switch it to the local source once it exists.

### Auto-dubbed English audio track on YouTube  (2026-10-19, verified)
- Observed: `yt-dlp -F` lists `140-0`/`251-0` [en-US] next to the original `140-1`/`251-1` [de-DE] "original (default)", plus DRC variants.
- Risk: a plain `ba` may pick the English dub.
- Action: format `ba[format_note*=original]`, fallback `ba[language^=de]`. Verified: picks `299+251-1` (1080p60 + German original Opus).

### Stills without downloading the video  (2026-10-18, unverified)
- Idea: `yt-dlp -g` resolves the stream URL once, then `ffmpeg -ss <t> -i <url> -frames:v 1` seeks over HTTP (`scripts/screens.py`).
- Note: stream URLs expire after ~6 h. Re-run resolves a fresh one. ~100 frames per session, 6 threads.

### YouTube embed from a local file  (2026-10-18, unverified)
- Risk: an iframe embed in `board.html` opened via `file://` may refuse to play (missing referrer).
- Action: the board always has an "auf YouTube öffnen" link with `&t=` as fallback.

## Claude Code workflow

### New agent definitions load only after session restart  (2026-10-18, verified)
- Observed: `Agent type 'clip-scout' not found` right after creating `.claude/agents/clip-scout.md`. Available after restart.
- Workaround: `general-purpose` agent with `model: haiku`, prompt "Read .claude/agents/<name>.md and follow it".

### Haiku scouts without examples score flat  (2026-10-18, verified)
- Observed: Folge 8 gave 34 candidates from 9 scouts. Scores were 2–6, mostly 5–6, none above 6. Each scout took ~15–40 s.
- Cause: strict prompt plus no approved examples to calibrate against.
- Action: rely on board feedback → `decisions.jsonl` → `/learn`. Re-check score spread after the first examples exist.

### Scouts emit types outside the enum  (2026-10-18, verified)
- Observed: one scout returned `"type": "roll"`.
- Action: normalize to the nearest allowed type when saving scout output (find-clips skill step 4).

### Chunk overlap produced no duplicates  (2026-10-18, verified)
- Observed: 34 raw → 34 after the >50 % overlap dedup in `candidates.py`.
- Note: dedup kept for safety. 30 s overlap rarely yields the same window twice.

### GPU is shared with the user's pipeline  (2026-10-18, verified)
- Observed: the user runs pnp-crawl transcription in the background. RTX 4070 Ti has 12 GB.
- Action: never start GPU jobs (pnp-crawl, `words.py`) without asking. Scout/board/feedback steps are CPU/LLM only.

### Redo versions are files, not commits  (2026-10-20, process)
- Observed: the repo has no git. Every redo overwrote clip and EDL files.
- Action: log one decision per redo in `decisions.jsonl` with the user's note verbatim. Keep versions as `out_vN.mp4`, `<id>.edl.vN.json`, `words_vN.json` etc. next to the originals (clip folder, session `scripts/` folder). Backups of edited pipeline scripts went to the session scratchpad only, so they are gone after the session.

### Hand retimes live only in the scratchpad  (2026-10-20, open)
- Observed: one-off retime scripts fixed word times after words.py: pause-based phrase bounds for the gold-saga climax and "Lindo Laut! Hör auf!", probe-based word times for kraken "Beschreib mir" and the kill narration. They exist only in the session scratchpad.
- Risk: any words.py re-run of those clips silently undoes them. Re-apply after every re-run.
- Action if it recurs: a per-cut `"words"` override in the EDL (feature for scripts/).

### Name the exact file in review questions  (2026-10-20, user feedback)
- Observed: the user did not know which file to review: out.mp4, out_pip.mp4 or out_vN.mp4.
- Action: every decision question names the single exact path to watch.

## Rendering (ffmpeg / ASS)

### `ass=` filter breaks on Windows drive letters  (2026-10-18, verified)
- Cause: `C:` inside filter args is parsed as an option separator.
- Action: `render.py` runs ffmpeg with `cwd=<clip dir>` and `ass=subs.ass` relative.

### ASS BorderStyle 3 box color = OutlineColour  (2026-10-18, verified)
- Observed (synthetic render): the hook box takes the OutlineColour alpha/color, not BackColour.
- Action: Hook style uses `OutlineColour=&H90000000` for a semi-transparent black box.

### Filter graph verified on synthetic input  (2026-10-18, verified)
- Observed: testsrc2 1920x1080 → 3 shots (crop, wide/blur, crop) + ASS + loudnorm → 1080x1920 h264/aac, 8.1 s for 8 s input. Frames looked right.
- Not yet verified on real stream material (crop boxes, real facecam layout).

### Multi-cut mode via EDL  (2026-10-19, verified on synthetic input)
- Why: storytelling clips (e.g. Folge 10 gold saga) span 6 min of session for 60 s of clip. One contiguous window cannot do that.
- Design: `scripts/<id>.edl.json` per clip. fetch downloads each cut and joins them with 30 ms audio fades. `window.json` stores the measured offset/dur per cut. words.py takes the speaker from the EDL (hand-corrected beats pnp-crawl labels). render does one shot per cut with a `cam` override for reaction shots. ass.py adds `card` overlays and never lets a subtitle card span a jump cut.
- Check: synthetic 3-part join (2+3+4 s) → 9.1 s out, card + hook + subs visible, shots switch per cut.
- Open: cut times inside long pnp-crawl segments are estimates. Refine the EDL after the first words.py run (words show where sentences really start/end), then re-fetch.

### Team A stream layout: small tiles, name plates  (2026-10-19, verified)
- Observed: 1920x1080 overlay. Four player tiles (~370x520) in the corners with character name plates (Dodo, Lindo Laut, Lunara, Gunther), the GM unplated at bottom center, the VTT map in the middle.
- Decision: show the whole tile fit to 1080 wide on a blurred fill (`render.shot_filter`). A 9:16 fill crop of a tile would be ~200 px wide (5x upscale), too soft. Name plates double as on-screen speaker labels.
- Person mapping comes from the name plates, not faces.

### Whisper on a jump-cut clip loses words  (2026-10-19, verified)
- Observed: transcribing the joined 59 s gold-saga clip gave 98 words. Three cuts came out empty and words slid into the wrong cut.
- Action: words.py multi mode transcribes each cut from source.mp4 with 10 s of context and keeps words inside the cut. 3 s context was too little (cuts still dropped).

### initial_prompt suppresses the prompted text  (2026-10-19, verified)
- Observed: passing the cut's verified text as `initial_prompt` gave 56 words. Whisper skipped exactly the sentences it was prompted with.
- Action: no initial_prompt. `hotwords` = character names (spelling nudge only).

### Subtitle text from the EDL, timings from Whisper  (2026-10-19, verified)
- Observed: even with good context, Whisper mis-hears table talk: "18 Gold" for "acht Säcke Gold", "nehmen wir wieder jammern", "mimensprache". One Celin line was never recognised (crosstalk).
- Action: `words.align_text` maps the verified EDL text onto Whisper word times (difflib equal + same-length replace blocks). Unmatched tokens are spread between neighbours. 142/142 words came out correct.

### ctranslate2 needs torch's CUDA DLLs on Windows  (2026-10-19, verified)
- Observed: `RuntimeError: Library cublas64_12.dll is not found or cannot be loaded`.
- Cause: the DLL ships in `ttrpg_env/Lib/site-packages/torch/lib`. pnp-crawl imports torch first, which adds that dir to the DLL path.
- Action: `import torch` before `faster_whisper` in words.py.

### Clip layout: picture band, hook above, subs below  (2026-10-19, verified)
- Observed: a tile fit to full width put the subtitles on top of the name plate and character portrait.
- Action: picture band y 380..1480 (`render.BAND_Y/BAND_H`). Hook box above (MarginV 260). Subs bottom at y 1600 (Sub MarginV 320), on the blurred fill.
- Known: long words can wrap to 2 lines and touch the band bottom ("Meme-Sprache zu sagen: shoppie,").

### VS Code preview plays no AAC audio  (2026-10-19, verified)
- Observed: the user heard nothing in src.mp4. volumedetect showed mean −26.6 dB, matching the German pnp-crawl MP3 exactly.
- Action: open clips in an external player (Windows Media Player, VLC). The `eng` language tag on the Opus track is a mux default, not the dub.

### Hook box must respect the right safe margin  (2026-10-19, verified)
- Observed: Hook style at 72 px with 80/80 margins drew the box out to x≈1013, inside the 120 px TikTok side-button zone (flagged by qa-checker).
- Action: Hook 64 px, MarginL 120 / MarginR 140. The box now ends at x≈952.

### Redo 1 of gold-saga: padding, bigger faces, background A/B  (2026-10-19)
- User feedback (decisions.jsonl): cuts clipped at sentence starts; no reaction shot while someone else speaks; faces too small; background color not nice.
- Padding: `fetch.padded` adds 0.2 s lead / 0.3 s tail per cut, none at seams that continue the source. Research (Haiku web, weak vendor sources) suggests 50–200 ms; we sit at the upper end because the user heard 0 as clipped. Cost: +3.4 s over 11 cuts.
- Faces: layouts.toml v2 boxes = inner camera image only (~300x350), band y 300..1500. Faces roughly 2x larger. The name plate is gone; subtitle color identifies the speaker.
- Background: `render.BG_STYLES` self | map | map-teal, chosen in `config/style.toml` or with `--bg` (writes out_<style>.mp4 for A/B). The research backs only orange/teal complementary contrast and blur/darken for focus. Blur, darken and grade values were set by eye.
- Bug caught: `[b0],crop` (leading comma after a filter label) breaks ffmpeg with "No such filter: ''". test_core now asserts no "]," / ",," in shot filters.

### Redo 2: user picks map bg + whole tiles, slightly zoomed  (2026-10-19)
- User: `map` background. Inner-camera crops (v2) looked worse than v1's whole card tiles, so v3 uses the tiles inset ~5 % per side (~18 % bigger). Clipped frame ornaments are OK per user.
- Lesson: the card frame + name plate is part of the look. Bigger faces are not worth losing it.
- Subtitle cards are now also capped at 24 chars (`ass.MAX_CHARS`). A 2-line card grew upward onto the name plate ("Meme-Sprache zu / sagen: shoppie,").

### Redo 3: story over length, uncut tiles, end card  (2026-10-19)
- Length rule changed with user approval: length follows the story, no hard cap. Updated rules.md, clip-scout, qa-checker, cut-clip skill, candidates.py (20–90 s guard), CLAUDE.md. The 60 s cap came from the handoff brief, not from any known algorithm advantage.
- Tiles: v1 whole boxes (uncut frames) shown in the 1200 px band, which equals v3 on-screen size. Supersedes "Redo 2" inset boxes.
- End card (`config/style.toml [endcard]`): dark blurred map + logo (`assets/dwarfmasters_logo.png`) + lines (channel in logo teal, "Daggerheart™ Compatible", campaign/season). 3 s, audio fades 0.4 s before it. render.endcard_filter builds the picture, ass.endcard the text.
- Logo prep: the original PNG has a white background. PIL `ImageDraw.floodfill` from the 4 corners (thresh 40) removes only border-connected white, so teeth and eye whites stay. Then crop to bbox.
- TikTok in-video links are not clickable; the card is a reminder, the profile link converts.

### Map as visual anchor: check the map before choosing map shots  (2026-10-19, verified)
- Observed: Folge 10 Kraken fight. Between 720 and 910 s and from about 2200 s, the GM's VTT editor is open inside the map region: side panels and an asset bar that literally reads "Kraken Tentacle". From about 1070 s the map is clean (ship, tentacles, kraken head, Dodo figure).
- Action: before writing an EDL, pull map-region frames at each beat (`ffmpeg -ss t -frames:v 1 -vf crop=845:575:540:55`). Use `cam: "map"` only where the map is clean; otherwise use the speaker's cam.
- Gotcha: ffmpeg `drawtext` segfaults in Git Bash (no fontconfig). Label frames by order, not with burned-in text.

### Two map layouts: A (map only) vs C `--layout pip`  (2026-10-19)
- A: map 845x575 fit to 1080 wide → about 735 px of the 1200 px band; the rest is blurred map. Nothing is cut off, but the map looks small and nobody is visible on map shots.
- C (`render.pip_filter`): map on top of the band (y 300..1035), speaker card below it (450 px at first; 2026-10-22 user: too small -> 700 px, y 1030..1730, top edge fixed, `render.PIP_TOP/PIP_H`; width capped by `PIP_W` 720 so the landscape GM cam stays only slightly larger). Map anchor plus "you always see who speaks". Writes `out_pip.mp4`. QA rated C clearly better on the map stretches.

### User picks C: map + speaker card is the standard  (2026-10-20, decision)
- The user chose C over A for the kraken clip. `config/style.toml layout = "pip"` is now the default for every map shot. `--layout full` keeps A for comparisons. Recorded in rules.md (Style).
- Redo v2: 152 s → 78.7 s (12 cuts). Cold open = the strongest map image (kraken head, from the v1 timeline at 0:58–1:07). It comes chronologically before the rest, so the clip runs linear with no "vorher" card. Kept the line setup (stone plan) → hit → Dodo setup → roll → jump → title. Cut the side scenes (night, the "Stopp" gag, Joar epilogue).
- Lesson: for fight clips, build the backbone setup → finisher first. Gags only go in if they sit on that backbone.

### Cut timing: never split inside a phrase, leave breath at seams  (2026-10-20, user feedback)
- Observed (kraken v2): the user found two cuts "slightly too fast". (1) Lindo Laut's "Ich würde schreien: / Es ist ein Monster!" was split around a 2 s pause, and the jump cut dropped "es" (1441.0 s), which sat in the gap. (2) The hook cut's tail (+0.3 s) reached into the GM's next word "Ein" (starts 0.07 s after "anblicken").
- Action: keep a thinking pause inside one line instead of jump-cutting it. Set `tail` so the cut ends before the next word starts (check the probe output). Give ~0.5 s `lead` before a new speaker's first cut after a scene jump.

### Cut points: 20 ms RMS dips beat Whisper word starts  (2026-10-20, verified)
- Observed: Whisper word starts were off by up to ~0.7 s. Tim's "Ich": probe 1437.97, real 1438.65. "und" at 1444.23 was really the drawn-out end of "Monster", which runs to ~1444.75.
- Method: a 20 ms RMS map on the 48 kHz source, `ffmpeg -af asetnsamples=960,astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level -f null -`. Word boundaries show as dips (−35…−48 dB). `silencedetect` (−27…−35 dB, d = 0.12) gives phrase bounds.
- Action: probe.py for which word sits where, the RMS map for the exact seam.

### Drawn-out words: end a cut at the next real pause  (2026-10-20, user feedback kraken v6)
- Observed: cutting at Whisper's start of the next word clipped "Monster". The user heard it cut off twice.
- Cause: Whisper starts the next word while the previous one is still ringing out.
- Action: end a cut where RMS drops below ~−45 dB, not at the next word's Whisper start.

### Same-speaker micro jump cuts work  (2026-10-20, verified)
- Observed: Tim's confession in gold-saga ("Ich | würde schreien") uses micro jump cuts inside one speaker's line. They read as natural pacing, not as glitches.
- Action: fine for one speaker on an unchanged cam. Subtitle cards may span these seams (`ass.seams`, see "Subtitle cards" below).

### Audio runs under the end card  (2026-10-20, user request)
- Why: the user found a silent end card looked "dead".
- Design: `style.toml [endcard] audio_overlap = true`. fetch extends the last cut by `seconds` and stores `endcard_audio` in window.json. render ends the picture at `dur - endcard_audio`, lays the card over the tail, and fades the audio over the last 1 s. ass shows no subtitles after the card starts.
- Verified on kraken v3: mean −18.6 / −21.1 dB under the card (v2: −91 dB, silent). The GM keeps narrating ("denn du springst mit Perfektion…") as the fade-out.

### Seam fades on continuous source caused dropouts  (2026-10-21, verified)
- Observed: qa-checker on Folge 9 unterwaesche v2 found 10–20 ms near-silent dips (−66…−94 dBFS) at every join, also where the next cut continues the source (cam switch mid-line).
- Cause: `fetch.concat_filter` put a 30 ms fade-out + fade-in on every seam.
- Action (done): fades only at real jumps (`concat_filter(durs, joined)`, test_core asserts it).

### align_text spilled unheard words into the next cut  (2026-10-21, verified)
- Observed: gunther-maske v1, cut 2: Whisper heard 7 of 52 words; the rest landed 31.96–35.61 s, inside cut 3, interleaved with its words ("Ich Kreis weiß ganz").
- Cause: the 0.1 s-per-word floor pushed a trailing run past `hi`.
- Action (done): `words.align_text` starts such a run early enough to end at its right anchor / `hi` (test_core).

### Whisper word times 0.3–0.6 s off; speech islands are the better clock  (2026-10-21, verified)
- Observed: Folge 9: probe/Whisper put "Ich" at 5574.76, but silencedetect shows silence until 5575.29; "Zebras" 8648.55 vs speech 8649.14–8649.62; "Kreis." really ends 3355.24 (20 ms RMS), the v2 cut at 3355.06 clipped it. Subtitle cards came up to 0.8 s early or late (qa-checker).
- Action: v3 cut points come from `silencedetect=noise=-35dB:d=0.06` islands and 20 ms RMS dips, not word starts. Subtitle times: probe words with each phrase start snapped to the nearest speech onset (≤ 0.7 s), rest of the phrase shifted along (scratch `retime.py`). Promote into words.py if it recurs.
- Snap gotchas found on the way: (1) only pauses ≥ 0.2 s count as onsets (0.1 s dips sit inside phrases, "von der | Roten" jumped 0.5 s); (2) a phrase start is a gap after the previous word's estimated end, not a start-to-start gap ("Leute, Liam." snapped onto the next sentence and shifted 8 words by 0.6 s); (3) an onset must lie after the previous word, or words reorder (0.00 s cards); (4) clamp words the shift pushes past the cut end instead of dropping them.
- A punchline word Whisper times early ("Zebros." 0.6 s) spoils the joke on screen: give it its own joined cut starting in the pause before it, so its card cannot start earlier.
- Also: with `endcard_audio` > 0, speech that continues after the last line plays unsubtitled under the end card (4 of 6 Folge 9 clips). Use `endcard_audio: 0` unless the tail is laughter.

### Bleep censoring via EDL  (2026-10-21, verified on synthetic input)
- Why: the user wants vulgar words censored in text and audio (Folge 9 zuckerwatte: "Arsch", "Arschloch").
- Design: EDL cut key `"bleep": [[s, e], ...]` in session seconds. fetch passes it through to window.json. `render.bleep_filter` maps it to clip time (`offset + s - start`), mutes `[0:a]` there and mixes in a 1 kHz sine before loudnorm. Subtitles: write the censored form ("A***loch") in the EDL text.
- Gotcha: ffmpeg `sine` has a fixed 1/8 amplitude (~-21 dBFS RMS). At volume 0.3 the bleep measured -34.5 dB, far under speech. Volume 1 is used.

### One-pass loudnorm overshoots true peak  (2026-10-20, verified)
- Observed: kraken v7 (Tim's shouted "MONSTER") measured true peak −0.0 dBFS despite `loudnorm=...:TP=-1`.
- Action: render.py appends `alimiter=limit=0.891:level=false` (−1 dBFS) after loudnorm. v7 re-render: −13.9 LUFS, peak −0.8 dBFS.

### Per-clip silent end card  (2026-10-20, user redo kraken v5)
- Why: in kraken the source runs on after the last line ("Aber Dodo…"); the user wanted the sound off after "…vom Deck runter bewegen."
- Design: EDL key `"endcard_audio": 0` overrides style.toml in fetch.py. render fades the last 0.05 s only (0.4 s, then 0.15 s, swallowed the drawn-out "-gen"); cut the last cut in an RMS dip (20 ms `astats` map), `tail: 0`.
- Tim/Gunther cut points came from 20 ms RMS dips: the two probe.py runs disagreed by > 1 s on "Ich" (1437.97 vs real 1438.65).

### probe in batch  (2026-10-19; promoted 2026-10-20)
- `probe.py` loads large-v3 on every call (~10 s each). For 20+ beats, one model load with many windows took about 2 min (scratch `probe_many.py`). Promote it to scripts/ if it gets used again.
- Done: `probe.py <stem> <s1> <e1> [<s2> <e2> ...]` takes several windows with one model load (2026-10-20, 6 windows for kraken v4 / gold-saga v3).
- Whisper missed a quiet line spoken over crosstalk ("Ich hab eine 26 mit Hope", 846 s) even with context. Times came from fragments, and the text from the segment.

### Length estimate vs. real length  (2026-10-19)
- Kraken EDL: about 138 s of cuts became 149 s of src (24 cuts × ~0.5 s lead/tail padding), 152 s with the end card. Estimate with padding included: `sum(dur) + 0.5 × cuts`.

### Stretched Whisper anchor squeezes untimed words into 0.1 s slots  (2026-10-20, verified)
- Observed: gold-saga v2, Celin's climax (42.85–51.4 s, continuous speech per silencedetect). Whisper missed 14 words and matched "langsam" as one word lasting 43.78–49.36 s (5.6 s). `align_text` (words.py:68) spread the 14 words between 42.85 and 43.78 with the 0.1 s floor. Result: four cards flash by in 1.4 s, then "ganz langsam ihren Kopf" stays on screen for 7.2 s. Subtitles run about 5 s ahead of the audio.
- Cause: matched words are trusted even when their duration is implausible.
- Action (done 2026-10-20): `words.align_text` ignores Whisper words longer than `MAX_WORD` (1.2 s) as anchors and spreads leftovers by length (`len + 1`). `ass.warnings` flags ≥ 3 words in a row under 0.12 s. On the real gold-saga data the climax no longer squeezes; the spread error is ≤ 0.85 s against the measured pauses. Pause-based bounds per phrase (silencedetect −27 dB, d = 0.12) were tighter still, so they were applied by hand (one-off scratch script).
- Also fixed: (1) The last cut's leftovers were spread into the end-card audio. ass then dropped them, and kraken v4 lost "vom Deck runter bewegen." Spread now ends at `dur - endcard_audio`. (2) Leftovers at a cut start (no left anchor) get natural pace (`PACE` 0.08 s per char + 1) right before their first anchor. A cut that opens on silence no longer stretches them over it. (3) words.py prints `WARN cut N: Whisper heard x of y words` below 60 %.

### Whisper misses words in the 10 s context run that probe.py hears  (2026-10-20, verified)
- Observed: kraken v4 last cut (2091.9–2106.1, slow GM narration). words.py (context 2081.9–2116.1) matched few words, and the drift reached +4 s. probe.py on 2071–2105 and 2094–2116 got every word, consistent with silencedetect. Different window, different result.
- Action: when words.py warns or a long cut looks off, take word times from probe.py output for that cut (`align_text(text, probe_words, lo, hi)`). Done by hand for kraken cuts 7 and 11.

### Stretched first word moved an EDL cut start into silence  (2026-10-20, verified)
- Observed: gold-saga v2 "Ich sag so: Hi, na?" started at 5351.2. Whisper stretched "Ich" over 2.3 s of silence, so the clip had 2 s of dead air before Tim. Speech really starts at 5353.29 (silencedetect).
- Action: check cut starts against silencedetect when the first word is long. Cut moved to 5353.25 (v3).

### Auto mode blocks render.py overwriting out.mp4  (2026-10-20)
- Observed: "Permission ... denied by the Claude Code auto mode classifier" for `render.py <stem> gold-saga` (target out.mp4). The same call with `--layout pip` (new file `out_pip.mp4`, exact allow-listed command form) ran.
- Action: in auto mode, render previews to `out_pip.mp4`. The human promotes them to out.mp4 (or approves via /review-clip).

### Subtitle cards: wrap at 24 chars, cross sentence ends  (2026-10-20, verified)
- Observed: "Steinen schmeißen und du" and "während die anderen noch" (24 chars) wrap to 2 lines at 80 px Arial Bold. The 2-line card covers the name plate. 7 of 44 gold-saga cards span a sentence end ("Neun Säcke Gold. Jetzt"). 8 cards last under 0.5 s ("go!" 0.06 s, "Hope." 0.22 s).
- Action (done 2026-10-20): `ass.cards` ends a card after `.!?:`. A 1-word card under `MIN_CARD` borrows the last word of the card before, unless that leaves a flash card behind. Short cards linger up to 0.5 s when there is room. `MAX_CHARS` = 20. Word starts more than `HOLD` (1 s) apart start a new card: Whisper hides pauses inside stretched words, and "Und damit trägt Dodo" had shown "Dodo" 1.4 s before the GM's pause ended. Cards may span a jump cut on the same cam (`ass.seams`), which fixed the "entbehrt" flash at the micro cuts of Tim's confession.

### Hook and subtitles sit in platform UI zones  (2026-10-20, verified on frames)
- Observed: the hook box sits at y ≈ 190–260 and 1-line subtitles at y ≈ 1505–1600 (Sub MarginV 320). Meta's Reels ads guide leaves 14 % at the top (≈ 269 px) and 35 % at the bottom (≈ 672 px). Third-party TikTok templates leave 150–240 px at the top and 340–660 px at the bottom. The hook is inside the top zone. The subtitles are inside the bottom zone under every template. The kraken head in the cold open sits in the right 120 px button column.
- Action (done 2026-10-20): Sub MarginV 320 → 440, Hook 64 → 72 px at MarginV 300 (long hooks wrap to 2 lines), picture band `BAND_Y` 300 → 280 (render.py) so the name plates stay above the subtitles. First try (Sub 420 / Hook 280) failed QA. libass puts the text box bottom, descenders included, on MarginV, so "g" and "," plus the 6 px outline reached y = 1505. BorderStyle 3 pads the hook box by Outline (20 px) beyond MarginV, so the box top sat at 260. "Card" overlays (e.g. "4 Minuten vorher…") last 2.0 s. /review-clip extracts `safezone_*.png` frames, and qa-checker checks them. Verified on gold-saga v3 / kraken v4: no text in the red bands. Open: the kraken head in the cold open still sits in the right button column (needs a per-cut map crop).

### Dice-roll insert: headless Edge + three.js, scripted tumble  (2026-10-25, status: verified)
- Observed: user wanted a BG3-style dice screen (Folge 8 dodo-streitkolben). Spoken audio had only "Plus 5 noch, also eine 36"; the single dice were in the VTT roll log on the map ("(6 + 4) + (12 + 9) = 31", crop of `source.mp4` at 5223 s). Both VTT d12 have the same colour, Hope/Fear came from the user ("Success with Hope").
- Decision: no physics (byWulf/threejs-dice etc. need npm and settle at random times). `assets/dice.html` poses dice as a pure function of time and lands on the wanted face; `scripts/dice.py` serves assets/ with stdlib http.server, runs `msedge --headless=new --use-angle=swiftshader --enable-unsafe-swiftshader --user-data-dir=<tmp>` (own profile, else it attaches to the open Edge), page POSTs each PNG. 90 frames 1080x1920 in ~10 s on CPU. Frames cached by sha1(spec, frame count, dice.html).
- Gotcha: grouping triangles into faces by `normal.toFixed(2)` split faces ("-0.00" != "0.00"); d12 check gave [1,2,4,4,6,6,...]. Key by `Math.round(x*100)`. `dice.py --check` asserts every d12/d6 value lands face up.
- EDL: insert = normal cut with real session span + `"dice"` + `text: ""` (table audio runs under it, no subtitles). edgecheck wanted lead 0.2 there, which pulls in the previous word ("Katze"); set lead by hand. Research and plan: `~/.claude/plans/dice-insert-tool.md`.

## Legal / consent

### Stream overlay art is self-made  (2026-10-19, confirmed by user)
- The character portraits, card frames, heart/shield icons and name plates in the Team A overlay are self-made, not official Daggerheart art. Clips may show them. Noted in `.claude/agents/qa-checker.md` so QA stops flagging them.

### Consent gate covers the whole session roster  (2026-10-18, decision)
- Reason: the wide shot shows every facecam, not only the speakers of the clip.
- Action: `render.py` checks all persons in `segments.json`.

### DPCGL 2.0 rules for audio/video  (2026-10-20, read from the PDF; human must update rules.md Legal)
- Source: https://darringtonpress.com/license (PDF "Darrington Press Community Gaming License 2.0", Last Updated 8/05/2026). The official name is "Darrington Press Community Gaming License (DPCGL)".
- 1.9.4: actual-play videos may be monetized through ads, tips and memberships.
- 2.5: "Daggerheart" is not allowed in a title or on a front cover. In marketing and descriptive text it must have "Compatible" next to it. Open question: does a bare `#daggerheart` count as descriptive text?
- 4.1, non-commercial: copyright notice, attribution, a link to the SRD, a license statement with a link, and a statement on modifications. The PDF's combined English text: "This product includes materials from the Daggerheart System Reference Document 2.0, © Critical Role, LLC. under the terms of the Darrington Press Community Gaming (DPCGL) License. More information can be found at https://www.daggerheart.com. There are no previous modifications by others."
- 4.2(g), commercial: in audio/video, the copyright and attribution must be visible for a time or read out in full. Images such as thumbnails must carry the community content logo (alchemy bottle).
- Gap: the caption draft in rules.md still has the old SRD wording. The end card shows only "Daggerheart™ Compatible".

## Conventions

### Work folder named after the episode  (2026-10-18, decision)
- `work/Season 1 Folge 8 Team A/`, derived from `video_title` (`paths.session_name`). Scripts still take the pnp-crawl stem as argument.

### Lint config is strict  (2026-10-18, verified)
- Observed: ruff flags RUF007 (`zip(x, x[1:])` → `itertools.pairwise`), UP017 (`datetime.UTC`), FURB122, PLW1510 (`subprocess.run` needs explicit `check`).
- Action: follow it. `& $PY -m ruff check scripts` before finishing.

### Glaze edits: own script, screen blend needs RGB  (2026-10-21, verified)
- Why: glaze/fancam edits are visual-only, cut on a BPM grid, from several sessions. EDL/render.py are one-session and speech-driven, so `scripts/glaze.py` renders a plan JSON (shots: stem, t, beats, src/box, fx, card) and reuses the consent gate, layouts and paths.
- Observed: `blend=all_mode=screen` on yuv420p tinted the whole frame magenta (joar-glaze-v1). Fix: `format=gbrp` before split, `format=yuv420p` after the blend.
- Observed: the VTT camera pans within seconds. Contact-sheet times (4 s grid) are too coarse for tight crops on a mini; pull a 2 s sequence of the map region first, then choose `t` and `box`.
- Photosensitivity (2026-10-21, measured): joar-glaze-v6 (strobe per beat + flash on 1-beat cuts) peaks at 2.5 flashes/s by a full-frame YAVG approximation of WCAG 2.3.1 (limit 3/s; flash = opposing luminance changes >= 10 %, darker state < 0.8). Little headroom: TikTok auto-detects flashing and may put a warning screen in front. Check every glaze render: `signalstats` YAVG per frame -> count opposing transitions per 1 s window.
- Fix (2026-10-21, measured): with `strobe` dimmed 0.45 -> 0.25 the count stayed at 2.5/s, because one light hit per beat (flash or strobe) is already 2/s and the dim blip still lifts dark cam frames by > 10 %. joar-glaze-final: no strobe, `pulse` (zoom bounce per beat) for the hectic feel, `flash` only on main hits >= 1.5 s apart -> 1.0 flashes/s.
- Observed: the VTT mouse cursor stays visible in map crops (Folge 9 at source px ~1152,190). Plan option `delogo` blurs it out before the crop. The top ~6 px of the map region hold the VTT toolbar, so start map boxes at y >= 62.

### Subtitle timing: Whisper word clocks stay 0.3-0.8 s off, retime snap had a cut-head bug  (2026-10-21, measured)
- Observed (Folge 9 v3 QA, 5 of 6 clips FAIL on sync): cards up to 0.8 s early/late against the audio envelope. probe.py uses `vad_filter=True`; a no-VAD rerun was not better (first word stretched over the pause, ±0.2-0.6 s elsewhere). Speech islands (silencedetect -35 dB, d=0.06) matched by ear-free envelope checks every time.
- Bug: the scratch retime added `c["start"]` as an onset candidate, so an early Whisper word snapped to the silent cut head (zebros cuts 6-10: cards 0.5-0.7 s before the voice, plus 2.7 s dead air because explicit cut starts skipped the head trim).
- Next (not built): align EDL text to speech islands directly (per-cut constant offset -> assign words to islands -> spread by word length inside the island); trim non-joined cut heads/tails to the first/last island ±0.15 s. Map pip crops still show the VTT toolbar sliver and corner glyphs (chat-gericht cuts 5, 10), see glaze entry: map boxes need y >= 62 and side margins.

### Cut ends clip words: subtitles show what the audio lost  (2026-10-21, verified on all 6 Folge 9 clips)
- Observed (user): "Sag das bitte niemandem." plays without "niemandem"; clip endings cut too early (gestaendnis ends on "Verdamm-", "-nis" 6609.99-6610.48 missing). `edgecheck.py` on all Folge 9 EDLs (v4/v5): 17 CUT, 4 DROP, 3 END, 53 TIGHT, 34 LISTEN edges; every clip affected.
- Cause, three parts that stack: (1) the build scripts wrote `"lead": 0.0, "tail": 0.0` on every cut, overriding fetch's 0.2/0.3 s pad; (2) cut ends sat on `silencedetect -35 dB` island ends, but German word endings (-m, -n, -s, -nis) and the 2nd syllable after a plosive dip are quieter than -35 dB, then the 30 ms seam fade eats the rest; (3) Whisper word starts run 0.3-0.9 s early, so the last word looked inside the cut ("niemandem." probe 8587.78, real 8588.70-8589.16 after a 0.6 s pause) and retime clamped its card into the cut. Result: card on screen, word not in the sound.
- Action: `scripts/edgecheck.py` + skill `check-edges`, gate in /cut-clip (0b) and /review-clip (0). 10 ms RMS against the local floor (10th percentile): pause = 60 ms below floor+8 dB (min -56 dB), dips < 150 ms at the cut = inside the word. DROP needs the speech island after the cut to hold no later Whisper word. Any fix that would pull in further Whisper words becomes LISTEN, not auto (would have added "Ich will, dass du" after "Kreis." and "die uns den Arsch blasen" after "Zucker.").
- Long words (user: "Verdammnis" cut, "Werte für längere Wörter funktionieren nicht"): the build's cut end = first `silencedetect` silence after the last word's Whisper START + 0.1 s, then `dip()` = deepest 20 ms frame in [end-0.12, end+0.2]. Multi-syllable words have internal dips (plosive closure / nasal: "Verdamm|nis" 80 ms below -55 dB, "zusammen|bricht", "durch|geht", "ab|bekommt"), and the deepest frame sits in that dip: the cut lands inside the word. Whisper's early start time makes it worse (the search window ends before the 2nd syllable). edgecheck had the same blind spot (60 ms = pause). Fix: a dip < 150 ms (`SPLIT`) right at the cut counts as word-internal unless Whisper starts a new word there (test_core "Verdammnis"). A global 150 ms pause was worse: it merged real sentence pauses into 2 s LISTEN runs. Never pick cut ends by "deepest dip near the word end"; end after the last sound + >= 0.12 s.
- Room tone: knie floor ~-67 dB put floor+8 inside the room-tone flicker (single -53 dB blips counted as speech, the fix crept 0.09 s per pass). Absolute minimum thresholds (-56 / -48 dB) and anchoring on LOUD frames fixed it.
- Limits: thresholds tuned on Folge 9 room tone (~-60 dB); a music bed needs a retune. Start edges in cross-talk are mostly LISTEN noise. DROP extends over the whole next island (zebros cut 8: 1.1 s incl. 0.55 s non-word sound): listen after the fix.

### Hear-check: Whisper listens to every seam  (2026-10-22, verified on Folge 9)
- Observed (user): clipped words still came back in new generations (chat-gericht v10: 0 CUT/DROP but 19 LISTEN; "einprügeln" missing). edgecheck only sees a word end where a pause follows; in connected speech it can only say LISTEN, which cost manual reviews.
- Licences: torchaudio's MMS_FA and VoxPopuli DE aligners are CC-BY-NC, out (CLAUDE.md). Forced alignment with an Apache German wav2vec2 would need `transformers` + 1.2 GB; user chose the Whisper hear-check (no new dependency), GPU allowed without asking.
- Method (`scripts/hearcheck.py`): per seam join ~3 s before + after exactly as played, transcribe (large-v3, no VAD, 0.15 s pads, ~0.3 s per call), LCS-align with the subtitle words of both sides, count only the 2 words next to the seam. Validated: old "niemandem" / "Verdammnis" edges -> MISSING ("…seinen Vertrag"), fixed ones -> OK.
- Gotchas: (1) per-edge checks flagged words split across jump cuts ("beängstigende | Macht"): check the seam as heard, not each edge. (2) ASR spellings ("Gunther" -> "Ganter", "Lunara" -> "du narra"): fuzzy ratio 0.7. (3) Whisper mishears short edge words ("Es" -> "ey"); the inward search "fixed" that with lead -0.65, cutting into "tut". So: only outward fixes (MISSING), EXTRA = LISTEN, fillers / <= 2 letters ignored. (4) Whisper completes a decaying tail from context ("erkennt" 0.56 s cut still heard): edgecheck stays first.
- Run 1: 59 per-edge findings -> 33 seam findings -> after the outward-only rule the rest is CONNECTED (cut inside connected speech, often micro cuts like "Chat," 0.28 s) or LISTEN leaks. Upstream rule for EDL authors: end cuts at a real pause, no cut under ~0.6 s of speech.
- Calibration (2026-10-22, hearcheck on the pre-fix EDLs + whole-clip Whisper of every out.mp4): found "niemandem", "da...", "zusammenbricht", "Verdammnis", "einprügeln"; misses slightly clipped tails that Whisper completes from context (edgecheck covers those, so run edgecheck first). Noise sources and the countermeasures built in: (1) a clipped word comes back as a piece or near-miss ("zusammen", "vertrag" for "Verdammnis") - `fragment()` counts it as truncation, not a leak, so it gets the automatic fix; (2) a 50 ms window change makes Whisper hallucinate for one step ("auf einen Pool gehen") - `walk()` skips transient noise and accepts only two clean steps in a row; (3) lone-word cuts ("Macht,") are not heard in joined audio - when the edge is clean by loudness (`edge_in_pause`) the finding is a NOTE; (4) words *inside* a cut that the EDL text lacks ("kannst du kannst du", "wie so ein, kennt") show up as `interior()` NOTEs of >= 3 words; Whisper drops stutters, so single words are ignored.
- Runs on the shared GPU wait behind other sessions' jobs (probe/hearcheck of other episodes ran at the same time: 10+ minutes for a 3-clip run). Keep hearcheck calls few: one per clip per pass, not one per step.

### Map shots in every clip: pip switch, where to put them, how to check  (2026-10-21, user decision)
- User wish (knie, unterwäsche, then all Folge 9 clips): 1-2 shots per clip that show the VTT map plus the speaker, "darf gerne einfach so switches für etwas mehr Reize auf dem Screen" (one at the very start is fine). Shorts: 1 is enough. A clip that is only one face for 60 s was the top monotony finding of the viewer reviews (gunther-maske 39 s, chat-gericht 18 s of one cam).
- How: EDL cut `"cam": "map"` -> `render.pip_filter` (map on top, the cut's `person` as speaker card below, no extra work). Switch inside a line without a seam by splitting the cut at an unchanged word boundary and marking the second piece `join: true` (prev end = this start, no fade, subtitles continue). Gunther: split at the 0.1 s dip after "Väterliche".
- Where: lines that narrate or set the scene (long third-person sentences, chat message read-outs, "Wachen!", a vote question) and where the map shows what is said (father on the balcony, guard at the arch, two minis alone in a room, die next to the party). Keep the face for the punchline and emotion cuts (tears, smirk, "Zebros.").
- Check first: `python scripts/mapsheet.py <stem> <id> [--step 3]` (or `<id>` = `<start>-<end>` session seconds) writes a contact sheet of the map region over the EDL's source spans. The VTT editor (left token column, bottom asset bar, dice tray) is open at times (gestaendnis 6465-6478 s, chat-gericht 5711-5719 s): not usable there, cut the map shot to start after it closes. Folge 9 zebros and gunther-maske are a static room view, clean throughout.
- Crop: `layouts.toml` `[team-a] map` was [540,55,845,575]: its top 5 px held the VTT toolbar and all four corners the purple frame ornaments (QA chat-gericht v3: "VTT chrome on map shots"). Measured at 4x zoom, now [560,66,806,548] (same aspect). Affects every future render, including the end card background. Already rendered clips (gold-saga, kraken) keep the old crop.
- Caveat: the speaker card is 450 px high in pip, smaller than a full face shot. Do not put a map shot on the one line where the face is the joke.

### Re-probes lost to wide windows; edgecheck vs. spectral edge review  (2026-10-21, chat-gericht v5)
- Observed: after a narrow `probe.py` re-run (6232.4-6237.6, the wide 6213-6240 run had garbled "wir spielen unglaublich"), retime still used the garbled words; Celin's first 4 words got `e < s` (86.48 s). Cause: `tools/retime.py probe_words` picks the window where a word sits farthest from the edges, so a wide window always beats a narrow re-probe, and equal margins (two windows ending at 6912) kept the word twice.
- Fix: windows <= 6 s win (re-probes are deliberate corrections), ties keep only the first window.
- Edge review: an Opus subagent set 38 edges from 10 ms RMS, band energy and F0 (Whisper starts 0.1-0.4 s off). `edgecheck.py` then still flagged 7 of those as CUT because it measures loudness only: stutter seams ("ihr seid, | ihr seid"), word-to-word joins with no pause. Do not `--apply` over hand-set edges; apply TIGHT/DROP tails by hand and listen to the CUT spots.

### EDL edits need fetch.py again: render reads cuts from window.json  (2026-10-21, gestaendnis v6, status: verified)
- Observed: added `"box"` to GM cuts in the EDL, re-rendered: frames identical to v5. Same trap for cut times/cams.
- Cause: `render.py` reads `clips/<id>/window.json` (written by `fetch.py`), not the EDL. Only `fetch.py` copies EDL cut fields (box, cam, card) into it.
- Action: after any EDL change run `fetch.py` before `ass.py`/`render.py`. GM face zoom: cut `"box": [775,670,370,410]` (team-a, GM tile [690,670,560,410]) fills the 1200 band (~2.9x upscale, still sharp enough); keep GM wide on some cuts for variety.

### Plosive closure looks like a word end  (2026-10-22, chat-gericht v11, status: verified)
- Observed: user heard "MVPs" cut off at the clip end. Cut ended 7233.17, inside a 50 ms dip (-48 dB) that ctx.py reported as a gap between speech islands; Whisper put the next word "etwas" at 7233.36.
- Cause: the dip was the closure of the "P" in "Em-Vau-Pees"; the voiced "-Pees" (7233.24-7233.44, highpass >4 kHz -17 dB below full band, so not an "s" hiss) is part of the word. A dip under ~80 ms inside a word is no cut point.
- Action: before ending on a dip < ~0.1 s, check the 20 ms RMS (`astats` with `asetnsamples=320` at 16 kHz) up to the next real pause (>= 0.1 s) and cut there.

### retime.py replaces words.py for EDL clips; the scratch retime had a cut-head bug  (2026-10-22, verified on Folge 9)
- Observed: `scripts/retime.py` (probe words + speech-onset snapping, uncovered cuts probed automatically into `probe_auto.txt`) against the Folge 9 scratch version on 5 clips: first subtitle word vs. first speech island of each cut head: mean |d| zebros 0.35 -> 0.23 s, gunther-maske 0.25 -> 0.12, knie 0.26 -> 0.18, unterwaesche 0.22 -> 0.18, gestaendnis 0.31 -> 0.27; zebros cards more than 0.25 s early 6 -> 1.
- Cause: the scratch version added the cut start as a snap candidate, so early Whisper words snapped to the silent cut head (zebros cuts 6-9: cards 0.5-0.8 s before the voice). The repo version only snaps to real onsets.
- Action: /cut-clip and /auto-clips use `retime.py` for multi-cut clips; `words.py` stays for single-window clips. Folge 9 scratch tools (`work/.../scripts/tools/`) are obsolete except `review.py`/`mapframes.py`. Still open: heads where the first island is a breath, not a word (gestaendnis: 5 heads 0.25+ s late).

### /auto-clips Folge 7: what cost time  (2026-10-22, status: verified)
- GPU contention: hearcheck stalled > 10 min (no output) because another session's hearcheck (Folge 9 chat-gericht) and a `recall.py` job held 11.8 of 12.3 GB. Killing foreign processes is blocked (auto mode) and wrong anyway. Action: check `nvidia-smi` before GPU steps; if busy, do the CPU path first (fetch -> retime from probe -> ass -> render) and run hearcheck when memory frees up. One `probe.py` call per run covers all clips, so words.py (GPU) is not needed when the session retime tool is used.
- `Out-File -Encoding utf8` (PowerShell 5.1) writes a BOM; the first `== a-b` header of probe_v1.txt did not match and retime silently gave 0 words for that window ("probe 0 / text 20  <-- check"). Fixed in the Folge 7 `tools/retime.py` (lstrip BOM). Also removed the cut-head onset there (learning "Subtitle timing" bug).
- Default pads leak neighbour words in connected speech: hearcheck run 1 reported EXTRA words at 9 seams ("wütender", "auslebt", "Genau dasselbe", GM "Und"), from fetch's 0.2/0.3 s lead/tail. Fix per cut from `ctx.py` islands: start on the island, `lead: 0`. Where two phrases touch without a pause (GM "Genau dasselbe. Es ist verlockend."), drop the line instead of hunting a cut point.
- edgecheck reads a following word 0.13 s after the last word as "tail clipped" (loch-im-dach "Dach | also"), hearcheck hears the edge clean. Its suggested tail would pull the next word in; left as a listen point.

### /auto-clips Folge 8: labels, scouts, retime  (2026-10-22, status: verified)
- Absent player still labelled: Tim was not in Folge 8 (empty Lindo-Laut tile), yet pnp-crawl labelled 6 segments `tim`. They were Heiko (Gunther holding Shadowbind: "Ich kann das nicht lange!") and Deniz voicing NPCs (Lindo Laut, Liam, Joar, a guard). Action: when a roster person's tile is empty in a frame, treat their labels as someone else's and set `person` from context + frames.
- Re-scouting with the format-aware clip-scout gave the same flat scores (max 7, mostly 4-6) as the 2026-10-18 run. Reading the transcript around the top candidates and the OKF summary picked the arcs; scouts are only a pointer list.
- Repo `retime.py` vs. hand-fixed scratch retime: on dodo/mutter/lindo it produced new flash cards (0.15-0.4 s, "probe 0 / text 3" on a 1.3 s cut) that the scratch run plus hand-placed island times did not have. Kept the hand-fixed words there (`words_v1.json`), repo version for the other three. Flash cards came from shouts and GM lines Whisper hears as one blob (island 1342.39-1348.99 = "Und Lindo Laut… Ihr Narren. Und Lindo Laut fliegt"): a narrow re-probe (6 s) of that span placed the words.
- QA (Haiku) on all pip map shots: speaker card measures ~720x530 px, rules.md (2026-10-22) says ~700 px high. Not changed here (render.py layout is shared); open for the user.
- Hook hidden by a cut-0 card (fixed in ass.py): `build()` ended the hook at the first card offset ("never stack hook + card"), so a `card` on cut 0 made the hook 0 s long; 4 of 4 mids showed only the card. Now cards before `MIN_HOOK` (1 s) start after the hook (test_core). Also set `endcard_audio: 0` on the mids: the default 3 s overlap played unsubtitled speech, and with it off the last cut needs edgecheck's END tail (kugel "lauf!", opfer "heute." were clipped).
- qa-checker still applies a 20 s minimum (old rule) and flags the pip card (527 px for the GM landscape cam, intended via `PIP_W`) and "attribution not in caption" (/review-clip appends it). Treat those three as noise until the agent prompt is updated.
