"""Render one clip: consent gate -> speaker-driven facecam shots -> subs -> loudnorm -> out.mp4.

Usage: python scripts/render.py <stem> <clip-id>
Exits 1 if any session participant lacks valid consent (config/consent.toml).
Shot crop boxes come from config/layouts.toml [<team>]; persons without a box get the wide shot.
"""
import subprocess
import sys
import tomllib
from itertools import pairwise

import dice
from paths import CONFIG, ROOT, clip_dir, dump, duration, load, session_dir, team

MIN_SHOT = 1.5
FIT = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
BAND_Y, BAND_H = 280, 1200  # picture band; hook box and subtitles overlap its edges (see ass.py styles)
PIP_TOP, PIP_H = 1030, 700  # layout "pip": speaker card under the map (map 1080x735 + 15 px gap), y 1030..1730
# 2026-10-22 user (Folge 9 review): card 450 high was too small -> grows downward, top edge fixed at 1030.
# PIP_W caps landscape cams (GM deniz 560x410: 956 wide looked too big -> 720x527, was 615x450); portrait cams unaffected.
PIP_W = 720
# Background styles: (source, filter). "map" = layouts.toml [<team>].map region (the VTT battle map).
# ponytail: values set by eye (research found no tested numbers); map-teal = cool complement to warm faces/overlay.
BG_STYLES = {
    "self": ("self", "boxblur=20:2"),
    "map": ("map", "boxblur=30:2,eq=brightness=-0.15:saturation=0.85"),
    "map-teal": ("map", ("boxblur=30:2,eq=brightness=-0.12:saturation=0.9,"
                         "colorbalance=rs=-0.2:gs=0.05:bs=0.25:rm=-0.15:gm=0.03:bm=0.15,vignette=PI/4")),
}


def consent_missing(persons, consent):
    """Persons without dated consent covering tiktok + AI processing, or revoked."""
    bad = []
    for p in sorted(persons):
        c = consent.get(p, {})
        if not (c.get("date") and "tiktok" in c.get("platforms", []) and c.get("ai_processing") is True
                and not c.get("revoked")):
            bad.append(p)
    return bad


def shots(words, duration):
    """Speaker turns -> contiguous shots covering [0, duration]; shots < MIN_SHOT merge into neighbour."""
    turns = []
    for w in words:
        if not turns or turns[-1]["person"] != w["person"]:
            turns.append({"person": w["person"], "s": w["s"]})
    if not turns:
        return [{"person": None, "s": 0.0, "e": duration}]
    turns[0]["s"] = 0.0
    for a, b in pairwise(turns):
        a["e"] = b["s"]
    turns[-1]["e"] = duration
    out = []
    for t in turns:
        if out and (t["e"] - t["s"] < MIN_SHOT or out[-1]["person"] == t["person"]):
            out[-1]["e"] = t["e"]
        else:
            out.append(dict(t))
    if len(out) > 1 and out[0]["e"] - out[0]["s"] < MIN_SHOT:
        out[1]["s"] = 0.0
        out.pop(0)
    return out


def crop(box):
    """'crop=w:h:x:y,' (filter + trailing comma) or '' for full frame."""
    return f"crop={box[2]}:{box[3]}:{box[0]}:{box[1]}," if box else ""


def shot_filter(i, shot, box, bg_box=None, bg_fx=BG_STYLES["self"][1]):
    """Box (facecam) or full frame, fit into the picture band, over a background fill.
    Background = bg_box region of the frame (e.g. the VTT map) or the shot itself, through bg_fx.
    ponytail: fit, not fill - stream cams are ~300x350, a 9:16 fill crop would be ~200 px wide and mush.
    Band y 280..1480; the hook box (from y 280) and subtitles (bottom edge 1480) sit on its edges, off the faces."""
    src = f"[0:v]trim=start={shot['s']:.3f}:end={shot['e']:.3f},setpts=PTS-STARTPTS"
    return (f"{src},split[b{i}][f{i}];[b{i}]{crop(bg_box or box)}{FIT},{bg_fx}[bg{i}];"
            f"[f{i}]{crop(box)}scale=1080:{BAND_H}:force_original_aspect_ratio=decrease[fg{i}];"
            f"[bg{i}][fg{i}]overlay=(W-w)/2:{BAND_Y}+({BAND_H}-h)/2,setsar=1[v{i}]")


