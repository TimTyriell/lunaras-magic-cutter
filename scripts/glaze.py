"""Render a visual-only glaze/fancam edit: beat-grid shots from several sessions, no speech.

Usage: python scripts/glaze.py <plan.json>
Plan: {"id", "bpm", "intro"?, "shots": [{"stem", "t", "beats", "src", "box"?, "fx"?, "card"?}]}
  src  = layouts.toml person/map box name ("deniz", "map", "tim", ...), "box" = [x,y,w,h] source-pixel
         sub-crop that overrides it (e.g. tight on a mini). t = session seconds, beats on the bpm grid.
  fx   = punch (zoom-in hit), push (slow zoom), stutter (zoom steps on every half beat, box centred on
         the target), glide (smooth accelerating zoom to 2x, box centred on the target), pulse (zoom bounce
         on every beat: hectic without flashing), slow (0.7x), shake, flash (white in), strobe (white blip
         per beat; counts as a photosensitive flash, see learnings), rgb (colour split), glow, warm.
  focus = [x, y] source pixels: zooms drift their centre onto this point (fully centred at 2x).
  delogo = [x, y, w, h] source pixels: blur out a static artefact (e.g. the VTT mouse cursor).
  card = short text (1-3 words) centred low; minimal text by design (glaze = visuals).
  intro = {"clip": <rendered mp4, repo-relative>, "end": s}: hook clip with its own audio, played first.
Writes <plan dir>/<id>.mp4, 1080x1920 30 fps; glaze part silent (music is added on TikTok).
Consent gate as render.py, over every session used.
"""
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

from paths import CONFIG, ROOT, load, session_dir, source_path, team
from render import consent_missing

FPS = 30
SLOW = 0.7
# ponytail: effect strengths set by eye; tune here.
FX = {
    "flash": "fade=t=in:st=0:d=0.18:color=white",
    # RGB for the blend: screen on YUV planes tints everything magenta (seen in joar-glaze-v1)
    "glow": ("format=gbrp,split[g0][g1];[g1]gblur=sigma=18[g2];[g0][g2]blend=all_mode=screen:all_opacity=0.35,"
             "format=yuv420p"),
    "warm": "colorbalance=rs=0.06:gs=0.02:bs=-0.05,eq=saturation=1.08",  # warm, never darker (see memory: no darkening)
    "shake": "scale=1134:2016,crop=1080:1920:x='27+20*sin(t*45)':y='48+20*cos(t*38)'",
    "rgb": "rgbashift=rh=-10:bh=10",
}


def strobe(beat):
    """White blip (60 ms) at the start of every beat. 0.25: 0.45 gave 2.5 flashes/s (WCAG limit 3), see learnings."""
    return f"eq=brightness='0.25*lt(mod(t,{beat:.4f}),0.06)':eval=frame"


def zoom(fx, frames, beat=0.5, focus=None):
    """zoompan expression: push (slow +8 %), stutter (+25 % per half beat, max 2x), glide (ease-in to 2x),
    punch (1.18 -> 1 in 8 frames), pulse (+7 % bounce decaying over 5 frames on every beat)."""
    z = "1"
    if "push" in fx:
        z = f"1+0.08*on/{frames}"
    if "stutter" in fx:
        z = f"min(2,1+0.25*floor(on/{beat * FPS / 2:.3f}))"
    if "glide" in fx:
        z = f"1+pow(on/{frames},2)"
    if "punch" in fx:
        z = f"({z})+0.18*max(0,1-on/8)"
    if "pulse" in fx:
        z = f"({z})+0.07*max(0,1-mod(on,{beat * FPS:.3f})/5)"
    if z == "1":
        return ""
    # centre drifts from frame centre to focus as zoom goes 1 -> 2, clamped inside the frame
    cx, cy = focus or ("iw/2", "ih/2")
    x = f"max(0,min(iw-iw/zoom,iw/2+({cx}-iw/2)*min(1,zoom-1)-iw/zoom/2))"
    y = f"max(0,min(ih-ih/zoom,ih/2+({cy}-ih/2)*min(1,zoom-1)-ih/zoom/2))"
    # 2x upscale first: zoompan rounds x/y to whole pixels, which makes slow zooms judder
    return f"scale=2160:3840:flags=lanczos,zoompan=z='{z}':d=1:x='{x}':y='{y}':s=1080x1920:fps={FPS}"


def focus_px(focus, box):
    """Source-pixel focus -> pixel in the 2160x3840 zoompan input (box cover-scaled and centre-cropped)."""
    s = max(2160 / box[2], 3840 / box[3])
    return (round((focus[0] - box[0]) * s - (box[2] * s - 2160) / 2),
            round((focus[1] - box[1]) * s - (box[3] * s - 3840) / 2))


