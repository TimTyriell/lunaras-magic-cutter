"""Build burned-in subtitles (ASS) for one clip.

Usage: python scripts/ass.py <stem> <clip-id>
Reads words.json + meta.json (hook), config/speakers.toml (colors), config/style.toml (end card).
Writes subs.ass.
"""
import sys
import tomllib
from itertools import pairwise

from paths import CONFIG, clip_dir, duration, load

MAX_WORDS, GAP, HOOK_END, CARD_DUR = 4, 0.4, 3.0, 2.0
MIN_HOOK = 1.0  # s; a card earlier than this waits for the hook to end instead of cutting it short
MAX_CHARS = 20  # one line at 80 px within margins (24 wrapped: "Steinen schmeißen und du")
MIN_CARD = 0.5  # s; a 1-word card shorter than this takes the last word of the card before ("go!" 0.06 s)
HOLD = 1.0  # s between word starts; more = a pause hidden in a stretched word ("trägt ... Dodo" showed Dodo early)

# Platform UI: TikTok/Reels cover ~150-270 px at the top, 340-670 px at the bottom, 120 px at the right
# (learnings: "Hook and subtitles sit in platform UI zones"). Compromise with the picture band (280..1480):
# Sub: bottom-center, text box bottom (descenders included) at y=1480, outline stays clear of y=1500.
# Hook: top, opaque box (BorderStyle 3 uses OutlineColour as box, padded by Outline=20 px) from y=280,
# text from y=300; long hooks wrap to 2 lines.
HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Arial,80,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,2,2,60,120,440,1
Style: Hook,Arial,72,&H00FFFFFF,&H00FFFFFF,&H90000000,&H00000000,-1,0,0,0,100,100,0,0,3,20,0,8,120,140,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def cards(words, breaks=()):
    """Group words into 2-4 word cards; break on speaker change, pause > GAP, sentence end, MAX_CHARS,
    or a jump cut in `breaks`. A 1-word card under MIN_CARD takes the last word of the card before."""
    def joins(g, w):
        return (len(g) < MAX_WORDS and g[-1]["person"] == w["person"] and w["s"] - g[-1]["e"] <= GAP
                and w["s"] - g[-1]["s"] <= HOLD
                and len(" ".join(x["w"] for x in [*g, w])) <= MAX_CHARS and g[-1]["w"][-1] not in ".!?:"
                and not any(g[0]["s"] < b <= w["s"] for b in breaks))

    groups = []
    for w in words:
        if groups and joins(groups[-1], w):
            groups[-1].append(w)
        else:
            groups.append([w])
    for a, b in pairwise(groups):  # orphan: borrow a word unless that leaves a flash card behind
        if (len(b) == 1 and b[0]["e"] - b[0]["s"] < MIN_CARD and len(a) > 1
                and a[-2]["e"] - a[0]["s"] >= MIN_CARD and joins([a[-1]], b[0])):
            b.insert(0, a.pop())
    out = [{"person": g[0]["person"], "s": g[0]["s"], "e": g[-1]["e"], "words": [x["w"] for x in g]}
           for g in groups]
    for a, b in pairwise(out):  # close tiny gaps so cards don't flicker; short cards linger up to MIN_CARD
        if b["s"] - a["e"] < 0.3:
            a["e"] = b["s"]
        elif a["e"] - a["s"] < MIN_CARD:
            a["e"] = min(b["s"], a["s"] + MIN_CARD, *(x for x in breaks if x > a["s"]))
    return out


def seams(cuts):
    """Cut offsets where the shot changes. Cards never span them; a jump cut on the same cam may share a card."""
    return [c["offset"] for p, c in pairwise(cuts) if (c.get("cam") or c.get("person")) != (p.get("cam") or p.get("person"))]


def warnings(words, cs):
    """QA hints: cards that flash by or stick, and runs of squeezed word times (alignment failure)."""
    out = [f"card {c['e'] - c['s']:.2f} s at {c['s']:.2f}: {' '.join(c['words'])}"
           for c in cs if not 0.4 <= c["e"] - c["s"] <= 3.0]
    run = 0
    for w in words:
        run = run + 1 if w["e"] - w["s"] < 0.12 else 0
        if run == 3:
            out.append(f"3+ words under 0.12 s up to {w['e']:.2f}: check alignment in words.json")
    return out


