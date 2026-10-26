# Short-form research: what the platforms and the scene tell us

Reference for clip decisions (length, hook, layout, captions, audio). Research as of 2026-10-20.

Evidence levels:
- **official**: the platform's own page, help center, or a named platform executive.
- **study**: third-party analysis of a large sample with stated method.
- **low**: vendor blog, ads-only data, a single report, or an estimate.

## Platform signals

- **TikTok** (official): the recommender page lists watch time, completion vs. skips, likes, shares, comments, follows and "not interested". No weights published. Follower count is not a direct factor. For longer videos, completion is a "strong indicator".
- **Instagram** (official): watch time, retention, shares, likes, comments. Mosseri 2024: "sends per reach" is among the most important signals.
- **Both** (official): watermarks from other platforms are penalized. Export clean.

## Hook

- TikTok ads guide (official, ads context, no data): core proposition in the first 3 s, hook by 6 s.
- 3 s hold rate exists only for ads (low): median ~33 % TikTok / 31 % Reels, top 10 % ~55 %.

## Length

- TikTok Creator Rewards (official): videos ≥ 1 min, 10K followers, 100K views in 30 days, 18+. So ≥ 60 s matters once monetization is a goal.
- Reels up to 3 min are shown to non-followers since Jan 2025 (official).
- Completion by length (low): vendor claims conflict, ~48 % for > 60 s vs ~62 % for 21–34 s. No basis for a hard cap. Project rule: length follows the story.

## Benchmarks

- TikTok engagement per view 2025 (study, Socialinsider, 2M videos): ~4.4 % for 1–5K follower accounts, ~4.2 % platform-wide.

## Safe zones (1080×1920)

- Meta Reels ads guide (official): keep 14 % top (~269 px), 35 % bottom (~672 px), 6 % sides free.
- TikTok (low, third-party templates only): top 150–240 px, bottom 340–660 px, right 120 px (button column).
- Project choice: hook box from y 280, subtitle bottom at y 1480, picture band 280–1480 (see `ass.py` / `render.py`, learnings "Hook and subtitles sit in platform UI zones").

## Instagram specifics

- Max 5 hashtags per post since Dec 2025 (official).
- Trial Reels go to non-followers first. Judge them after 72 h (official).

## Audio

- No official LUFS target on either platform. Community default (low): −14 LUFS integrated, −1 dBTP true peak. render.py uses `loudnorm I=-14`.

## DACH audience

- Ad reach Oct 2025, 18+ (study, platform ad-reach data): Instagram 31.3 M, TikTok 23.7 M (+8.5 % y/y).
- Set the creator account language to German (low).

## TTRPG specifics

Evidence is thin. TikTok and Shorts pages could not be fetched, so view counts come from press and interviews.

- Outsider reach comes from self-contained setup → escalation → payoff bits (low). The biggest numbers are skits, e.g. "Fartbuckle the Goblin", 5.2 M views in 6 days.
- Fan-only content runs on callbacks, shipping and running gags (low). It keeps fans, it does not find new viewers.
- Sam Reich (Dropout, interview; low, his estimate): TikTok was their first discoverability platform. ~85 % of viewers find Dropout via organic social. Verticalizing hides ~66 % of the frame, so framing decides what survives.
- Critical Role YouTube (low, public view counts, one snapshot): full episodes 325K–718K views vs "Abridged" cut-downs 45K–64K.
- Bards of New York (low, hypothesis): in-character warm-ups reported as "especially viral". No numbers.
- No public source measures clip → subscriber conversion.
- German scene (low): Orkenspalter TV ~25.4K Twitch followers, #1 German TTRPG channel on Twitch.

## License

- DPCGL 2.0 rules for actual-play video (attribution, "Compatible", no "Daggerheart" in titles): see learnings entry "DPCGL 2.0 rules for audio/video" in [../learnings/pipeline.md](../learnings/pipeline.md).

## What this means for picks (our reading, not evidence)

- Prefer self-contained setup → payoff clips for reach; callback clips are for existing fans.
- Optimize for shares/sends and completion, not likes.
- Strong first 3 s, clean export, text outside the UI zones.
