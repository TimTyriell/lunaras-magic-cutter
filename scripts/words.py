"""Word timestamps for one clip via faster-whisper (run with pnp-crawl ttrpg_env python).

Usage: <ttrpg_env python> scripts/words.py <stem> <clip-id> [--apply]
--apply: patch persons from clips/<id>/corrections.json (speaker-checker output) instead.
Writes clips/<id>/words.json: [{w, s, e, person}], times relative to src.mp4.
Person comes from pnp-crawl segments by max overlap (nearest segment if none).
Multi-cut (window.json mode "multi"): each cut transcribed from source.mp4 with context; if the
cut has "text" (verified), that text is the subtitle and Whisper only supplies timings.
Person from the EDL cut, falling back to segment overlap.
"""
import difflib
import re
import subprocess
import sys

from paths import clip_dir, dump, load, session_dir, source_path

CONTEXT = 10.0  # s of audio around each multi-cut; 3 s was too little for Whisper to keep short cuts
MAX_WORD = 1.2  # s; longer Whisper words are stretched over speech Whisper missed (gold-saga "langsam" 5.6 s)
PACE = 0.08  # s per (char + 1) of untimed words at a cut start; the cut may open on silence ("Ich" 2.3 s early)


def assign(words, segs, t0):
    for w in words:
        a, b = t0 + w["s"], t0 + w["e"]
        best = max(segs, key=lambda s: (min(b, s["end"]) - max(a, s["start"]),
                                        -abs((s["start"] + s["end"]) / 2 - (a + b) / 2)))
        w["person"] = best["person"]
    return words


def keep_in_cut(ws, cut, a):
    """Words transcribed from source audio starting at session time a -> words inside the cut,
    on the src.mp4 timeline (cut offset), end clamped to the cut."""
    out = []
    for w in ws:
        s = a + w["s"]
        if cut["start"] - 0.05 <= s < cut["end"]:
            rel = cut["offset"] + max(0.0, s - cut["start"])
            end = cut["offset"] + min(a + w["e"], cut["end"]) - cut["start"]
            out.append({"w": w["w"], "s": round(rel, 3), "e": round(max(end, rel + 0.05), 3)})
    return out


def _norm(t):
    return re.sub(r"[^\w]", "", t.lower())


def align_text(text, ws, lo, hi):
    """Subtitle words = verified EDL text; timings from Whisper words ws via difflib.
    Equal and same-length replace blocks take Whisper times, except words longer than MAX_WORD
    (no trusted anchor). Leftover tokens are spread by length between their timed neighbours
    (or across [lo, hi] if nothing matched)."""
    toks = text.split()
    times = [None] * len(toks)
    sm = difflib.SequenceMatcher(a=[_norm(t) for t in toks], b=[_norm(w["w"]) for w in ws], autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal" or (op == "replace" and i2 - i1 == j2 - j1):
            for k in range(i2 - i1):
                w = ws[j1 + k]
                if w["e"] - w["s"] <= MAX_WORD:
                    times[i1 + k] = (w["s"], w["e"])
    i = 0
    while i < len(toks):
        if times[i]:
            i += 1
            continue
        j = i
        while j < len(toks) and times[j] is None:
            j += 1
        a = times[i - 1][1] if i else lo
        b = times[j][0] if j < len(toks) else hi
        wts = [len(t) + 1 for t in toks[i:j]]  # ponytail: chars as speech-time proxy; syllables if it drifts
        if i == 0 and j < len(toks):  # leading run: only the right side is anchored -> natural pace before it
            a = max(a, b - PACE * sum(wts))
        # the 0.1 s/word floor must not push the run past b: past hi it lands in the next cut
        # (gunther-maske v1: 45 unheard words spilled 3.7 s into the following cut)
        a = max(lo, min(a, b - 0.1 * (j - i)))
        unit = max(b - a, 0.1 * (j - i)) / sum(wts)
        for k in range(i, j):
            times[k] = (a, a + unit * wts[k - i])
            a = times[k][1]
        i = j
    return [{"w": t, "s": round(s, 3), "e": round(e, 3)} for t, (s, e) in zip(toks, times, strict=True)]


def cut_at(cuts, t):
    """Cut containing src.mp4 time t (last cut if t is past the end)."""
    return next((c for c in cuts if t < c["offset"] + c["dur"]), cuts[-1])


def assign_multi(words, segs, cuts):
    """Multi-cut: EDL person wins (labels are hand-corrected); else map back to session time."""
    for w in words:
        c = cut_at(cuts, w["s"])
        if c.get("person"):
            w["person"] = c["person"]
        else:
            assign([w], segs, c["start"] - c["offset"])
    return words


def apply_corrections(words, corrections):
    for c in corrections:
        for w in words[c["from"]:c["to"] + 1]:
            w["person"] = c["person"]
    return words


def main(stem, cid, *flags):
    d = clip_dir(stem, cid)
    if "--apply" in flags:  # patch speakers from speaker-checker output, no re-transcription
        fixes = load(d / "corrections.json")["corrections"]
        dump(apply_corrections(load(d / "words.json"), fixes), d / "words.json")
        print(f"applied {len(fixes)} corrections")
        return

    import torch  # noqa: F401  ponytail: puts torch/lib (cublas64_12.dll) on the DLL path for ctranslate2
    from faster_whisper import WhisperModel

    win = load(d / "window.json")
    model = WhisperModel("large-v3", device="cuda", compute_type="float16")

    # initial_prompt made Whisper skip the prompted sentences; hotwords only nudge spelling.
    hot = " ".join(sorted({s["character"] for s in load(session_dir(stem) / "segments.json")} - {"GM"}))

    def transcribe(path):
        segments, _ = model.transcribe(str(path), language="de", word_timestamps=True, vad_filter=True,
                                       beam_size=5, hotwords=hot)
        return [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)}
                for seg in segments for w in (seg.words or []) if w.word.strip()]

    segs = [s for s in load(session_dir(stem) / "segments.json")
            if s["end"] > win["t0"] - 5 and s["start"] < win["t1"] + 5]
    if win.get("mode") == "multi":
        # Whisper on the joined clip drops words at jump cuts -> transcribe each cut with context from source.
        words = []
        for i, c in enumerate(win["cuts"]):
            a = max(0.0, c["start"] - CONTEXT)
            wav = d / f"ctx_{i:02d}.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{c['end'] + CONTEXT - a:.3f}",
                            "-i", str(source_path(stem)), "-ac", "1", "-ar", "16000", str(wav)], check=True)
            ws = keep_in_cut(transcribe(wav), c, a)
            # last cut runs on under the end card: spread leftovers only over the spoken part (ass drops the rest)
            hi = c["offset"] + c["dur"] - (win.get("endcard_audio", 0.0) if i == len(win["cuts"]) - 1 else 0.0)
            if c.get("text") and len(ws) < 0.6 * len(c["text"].split()):
                print(f"WARN cut {i}: Whisper heard {len(ws)} of {len(c['text'].split())} words, rest interpolated "
                      f"(check with probe.py)")
            words += align_text(c["text"], ws, c["offset"], hi) if "text" in c else ws  # "" = no subs (reaction)
            wav.unlink()
        words = assign_multi(words, segs, win["cuts"])
    else:
        words = assign(transcribe(d / "src.mp4"), segs, win["t0"])
    dump(words, d / "words.json")
    print(f"{len(words)} words -> {d / 'words.json'}")


if __name__ == "__main__":
    main(*sys.argv[1:])