def ass_color(hex_):
    h = hex_.lstrip("#")
    return f"&H{h[4:6]}{h[2:4]}{h[0:2]}&".upper()


def ts(t):
    cs = round(t * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def esc(text):
    return text.replace("\\", "/").replace("{", "(").replace("}", ")")


def build(words, hook, colors, cuts=()):
    """cuts (multi-cut mode): subtitle cards never span a shot change (seams); a cut's "card" text shows at its start."""
    lines = [HEADER]
    end = 0.0
    if hook:
        # never stack hook + card; a card in the first second waits for the hook instead of
        # cutting it to 0 s (Folge 7: card on cut 0 hid the hook in 4 clips)
        end = min([HOOK_END] + [c["offset"] for c in cuts if c.get("card") and c["offset"] >= MIN_HOOK])
        lines.append(f"Dialogue: 1,{ts(0)},{ts(end)},Hook,,0,0,0,,{esc(hook)}")
    shown = None  # end time of the last card line
    for prev, cut in pairwise([{}, *cuts]):
        if cut.get("card") and cut["card"] == prev.get("card"):  # same card on the next cut: extend, don't flicker
            lines[-1] = lines[-1].replace(f",{ts(shown)},", f",{ts(cut['offset'] + CARD_DUR)},", 1)
            shown = cut["offset"] + CARD_DUR
        elif cut.get("card"):
            t = max(cut["offset"], end)
            shown = t + CARD_DUR
            lines.append(f"Dialogue: 1,{ts(t)},{ts(shown)},Hook,,0,0,0,,{esc(cut['card'])}")
    for c in cards(words, seams(cuts)):
        col = colors.get(c["person"], {}).get("color", "#FFFFFF")
        text = esc(" ".join(c["words"]))
        lines.append(f"Dialogue: 0,{ts(c['s'])},{ts(c['e'])},Sub,{c['person']},0,0,0,,{{\\c{ass_color(col)}}}{text}")
    return "\n".join(lines) + "\n"


def endcard(lines, t0, dur):
    """End card text below the logo (render.py places the logo at y 240..~975).
    First line = channel in brand teal, then info lines in white."""
    out = []
    for k, text in enumerate(lines):
        y, size, col = (1040, 76, "&HDCF000&") if k == 0 else (1150 + (k - 1) * 70, 52, "&HFFFFFF&")
        out.append(f"Dialogue: 2,{ts(t0)},{ts(t0 + dur)},Sub,end,0,0,0,,"
                   f"{{\\an8\\pos(540,{y})\\fs{size}\\c{col}}}{esc(text)}")
    return out


def main(stem, cid):
    d = clip_dir(stem, cid)
    colors = tomllib.loads((CONFIG / "speakers.toml").read_text(encoding="utf-8"))
    style = tomllib.loads((CONFIG / "style.toml").read_text(encoding="utf-8"))
    meta = load(d / "meta.json") if (d / "meta.json").exists() else {}
    win = load(d / "window.json")
    hook = meta.get("hook") or win.get("hook", "")
    vdur = duration(d / "src.mp4") - win.get("endcard_audio", 0.0)  # end card starts here (render.py)
    words = [w for w in load(d / "words.json") if w["s"] < vdur]  # no subtitles over the end card
    cuts = win.get("cuts", [])
    text = build(words, hook, colors, cuts)
    for msg in warnings(words, cards(words, seams(cuts))):
        print("WARN", msg)
    end = style.get("endcard", {})
    if end.get("enabled") and win.get("format") != "short":  # short-short ends on the payoff and loops
        text += "\n".join(endcard(end["lines"], vdur, end["seconds"])) + "\n"
    (d / "subs.ass").write_text(text, encoding="utf-8")
    print(d / "subs.ass")


if __name__ == "__main__":
    main(*sys.argv[1:3])