def pip_filter(i, shot, box, pip, bg_box=None, bg_fx=BG_STYLES["self"][1]):
    """Layout "pip": box (the map) full width at the top of the band, the speaker's card (pip) below it.
    ponytail: assumes a landscape box (map 845x575 -> 1080x735); a taller box would overlap the card."""
    src = f"[0:v]trim=start={shot['s']:.3f}:end={shot['e']:.3f},setpts=PTS-STARTPTS"
    return (f"{src},split=3[b{i}][f{i}][p{i}];[b{i}]{crop(bg_box or box)}{FIT},{bg_fx}[bg{i}];"
            f"[f{i}]{crop(box)}scale=1080:-2[fg{i}];"
            f"[p{i}]{crop(pip)}scale={PIP_W}:{PIP_H}:force_original_aspect_ratio=decrease[pp{i}];"
            f"[bg{i}][fg{i}]overlay=0:{BAND_Y}[m{i}];"
            f"[m{i}][pp{i}]overlay=(W-w)/2:{PIP_TOP},setsar=1[v{i}]")


def dice_filter(i, shot, map_box, k):
    """Dice-roll insert (EDL cut "dice", frames from dice.py as input k): the shot's map, full screen, lightly
    blurred (user 2026-10-25: "leicht unscharf"), dice PNGs (alpha) on top; last frame holds if the cut runs longer."""
    src = f"[0:v]trim=start={shot['s']:.3f}:end={shot['e']:.3f},setpts=PTS-STARTPTS"
    return (f"{src},{crop(map_box)}{FIT},boxblur=6:1,eq=brightness=-0.25:saturation=0.9,vignette=PI/4[bg{i}];"
            f"[{k}:v]format=rgba[dk{i}];[bg{i}][dk{i}]overlay=0:0,setsar=1[v{i}]")


def endcard_filter(map_box, sec):
    """[ec]: first frame's map region, blurred + dark, held for sec, logo (input 1) on top (y 240, 720 wide).
    Text lines come from ass.py (endcard) so they share the subtitle font pipeline."""
    return (f"[0:v]trim=end_frame=1,setpts=PTS-STARTPTS,{crop(map_box)}{FIT},boxblur=30:2,"
            f"eq=brightness=-0.3:saturation=0.8,tpad=stop_mode=clone:stop_duration={sec}[ebg];"
            f"[1:v]scale=720:-1,format=rgba[logo];"
            f"[ebg][logo]overlay=(W-w)/2:240:shortest=1,format=yuv420p,setsar=1[ec]")


def bleep_filter(cuts):
    """Censor: EDL cut "bleep": [[s, e], ...] (session seconds) -> mute [0:a] there, lay a 1 kHz tone over -> [a0]."""
    wins = [(c["offset"] + s - c["start"], c["offset"] + e - c["start"]) for c in cuts for s, e in c.get("bleep", [])]
    if not wins:
        return "[0:a]anull[a0]"
    on = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in wins)
    return (f"[0:a]volume='if({on},0,1)':eval=frame[am];"
            f"sine=f=1000:r=48000,aformat=channel_layouts=stereo,volume='if({on},1,0)':eval=frame[bt];"  # sine is 1/8 amplitude (~-21 dB), near speech level
            "[am][bt]amix=inputs=2:duration=first:normalize=0[a0]")


def multi_shots(cuts):
    """Multi-cut: one shot per EDL cut; cam overrides person (reaction shots, "map"); speaker kept for pip.
    Optional cut "box": [x, y, w, h] overrides the cam's layouts.toml box (zoom into the map)."""
    return [{"person": c.get("cam") or c.get("person"), "speaker": c.get("person"),
             "s": c["offset"], "e": c["offset"] + c["dur"], **{k: c[k] for k in ("box", "dice") if k in c}}
            for c in cuts]


