"""Hear-check: does the viewer hear exactly the subtitle words at every seam? (skill /check-edges, GPU)

Usage: python scripts/hearcheck.py <stem> <id> [--apply]
edgecheck.py finds clipped words only where a pause marks the word end. In connected speech (the GM talks on
without a pause) it can only say LISTEN. This script listens instead: at every audio jump (and at the clip start and
end) it joins the ~3 s before and after the seam exactly as the clip plays them, transcribes that (faster-whisper
large-v3) and aligns the result with the subtitle words of both sides. Only words next to the seam count:
  MISSING A/B  one of the last 2 words before / first 2 after the seam is not heard (clipped or outside the cut)
  EXTRA        words heard at the seam that no subtitle shows (next phrase leaks in, syllable fragment)
Words split across a jump cut ("beängstigende | Macht") are fine as long as the viewer hears them in order.
--apply extends the edge in STEP s steps (MISSING only) until the seam is heard as subtitled and writes lead/tail
into the EDL (old one -> .edl.v<N>.json). No clean edge within REACH = CONNECTED: the cut sits inside connected
speech, move it to another phrase end by hand. EXTRA = LISTEN, never moved inward automatically (see walk).
Run edgecheck.py --apply first (fading tails at pauses, settle at the end; Whisper "hears" those words anyway).
"""
import subprocess
import sys
from difflib import SequenceMatcher
from itertools import pairwise

import numpy as np

from edgecheck import MARGIN, Env, norm
from fetch import FADE, padded
from paths import dump, edl_path, load, source_path

SR = 16000
WIN = 3.0  # s per side of a seam: context for Whisper, little room to "complete" a clipped word
PAD = 0.15  # s of silence around the window (longer pads make Whisper hallucinate "Untertitel ...")
STEP, REACH = 0.05, 1.0  # edge search step and how far an edge may move
NEAR = 2  # words on each side of a seam that must be heard
# Whisper mishears short words at a window edge ("Es" -> "ey"): such EXTRAs are noise, not leaks
FILLER = {"äh", "ähm", "hm", "hmm", "ey", "ja", "ne", "nee", "so", "oh", "ah"}


def close(heard, want):
    """Same word despite ASR spelling ('ganter'/'gunther'), not a fragment ('verdamm'/'verdammnis'); '*' = bleep."""
    return "*" in want or heard == want or (
        SequenceMatcher(None, heard, want).ratio() >= 0.7 and len(heard) >= 0.75 * len(want))


def align(exp, heard):
    """Longest common subsequence with fuzzy word match -> [(i_exp, j_heard)]."""
    n, m = len(exp), len(heard)
    lcs = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            lcs[i][j] = lcs[i + 1][j + 1] + 1 if close(heard[j], exp[i]) else max(lcs[i + 1][j], lcs[i][j + 1])
    pairs, i, j = [], 0, 0
    while i < n and j < m:
        if close(heard[j], exp[i]) and lcs[i][j] == lcs[i + 1][j + 1] + 1:
            pairs.append((i, j))
            i, j = i + 1, j + 1
        elif lcs[i + 1][j] >= lcs[i][j + 1]:
            i += 1
        else:
            j += 1
    return pairs


def fragment(heard, want):
    """Whisper hears a clipped word as a piece of it or as a near-miss: 'zusammen'/'zusammenbricht',
    'vertrag'/'verdammnis' (same first 3 letters), 'ptlich'/'plötzlich' (same last 4). Not a leak."""
    return (heard in want or want in heard or (len(heard) >= 3 and heard[:3] == want[:3])
            or (len(heard) >= 4 and heard[-4:] == want[-4:]))


def seam_status(a, b, heard, a_known=True, b_known=True):
    """a/b: subtitle words before/after the seam ([] = clip start/end), heard: Whisper words of the joined audio.
    *_known False = that side has no subtitle (reaction cut): nothing expected, no EXTRA blamed on it."""
    pairs, na = align(a + b, heard), len(a)
    got = {i for i, _ in pairs}
    st = {"miss_a": [a[i] for i in range(max(0, na - NEAR), na) if i not in got],
          "miss_b": [b[i] for i in range(min(NEAR, len(b))) if na + i not in got], "extra": []}
    ja = max((j for i, j in pairs if i < na), default=None)
    jb = min((j for i, j in pairs if i >= na), default=None)
    lo = ja + 1 if ja is not None else (0 if not a else None)  # no A word heard: window too garbled to blame
    hi = jb if jb is not None else (len(heard) if not b else None)
    if a_known and b_known and lo is not None and hi is not None:
        st["extra"] = [w for w in heard[lo:hi] if len(w) > 2 and w not in FILLER
                       and not any(fragment(w, m) for m in st["miss_a"] + st["miss_b"])]
    return st


