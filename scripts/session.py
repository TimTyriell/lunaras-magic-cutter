"""Adapter: pnp-crawl final transcript + OKF session file -> work/<stem>/.

Usage: python scripts/session.py <stem>
Writes segments.json, context.md, chunks/chunk_NN.txt (15 min, 30 s overlap).
"""
import re
import sys

from paths import FINAL, OKF_SESSIONS, dump, load, session_dir

LABEL = re.compile(r"^(.*?)\s*\((.*)\)$")
CHUNK, OVERLAP = 900, 30


def parse_speaker(label):
    m = LABEL.match(label)
    person, character = (m.group(1), m.group(2)) if m else (label, "")
    return person.strip().lower(), character.strip()


def hms(t):
    t = int(t)
    return f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}"


def line(s):
    return f"[{s['start']:.1f}-{s['end']:.1f} | {hms(s['start'])}] {s['person']} ({s['character']}): {s['text']}"


def main(stem):
    src = load(FINAL / f"{stem}.json")
    segs = []
    for s in src["segments"]:
        person, character = parse_speaker(s["speaker"])
        segs.append({"start": s["start"], "end": s["end"], "person": person,
                     "character": character, "text": s["text"].strip()})
    out = session_dir(stem)
    dump(segs, out / "segments.json")

    roster = sorted({(s["person"], s["character"]) for s in segs})
    okf = OKF_SESSIONS / f"{src['video_date']}.md"
    ctx = [f"# {src['video_title']}", f"date: {src['video_date']}  url: {src['video_url']}", "",
           "## Roster (person key -> character)", *[f"- {p}: {c}" for p, c in roster], ""]
    if okf.exists():
        body = okf.read_text(encoding="utf-8").split("---", 2)[-1]  # drop YAML frontmatter
        ctx += ["## OKF session summary", body.strip()]
    (out / "context.md").write_text("\n".join(ctx), encoding="utf-8")

    chunks = out / "chunks"
    chunks.mkdir(exist_ok=True)
    end, t, n = segs[-1]["end"], 0.0, 0
    while t < end:
        part = [line(s) for s in segs if s["end"] > t - OVERLAP and s["start"] < t + CHUNK]
        (chunks / f"chunk_{n:02d}.txt").write_text("\n".join(part), encoding="utf-8")
        t, n = t + CHUNK, n + 1
    print(f"{len(segs)} segments, {n} chunks, okf={'yes' if okf.exists() else 'no'} -> {out}")


if __name__ == "__main__":
    main(sys.argv[1])