def main(stem, cid, *flags):
    """--bg <style>: override config/style.toml and write out_<style>.mp4 (A/B comparison).
    --layout pip|full: override style.toml layout for map shots (pip = speaker card under the map),
    writes out_<layout>.mp4."""
    d = clip_dir(stem, cid)
    consent = tomllib.loads((CONFIG / "consent.toml").read_text(encoding="utf-8"))
    # ponytail: gate on whole session roster, since the wide shot shows every cam
    persons = {s["person"] for s in load(session_dir(stem) / "segments.json")}
    bad = consent_missing(persons, consent)
    if bad:
        sys.exit(f"CONSENT GATE: missing/invalid consent for {bad} in config/consent.toml")

    layout = tomllib.loads((CONFIG / "layouts.toml").read_text(encoding="utf-8")).get(team(stem), {})
    win = load(d / "window.json")
    dur = duration(d / "src.mp4")
    vdur = dur - win.get("endcard_audio", 0.0)  # src tail whose audio runs under the end card (fetch.py)
    if win.get("mode") == "multi":
        plan = multi_shots(win["cuts"])
        for s in plan:
            s["e"] = min(s["e"], vdur)
    else:
        plan = shots(load(d / "words.json"), vdur)
    dump(plan, d / "shots.json")
    cfg = tomllib.loads((CONFIG / "style.toml").read_text(encoding="utf-8"))
    style = flags[flags.index("--bg") + 1] if "--bg" in flags else cfg["bg"]
    lay = flags[flags.index("--layout") + 1] if "--layout" in flags else cfg.get("layout", "full")
    pip = lay == "pip"
    out = ("out" + (f"_{style}" if "--bg" in flags else "") + (f"_{lay}" if "--layout" in flags else "")) + ".mp4"
    source, bg_fx = BG_STYLES[style]
    bg_box = layout.get("map") if source == "map" else None

    end = cfg.get("endcard", {})
    with_end = end.get("enabled") and win.get("format") != "short"  # short-short ends on the payoff and loops
    dice_in = []  # extra inputs after src.mp4 (0) and the end-card logo (1)

    def shot(i, s):
        if s.get("dice"):
            dice_in.extend(["-framerate", str(dice.FPS), "-i", str(dice.frames(s["dice"], s["e"] - s["s"], d) / "%03d.png")])
            return dice_filter(i, s, layout.get("map"), int(with_end) + len(dice_in) // 4)
        box = s.get("box") or layout.get(s["person"])
        if pip and s["person"] == "map" and s.get("speaker") in layout:
            return pip_filter(i, s, box, layout[s["speaker"]], bg_box, bg_fx)
        return shot_filter(i, s, box, bg_box, bg_fx)

    fc = bleep_filter(win.get("cuts", [])) + ";" + ";".join(shot(i, s) for i, s in enumerate(plan))
    fc += ";" + "".join(f"[v{i}]" for i in range(len(plan))) + f"concat=n={len(plan)}:v=1:a=0[cv]"
    inputs = ["-i", "src.mp4"]
    if with_end:
        sec = end["seconds"]
        total = vdur + sec
        # audio under the end card: long fade at the very end; otherwise fade before the card, then silence
        # silent card: short fade so a last word cut at its end keeps its tail (kraken v5 "bewegen.")
        fade_st, fade_d = (total - 1.0, 1.0) if vdur < dur else (dur - 0.05, 0.05)
        inputs += ["-loop", "1", "-t", f"{sec}", "-i", str(ROOT / end["logo"])]
        fc += f";{endcard_filter(layout.get('map'), sec)}"
        fc += ";[cv][ec]concat=n=2:v=1:a=0[cvv];[cvv]ass=subs.ass[v]"
        fc += (f";[a0]loudnorm=I=-14:TP=-1:LRA=11,alimiter=limit=0.891:level=false,afade=t=out:st={fade_st:.3f}:d={fade_d},"
               f"apad=whole_dur={total:.3f},atrim=end={total:.3f}[a]")
    else:
        fc += ";[cv]ass=subs.ass[v];[a0]loudnorm=I=-14:TP=-1:LRA=11,alimiter=limit=0.891:level=false[a]"
    # cwd=clip dir so the ass filter gets a relative path (Windows drive colons break filter args)
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, *dice_in, "-filter_complex", fc,
                    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
                    "-movflags", "+faststart", out], cwd=d, check=True)
    print(f"{len(plan)} shots, bg={style} -> {d / out}")


if __name__ == "__main__":
    main(*sys.argv[1:])
