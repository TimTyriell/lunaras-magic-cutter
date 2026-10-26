"""Subtitle word times for a multi-cut clip: probe words snapped to speech onsets (replaces words.py for EDL clips).

Usage: python scripts/retime.py <stem> <id>   (after fetch.py; GPU only for cuts the probe files do not cover)
Why not words.py: Whisper on a cut with context drops words the longer probe window hears, and every Whisper word
start runs 0.3-0.9 s off (learnings "Whisper word times 0.3-0.6 s off", "Whisper misses words in the 10 s context
run"). Here the words come from probe windows (work/<session>/scripts/probe*.txt, written by probe.py; cuts not
covered are probed first into probe_auto.txt), each phrase start is snapped to the nearest speech onset from
silencedetect, the rest of the phrase moves along, and words.align_text puts the verified EDL text on those times.
Prints `<-- check` for a cut where less than 60 % of its words were heard (timing interpolated there).
Folge 9 scratch version: work/Season 1 Folge 9 Team A/scripts/tools/retime.py.
"""
import re
import subprocess
import sys

from edgecheck import probe_words
from paths import clip_dir, dump, load, session_dir, source_path
from probe import windows
from words import MAX_WORD, align_text

CTX = 1.5  # s of probe context around a cut
ISLAND_GAP = 0.2  # only pauses >= this mark a phrase start ("von der | Roten" has a 0.1 s dip inside the phrase)
SNAP = 0.7  # s a probe phrase start may move to reach a speech onset


def silences(stem, a, b):
    r = subprocess.run(["ffmpeg", "-v", "info", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", str(source_path(stem)),
                        "-vn", "-af", "silencedetect=noise=-35dB:d=0.06", "-f", "null", "-"],
                       check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
    st = [a + float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    en = [a + float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return list(zip(st, en))


def uncovered(cuts, wins):
    """Probe windows still needed: the cut +-CTX must lie in one existing window; neighbours are merged."""
    need = []
    for c in cuts:
        if c.get("text", "").strip() and not any(a <= c["start"] - 0.6 and c["end"] + 0.8 <= b for a, b in wins):
            a, b = c["start"] - CTX, c["end"] + CTX
            if need and a <= need[-1][1] + 1.0:
                need[-1][1] = b
            else:
                need.append([a, b])
    return need


def ensure_probe(stem, cuts):
    need = uncovered(cuts, probe_words(stem)[1])
    if need:
        print(f"probing {len(need)} uncovered window(s): " + ", ".join(f"{a:.0f}-{b:.0f}" for a, b in need))
        out = session_dir(stem) / "scripts" / "probe_auto.txt"
        with out.open("a", encoding="utf-8") as f:
            for a, b, lines in windows(stem, [x for w in need for x in w]):
                f.write(f"== {a:.2f}-{b:.2f}\n" + "\n".join(lines) + "\n")
    return probe_words(stem)[0]


def shifted(stem, c, pw, tail):
    """Probe words of one cut with each phrase start snapped to a speech onset -> [(session s, word)]."""
    cw = [(t, w) for t, w in pw if c["start"] - 0.6 <= t < c["end"] - tail]
    # silencedetect from the cut start: an island that already runs at the cut head gives no onset there, so an
    # early Whisper word cannot snap to the silent head (Folge 9 zebros: cards 0.5-0.7 s before the voice)
    onsets = [e for s, e in silences(stem, c["start"] - 0.1, c["end"] - tail) if e - s >= ISLAND_GAP]
    delta, adj = 0.0, []
    for k, (t, w) in enumerate(cw):
        prev = adj[-1][0] if adj else -1e9
        # phrase start = gap after the previous word's estimated END (start-to-start gaps hide long words)
        if k == 0 or t - (cw[k - 1][0] + 0.07 * len(cw[k - 1][1]) + 0.15) > 0.15:
            near = [o for o in onsets if abs(o - t) <= SNAP and o > prev + 0.15]  # never before the last word
            delta = (min(near, key=lambda o: abs(o - t)) - t) if near else delta
        adj.append((max(t + delta, prev + 0.05), w))
    # words the shift pushed past the cut end are spoken inside it (the end sits in silence): clamp, don't drop
    cend = c["end"] - tail
    keep = [(t, w) for t, w in adj if t >= c["start"] - 0.05]
    return [(min(t, cend - 0.15 * (len(keep) - k)), w) for k, (t, w) in enumerate(keep) if t < cend + 0.8]


def rebuild(stem, cid, pw):
    d = clip_dir(stem, cid)
    win = load(d / "window.json")
    words = []
    for i, c in enumerate(win["cuts"]):
        tail = win.get("endcard_audio", 0.0) if i == len(win["cuts"]) - 1 else 0.0  # audio under the end card
        lo, hi = c["offset"], c["offset"] + c["dur"] - tail
        if not c.get("text", "").strip():
            continue
        cw = shifted(stem, c, pw, tail)
        ws = []
        for k, (t, w) in enumerate(cw):
            s = lo + max(0.0, t - c["start"])
            e = s + 0.07 * len(w) + 0.15
            if k + 1 < len(cw):
                e = min(e, lo + cw[k + 1][0] - c["start"])
            ws.append({"w": w, "s": round(s, 3), "e": round(min(e, s + MAX_WORD - 0.01, hi), 3)})
        n = len(c["text"].split())
        flag = "  <-- check" if len(cw) < 0.6 * n else ""
        words += [{**w, "person": c["person"]} for w in align_text(c["text"], ws, lo, hi)]
        print(f"{cid} cut {i:2}: probe {len(cw):3} / text {n:3} words, {lo:6.2f}-{hi:6.2f}{flag}")
    dump(words, d / "words.json")
    print(f"{len(words)} words -> {d / 'words.json'}")


def main(stem, cid):
    win = load(clip_dir(stem, cid) / "window.json")
    if win.get("mode") != "multi":
        sys.exit("single-window clip: use words.py")
    rebuild(stem, cid, ensure_probe(stem, win["cuts"]))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(*sys.argv[1:3])