def interior(words, heard, run=3):
    """Runs of >= `run` content words inside a group that only one side has: (audible, subtitled-not-heard).
    Head/tail differences are the seam check's job. Whisper drops stutters: single words are noise."""
    pairs = align(words, heard)
    if len(pairs) < 2:
        return [], []
    (i0, j0), (i1, j1) = pairs[0], pairs[-1]
    mj, mi = {j for _, j in pairs}, {i for i, _ in pairs}

    def runs(idx, seq):
        content = [seq[k] for k in idx if len(seq[k]) > 2 and seq[k] not in FILLER]
        return [" ".join(content)] if len(content) >= run else []

    def gaps(rng, matched, seq):
        out, cur = [], []
        for k in rng:
            if k in matched:
                out += runs(cur, seq)
                cur = []
            else:
                cur.append(k)
        return out

    return gaps(range(j0, j1), mj, heard), gaps(range(i0, i1), mi, words)


def edge_in_pause(src, t, side):
    """Loudness view of one audible edge (edgecheck's Env): True = the sound ends >= MARGIN before it (a) / starts
    after it (b), i.e. nothing is clipped there. A missing word is then behind a pause or misheard."""
    env = Env(src, t)
    j = env.sound(env.i(t), -1 if side == "a" else 1, 0.6 if side == "a" else 0.4, loud=True)
    if j is None:
        return True
    return t - env.t(env.pause_after(j)) >= MARGIN - 0.02 if side == "a" else t - env.t(env.pause_before(j)) <= 0.02


def show(st):
    return "  ".join(f"{k.upper().replace('_', ' ')} '{' '.join(v)}'" for k, v in st.items() if v)