def chain(shot, box, dur, beat=0.5):
    """Video filter for one shot: crop box -> fill 9:16 -> speed -> zoom -> effects."""
    fx = shot.get("fx", [])
    dl = shot.get("delogo")
    parts = [dl and f"delogo=x={dl[0]}:y={dl[1]}:w={dl[2]}:h={dl[3]}",
             f"crop={box[2]}:{box[3]}:{box[0]}:{box[1]}",
             "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1"]
    if "slow" in fx:
        parts.append(f"setpts=PTS/{SLOW}")
    parts.append(f"fps={FPS},trim=duration={dur:.3f},setpts=PTS-STARTPTS")
    parts.append(zoom(fx, round(dur * FPS), beat, shot.get("focus") and focus_px(shot["focus"], box)))
    parts += [FX[k] for k in ("shake", "rgb", "warm", "glow", "flash") if k in fx]
    if "strobe" in fx:
        parts.append(strobe(beat))
    return ",".join(p for p in parts if p)


def ass_cards(cards):
    """cards: [(start, end, text)] -> ASS document (bold, centred low, soft shadow)."""
    def ts(s):
        return f"{int(s // 3600)}:{int(s % 3600 // 60):02}:{s % 60:05.2f}"
    head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
            "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
            "Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: Card,Arial,96,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,6,0,1,4,6,2,80,80,360,1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    return head + "".join(f"Dialogue: 0,{ts(a)},{ts(b)},Card,,0,0,0,,{{\\fad(80,80)}}{t}\n" for a, b, t in cards)


def plan(shots, bpm):
    """Shot start/end on the beat grid."""
    beat, t, out = 60 / bpm, 0.0, []
    for s in shots:
        d = s["beats"] * beat
        out.append((t, t + d))
        t += d
    return out


def main(plan_path):
    p = Path(plan_path).resolve()
    spec = load(p)
    consent = tomllib.loads((CONFIG / "consent.toml").read_text(encoding="utf-8"))
    persons = {s["person"] for stem in {x["stem"] for x in spec["shots"]}
               for s in load(session_dir(stem) / "segments.json")}
    bad = consent_missing(persons, consent)
    if bad:
        sys.exit(f"CONSENT GATE: missing/invalid consent for {bad} in config/consent.toml")

    layouts = tomllib.loads((CONFIG / "layouts.toml").read_text(encoding="utf-8"))
    times = plan(spec["shots"], spec["bpm"])
    tmp = Path(tempfile.mkdtemp(prefix="glaze_"))
    parts = []
    for i, (shot, (a, b)) in enumerate(zip(spec["shots"], times, strict=True)):
        box = shot.get("box") or layouts[team(shot["stem"])][shot["src"]]
        dur = b - a
        read = dur * (1 / SLOW if "slow" in shot.get("fx", []) else 1) + 0.5
        out = tmp / f"{i:02}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{shot['t']:.3f}", "-t", f"{read:.3f}",
                        "-i", str(source_path(shot["stem"])), "-an", "-vf", chain(shot, box, dur, 60 / spec["bpm"]),
                        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(out)],
                       check=True)
        parts.append(out)

    (tmp / "list.txt").write_text("".join(f"file '{x.name}'\n" for x in parts), encoding="utf-8")
    (tmp / "cards.ass").write_text(ass_cards([(a, b, s["card"]) for s, (a, b) in zip(spec["shots"], times)
                                              if s.get("card")]), encoding="utf-8")
    dst = p.parent / f"{spec['id']}.mp4"
    glaze = tmp / "glaze.mp4" if spec.get("intro") else dst
    enc = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000"]
    # cwd=tmp so the ass filter gets a relative path (Windows drive colons break filter args)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", "list.txt",
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-vf", "ass=cards.ass",
                    *enc, "-shortest", str(glaze)], check=True, cwd=tmp)
    total = times[-1][1]
    if spec.get("intro"):
        intro = spec["intro"]
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-t", f"{intro['end']:.3f}", "-i", str(ROOT / intro["clip"]),
                        "-i", str(glaze), "-filter_complex",
                        (f"[0:v]fps={FPS},setsar=1[v0];[1:v]setsar=1[v1];"
                         f"[0:a]afade=t=out:st={intro['end'] - 0.08:.3f}:d=0.08[a0];"
                         "[v0][a0][v1][1:a]concat=n=2:v=1:a=1[v][a]"),
                        "-map", "[v]", "-map", "[a]", *enc, str(dst)], check=True)
        total += intro["end"]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(dst), "-c", "copy", "-movflags", "+faststart",
                    str(tmp / "fs.mp4")], check=True)
    (tmp / "fs.mp4").replace(dst)
    print(f"{len(parts)} shots, {total:.1f} s -> {dst}")


if __name__ == "__main__":
    main(*sys.argv[1:])
