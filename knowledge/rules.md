# Clip rules

Human-curated. Changed only by approved diff from `knowledge/proposals/` (see /learn).
Read by clip-scout, caption-writer, qa-checker.

## Formats (approved 2026-10-21)
Every candidate and EDL carries `format`: `short` or `mid`. Pick by structure (one beat vs. a story arc), not by length. Length follows the format and the story, not a target number; cut filler, never story beats.
- **Short-Short** (`short`, ~8–30 s): one beat with one punchline or emotional peak (reaction, crit/fail roll, one-liner, in-character bit). Context max one line, preferably in the hook overlay instead of spoken setup. Payoff within ~5 s or as cold open; end right on the payoff, letting the last word ring out, so the clip loops. 1–4 cuts. No end card, no "vorher" card. Caption: 1 sentence.
- **Mid-Short** (`mid`, ~45–100 s; ≥ 61 s keeps TikTok Creator Rewards eligibility): story arc setup → escalation → payoff (fights, schemes; e.g. gold-saga, kraken). Multi-cut EDL; cold open with "vorher" card allowed; end card allowed. Every second carries the story.
- The rest of this file applies to both formats unless a line names one.

## Selection
- Hook in first 0–3 s: punchline, reaction, roll result, or a line that raises a question.
- Self-contained: understandable without campaign knowledge. `short`: max one sentence of setup. `mid`: setup is allowed as long as it is part of the story.
- Prefer: critical successes/fails, dramatic rolls, in-character voice bits, table laughter, sacrifices, cliffhangers, GM reveals.
- Avoid: rules lookups, out-of-game logistics (breaks, tech issues, scheduling), long silences, crosstalk-heavy stretches.
- Avoid single moments whose punchline needs >10 s of build-up. Multi-beat stories may carry a longer setup when the setup is part of the story. (approved 2026-10-21)
- No content from sessions not yet public on YouTube.

## Style
- German primary. Captions in German; English only if requested.
- Subtitles: 2–4 words per card, speaker colors from `config/speakers.toml`.
- Hook overlay: max 6 words, no spoiler of the punchline.
- VTT map as visual anchor (approved 2026-10-20): use map shots for GM narration of visual moments (monster appears, hits, finisher), but only where the map is clean (no GM editor panels). Map shots always use layout "pip" (map on top, speaker's card below), so the speaker stays visible. The speaker card is large (~700 px high, top edge right under the map, growing downward), never a small inset; the wide GM cam only slightly larger than before (max ~720 px wide). (user, 2026-10-22)
- Cold open = the strongest visual moment. If it comes chronologically right before the rest, keep the clip linear (no "vorher" card).
- Fights: prioritize setup → finisher (who does what, the roll, the hit, the title/payoff). Cut side plots and table gags, even good ones, when they do not serve that line.
- Reaction beats: cut a player's emotional peak (shout, outburst, cheer) as a short, fast insert on their cam, keeping only the emotional core ("Ein MONSTER!", not "Ich würde, ich würde schreien, es ist ein Monster!"). Drop stutters, false starts and lead-ins ("Pass auf, …"). Start straight on the line, but let the last word ring out to the next real pause. (approved 2026-10-20)
- Cam follows the voice: while a line is heard, show the speaker's cam, not a reactor's, unless the reaction is the point of the beat. (approved 2026-10-21)
- Cut edges: never clip a word; keep a short pad before the first word of a line. (approved 2026-10-21)
- Caption: 1–2 sentences (`short`: 1) + 3–5 hashtags (Instagram allows max 5) (#daggerheart allowed as hashtag; never the trademark in the title/hook).

## Legal (non-negotiable)
- Attribution in every caption. Draft (VERIFY current Darrington Press Community Gaming License wording before first post):
  `Daggerheart™ Compatible. Enthält Material aus dem Daggerheart SRD © Critical Role, LLC, unter der DPCGL.`
- No official Daggerheart art or logos; no Twitch/YouTube logos or watermarks; no third-party music.
- Every person in the session must be in `config/consent.toml` with valid consent.