class Ear:
    def __init__(self, stem):
        import torch  # noqa: F401  ponytail: puts torch/lib (cublas64_12.dll) on the DLL path for ctranslate2
        from faster_whisper import WhisperModel
        self.model = WhisperModel("large-v3", device="cuda", compute_type="float16")
        self.src, self.cache = source_path(stem), {}

    def audio(self, a, b):
        """Source audio a..b (session s) as float32, decoded once per 30 s block."""
        k0 = int(a // 30)
        parts = []
        for k in range(k0, int(b // 30) + 1):
            if k not in self.cache:
                raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(k * 30), "-t", "30.5", "-i", str(self.src),
                                      "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                                     capture_output=True, check=True).stdout
                self.cache[k] = np.frombuffer(raw[:len(raw) // 2 * 2], np.int16).astype(np.float32) / 32768
            parts.append(self.cache[k][:30 * SR])
        x = np.concatenate(parts)
        return x[round((a - k0 * 30) * SR):round((b - k0 * 30) * SR)]

    def hear(self, *spans):
        """Whisper words of the source spans [(a, b)] joined back to back, as the clip plays them."""
        pad = np.zeros(round(PAD * SR), np.float32)
        x = np.concatenate([pad, *(self.audio(a, b) for a, b in spans), pad])
        segs, _ = self.model.transcribe(x, language="de", beam_size=5, temperature=0.0, vad_filter=False,
                                        condition_on_previous_text=False, without_timestamps=True)
        return [w for w in (norm(t) for s in segs for t in s.text.split()) if w]


def walk(fn):
    """Move an edge outward by STEP*k until fn(shift) is clean at two steps in a row (the second is the word's
    release; one clean step can be luck: Whisper hallucinates "auf einen Pool gehen" at a 50 ms shift and hears the
    clipped word one step later). None when nothing is clean within REACH, e.g. the next phrase follows without a gap.
    Outward only: moving an edge inward on Whisper's word ruled out the word it misheard ("Es" heard as "ey",
    lead -0.65 cut into "tut")."""
    for k in range(1, round(REACH / STEP)):
        if not any(fn(k * STEP).values()) and not any(fn((k + 1) * STEP).values()):
            return round((k + 1) * STEP, 2)
    return None


def groups(cuts, spans):
    """Runs of cuts joined on continuous source -> [{f, l, s, e, words, known}] (s/e = padded, as played)."""
    out, first = [], 0
    for i in range(len(cuts)):
        if i == len(cuts) - 1 or abs(cuts[i]["end"] - cuts[i + 1]["start"]) >= 0.05:
            words = [norm(w) if "*" not in w else "*" for c in cuts[first:i + 1] for w in c.get("text", "").split()]
            words = [w for w in words if w]
            out.append({"f": first, "l": i, "s": spans[first]["start"], "e": spans[i]["end"],
                        "words": words, "known": bool(words)})
            first = i + 1
    return out


def main(stem, cid, *flags):
    p = edl_path(stem, cid)
    if not p.exists():
        sys.exit("single-window clip: no cut edges to check")
    edl = load(p)
    cuts, apply = edl["cuts"], "--apply" in flags
    spans = padded(cuts)
    gs = groups(cuts, spans)
    out_t = [0.0]
    for g in gs:
        out_t.append(out_t[-1] + g["e"] - g["s"])
    silent_end = edl.get("format") == "short" or not edl.get("endcard_audio", 1)  # audio under the card: no end check
    seams = [(None, 0), *pairwise(range(len(gs)))] + ([(len(gs) - 1, None)] if silent_end else [])
    ear, bad, notes, fixed = Ear(stem), 0, 0, 0
    src = source_path(stem)

    def status(ia, ib, ta=0.0, lb=0.0):
        A, B = (gs[ia] if ia is not None else None), (gs[ib] if ib is not None else None)
        spans_ = ([(max(A["s"], A["e"] + ta - WIN), A["e"] + ta)] if A else []) + \
                 ([(B["s"] - lb, min(B["e"], B["s"] - lb + WIN))] if B else [])
        return seam_status(A["words"][-8:] if A else [], B["words"][:8] if B else [], ear.hear(*spans_),
                           A["known"] if A else True, B["known"] if B else True)

    for ia, ib in seams:
        st = status(ia, ib)
        if not any(st.values()):
            continue
        where = f"seam {gs[ia]['l'] if ia is not None else '-'}|{gs[ib]['f'] if ib is not None else '-'}"
        t = out_t[ib] if ib is not None else out_t[-1]
        if st["extra"]:  # leak or misheard word: no safe automatic fix
            notes += 1
            print(f"NOTE {where:12} @{t:5.1f}s  {show(st)}  -> listen: words no subtitle shows")
            continue
        ta = walk(lambda x, ia=ia, ib=ib: status(ia, ib, x)) if st["miss_a"] else 0.0  # extend A's end
        if st["miss_b"] and ta is not None:  # start B earlier
            lb = walk(lambda x, ia=ia, ib=ib, ta=ta: status(ia, ib, ta, x))
        else:
            lb = 0.0
        if ta is None or lb is None:
            clean = (not st["miss_a"] or ia is None or edge_in_pause(src, gs[ia]["e"] - FADE, "a")) and                     (not st["miss_b"] or ib is None or edge_in_pause(src, gs[ib]["s"] + FADE, "b"))
            if clean:  # nothing clipped by loudness (edgecheck): Whisper probably misheard a short/lone word
                notes += 1
                print(f"NOTE {where:12} @{t:5.1f}s  {show(st)}  -> edge sits in a pause, probably misheard: listen")
            else:
                bad += 1
                print(f"HARD {where:12} @{t:5.1f}s  {show(st)}  -> CONNECTED: no clean cut within {REACH} s, "
                      "move it by hand")
            continue
        bad += 1
        fix = []
        if ta and ia is not None:
            c = cuts[gs[ia]["l"]]
            c_tail = round(spans[gs[ia]["l"]]["end"] - c["end"] + ta, 2)
            fix.append(f"cut {gs[ia]['l']} tail {c_tail}")
            if apply:
                c["tail"] = c_tail
        if lb and ib is not None:
            c = cuts[gs[ib]["f"]]
            c_lead = round(c["start"] - spans[gs[ib]["f"]]["start"] + lb, 2)
            fix.append(f"cut {gs[ib]['f']} lead {c_lead}")
            if apply:
                c["lead"] = c_lead
        fixed += bool(fix) and apply
        print(f"FIX  {where:12} @{t:5.1f}s  {show(st)}  -> {', '.join(fix) or 'no fix found'}")
    for k, g in enumerate(gs):
        if g["known"] and g["e"] - g["s"] > 2.0:
            audible, unheard = interior(g["words"], ear.hear((g["s"], g["e"])))
            for x in audible:
                notes += 1
                print(f"NOTE cuts {g['f']}-{g['l']} @{out_t[k]:5.1f}s  audio has '{x}', no subtitle shows it -> fix the EDL text")
            for x in unheard:
                notes += 1
                print(f"NOTE cuts {g['f']}-{g['l']} @{out_t[k]:5.1f}s  subtitle '{x}' not heard -> fix the EDL text or the cut")
    print(f"== {cid}: {bad} hard, {notes} notes" + (f", {fixed} fixed" if apply else ""))
    if apply and fixed:
        v = 1
        while p.with_suffix(f".v{v}.json").exists():
            v += 1
        p.with_suffix(f".v{v}.json").write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
        dump(edl, p)
        print(f"old EDL -> {p.with_suffix(f'.v{v}.json').name}. Next: fetch, words, ass, render")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(*sys.argv[1:])
