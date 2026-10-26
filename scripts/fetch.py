"""Build a clip's src.mp4 from a locally cached copy of the episode.

Usage: python scripts/fetch.py <stem> <clip-id>
First run per episode downloads the full video once to work/<session>/source.mp4
(1080p, German original audio). Section downloads from YouTube stall (throttled HTTP seek).
Single mode: window of candidates.json entry (+-PAD).
Multi-cut mode (scripts/<id>.edl.json exists): cuts joined in EDL order; window.json gets "cuts"
with offset/dur on the src.mp4 timeline.
"""
import subprocess
import sys
import tomllib
from itertools import pairwise

from paths import (
    CONFIG,
    FINAL,
    YTDLP,
    clip_dir,
    dump,
    edl_path,
    load,
    session_dir,
    source_path,
    ytdlp_auth,
)

PAD = 2.0
LEAD, TAIL = 0.2, 0.3  # multi-cut breathing room (s); research: 50-200 ms typical, user found 0 too clipped
FADE = 0.03  # ponytail: 30 ms audio fades hide clicks at jump cuts; crossfades if cuts feel harsh
# Video has an auto-dubbed en-US audio track; pick the original (German) one explicitly.
FORMAT = "bv*[height<=1080][vcodec^=avc1]+ba[format_note*=original]/bv*[height<=1080]+ba[language^=de]/bv*+ba"


def source(stem):
    """Full episode, cached once per session folder."""
    out = source_path(stem)
    if not out.exists():
        url = load(FINAL / f"{stem}.json")["video_url"]
        subprocess.run([str(YTDLP), *ytdlp_auth(), url, "-f", FORMAT, "--merge-output-format", "mp4",
                        "-o", str(out)], check=True)
    return out


def concat_filter(durs, joined=()):
    """Join N inputs (video+audio) with short audio fades at every seam, except where the source runs on
    (joined[i]: input i+1 continues input i, e.g. a cam switch mid-line; fades there are audible dropouts)."""
    j = [*joined, *[False] * len(durs)]
    parts = []
    for i, d in enumerate(durs):
        fx = ([] if i and j[i - 1] else [f"afade=t=in:d={FADE}"]) + \
             ([] if j[i] else [f"afade=t=out:st={max(0.0, d - FADE):.3f}:d={FADE}"])
        parts.append(f"[{i}:a]{','.join(fx) or 'anull'}[a{i}]")
    pairs = "".join(f"[{i}:v][a{i}]" for i in range(len(durs)))
    return ";".join(parts) + f";{pairs}concat=n={len(durs)}:v=1:a=1[v][a]"


def padded(cuts):
    """Breathing room around EDL cuts (they are set on word boundaries and felt clipped).
    No padding at seams where the next cut continues the source directly. Per-cut "lead"/"tail" override."""
    out = []
    for i, c in enumerate(cuts):
        prev_joined = i > 0 and abs(cuts[i - 1]["end"] - c["start"]) < 0.05
        next_joined = i + 1 < len(cuts) and abs(cuts[i + 1]["start"] - c["end"]) < 0.05
        lead = 0.0 if prev_joined else c.get("lead", LEAD)
        tail = 0.0 if next_joined else c.get("tail", TAIL)
        out.append({**c, "start": round(max(0.0, c["start"] - lead), 3), "end": round(c["end"] + tail, 3)})
    return out


def cut(src, spans, out):
    """spans [(start, end)] in session seconds -> one re-encoded mp4 (fast input seek per span)."""
    inputs = [a for s, e in spans for a in ("-ss", f"{s:.3f}", "-t", f"{e - s:.3f}", "-i", str(src))]
    joined = [abs(b[0] - a[1]) < 0.01 for a, b in pairwise(spans)]
    fc = concat_filter([e - s for s, e in spans], joined)
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", fc,
                    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                    "-c:a", "aac", "-b:a", "192k", str(out)], check=True)


def endcard_overlap():
    """Seconds of extra source audio to run under the end card (style.toml [endcard] audio_overlap)."""
    end = tomllib.loads((CONFIG / "style.toml").read_text(encoding="utf-8")).get("endcard", {})
    return float(end["seconds"]) if end.get("enabled") and end.get("audio_overlap") else 0.0


def main(stem, cid):
    d = clip_dir(stem, cid)
    d.mkdir(parents=True, exist_ok=True)
    src = source(stem)
    ov = endcard_overlap()
    if edl_path(stem, cid).exists():
        edl = load(edl_path(stem, cid))
        # per clip; 0 = silent end card (kraken v5: "Ton ab"); format "short" has no end card at all (rules.md Formats)
        ov = 0.0 if edl.get("format") == "short" else edl.get("endcard_audio", ov)
        spans = padded(edl["cuts"])
        spans[-1] = {**spans[-1], "end": round(spans[-1]["end"] + ov, 3)}
        cut(src, [(c["start"], c["end"]) for c in spans], d / "src.mp4")
        cuts, off = [], 0.0
        for c in spans:
            cuts.append({**c, "offset": round(off, 3), "dur": round(c["end"] - c["start"], 3)})
            off += c["end"] - c["start"]
        meta = {k: v for k, v in edl.items() if k != "cuts"}
        dump({"stem": stem, "mode": "multi", **meta, "id": cid, "cuts": cuts, "endcard_audio": ov,
              "t0": min(c["start"] for c in cuts), "t1": max(c["end"] for c in cuts)}, d / "window.json")
    else:
        cand = next(c for c in load(session_dir(stem) / "candidates.json") if c["id"] == cid)
        ov = 0.0 if cand.get("format") == "short" else ov
        t0, t1 = max(0.0, cand["start"] - PAD), cand["end"] + PAD + ov
        cut(src, [(t0, t1)], d / "src.mp4")
        dump({"stem": stem, "id": cid, "t0": t0, "t1": t1, "endcard_audio": ov, **cand}, d / "window.json")
    print(d / "src.mp4")


if __name__ == "__main__":
    main(*sys.argv[1:3])
