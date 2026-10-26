"""Audio-edge review: does a word that the subtitles/caption show lose its sound at a cut? (skill /check-edges)

Usage: python scripts/edgecheck.py <stem> <id> [--apply]
Per EDL cut edge where the audio jumps (not joined), on the cached source.mp4, 10 ms RMS against the local floor:
  CUT    sound still running at the audible edge -> word tail (end) or onset (start) clipped
  TIGHT  sound ends < MARGIN before the audible end; the 30 ms seam fade eats the rest
  DROP   the cut's last text word cannot fit before the edge (probe start + est. length) and speech resumes
         right after -> the word sits in the next speech island (Whisper starts run 0.3-0.9 s early, Folge 9)
  END    last cut: < SETTLE after the last sound (clip stops on the word), or the text ends mid-sentence
Each finding prints the out.mp4 time, the edge words and a suggested lead/tail (session seconds, s).
--apply writes the suggestions into the EDL (old one kept as .edl.v<N>.json); then rerun fetch, words, ass, render.
Probe words: work/<session>/scripts/probe*.txt (probe.py output); without them DROP is skipped.
"""
import math
import re
import subprocess
import sys
from array import array

from fetch import FADE, padded
from paths import dump, edl_path, load, session_dir, source_path

SR, FR = 16000, 0.01
QUIET, LOUD = 8.0, 14.0  # dB above the local floor: below QUIET = pause, from LOUD = clearly audible
MIN_Q, MIN_LOUD = -56.0, -48.0  # floors near -67 dB (knie) put floor+8 inside the room-tone flicker
GAP = 0.06  # a pause = 60 ms of QUIET frames
SPLIT = 0.15  # a pause shorter than this at the cut sits inside a long word (plosive closure: "Verdamm|nis" 80 ms,
# "ab|bekommt"); the build's RMS-dip snap put cut ends exactly there. A global 150 ms GAP merged real sentence pauses.
MARGIN = 0.12  # wanted room between the last sound and the audible end
SETTLE = {"mid": 0.5, "short": 0.25}  # last cut: room after the last word; shorts loop, they may end tighter
RESUME = 1.2  # DROP: speech resuming within this after the edge holds the missing word
ISLAND = 0.12  # shorter sound islands are clicks or breaths, not words
LONG = 0.8  # sound running this far across an edge = next speaker / cross-talk / mid-phrase cut: listen, no auto fix
RE_PROBE = 6.0  # probe windows up to this long are re-probes of a garbled span: their words win (pick_words)
# ponytail: one threshold set, tuned on Folge 9 room tone (~-60 dB); a music bed under speech needs a retune


def envelope(src, a, d):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{a:.3f}", "-t", f"{d:.3f}", "-i", str(src), "-vn",
                          "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True, check=True).stdout
    x, n = array("h"), int(SR * FR)
    x.frombytes(raw[:len(raw) // 2 * 2])
    return [20 * math.log10(math.sqrt(sum(v * v for v in x[i:i + n]) / n) / 32768 + 1e-9)
            for i in range(0, len(x) - n + 1, n)]


class Env:
    """10 ms dB frames around one edge, thresholds relative to the local floor (10th percentile)."""

    def __init__(self, src, t, before=1.5, after=2.5):
        self.a = max(0.0, t - before)
        self.e = envelope(src, self.a, before + after)
        floor = sorted(self.e)[len(self.e) // 10]
        self.q, self.loud = max(floor + QUIET, MIN_Q), max(floor + LOUD, MIN_LOUD)

    def i(self, t):
        return min(len(self.e) - 1, max(0, round((t - self.a) / FR)))

    def t(self, i):
        return self.a + i * FR

    def pause_after(self, i):
        """First frame of the first >= GAP quiet run at or after frame i."""
        run, need = 0, round(GAP / FR)
        for k in range(i, len(self.e)):
            run = run + 1 if self.e[k] < self.q else 0
            if run >= need:
                return k - run + 1
        return len(self.e)

    def pause_before(self, i):
        """Frame after the last >= GAP quiet run ending at or before frame i (= onset of the sound at i)."""
        run, need = 0, round(GAP / FR)
        for k in range(i, -1, -1):
            run = run + 1 if self.e[k] < self.q else 0
            if run >= need:
                return k + run
        return 0

    def sound(self, i, step, limit, loud=False):
        """Nearest frame from i (walking by step, at most limit s) above QUIET (or LOUD), or None."""
        for k in range(i, i + step * round(limit / FR), step):
            if 0 <= k < len(self.e) and self.e[k] >= (self.loud if loud else self.q):
                return k
        return None

    def island(self, i, limit):
        """(onset, release) frames of the next speech island starting within limit s after frame i.
        Islands under ISLAND are clicks/breaths, skipped."""
        end = i + round(limit / FR)
        while (n := self.sound(i, 1, (end - i) * FR)) is not None:
            r = self.pause_after(n)
            if (r - n) * FR >= ISLAND:
                return n, r
            i = r
        return None


def probe_words(stem):
    """(t, word) from every probe*.txt (utf-8 or cp1252, PowerShell redirects), windows [(a, b)].
    Overlapping windows time the same word differently: keep it only from the window where it sits farthest
    from the edges (as Folge 9 retime.py)."""
    wins = []
    for f in sorted((session_dir(stem) / "scripts").glob("probe*.txt")):
        for raw in f.read_bytes().splitlines():
            try:
                line = raw.decode("utf-8")
            except UnicodeDecodeError:
                line = raw.decode("cp1252")
            if m := re.match(r"== ([\d.]+)-([\d.]+)", line):
                wins.append((float(m[1]), float(m[2]), []))
            elif wins:
                wins[-1][2].extend((float(t), w) for t, w in re.findall(r"([\d.]+):(\S+)", line))
    return pick_words(wins), [(a, b) for a, b, _ in wins]


def pick_words(wins):
    """[(a, b, [(t, word)])] -> sorted [(t, word)], each time span taken from one window only: a narrow re-probe
    (<= RE_PROBE s, a deliberate correction) beats wide windows, else the window where t sits farthest from the
    edges; ties keep the first (Folge 6: a wide garbled window always won over the narrow re-probe)."""
    def margin(w, t):
        return min(t - w[0], w[1] - t)

    def best(t):
        ws = [w for w in wins if w[0] <= t <= w[1]]
        return max([w for w in ws if w[1] - w[0] <= RE_PROBE] or ws, key=lambda w: margin(w, t))

    return sorted((t, word) for w in wins for t, word in w[2] if best(t) is w)


def norm(w):
    return re.sub(r"\W", "", w.lower())


def same(a, b):
    """ASR spelling drift: 'niemandem'/'niemanden', 'würfel'/'würfle'."""
    a, b = norm(a), norm(b)
    return a == b or (min(len(a), len(b)) >= 4 and a[:max(4, min(len(a), len(b)) - 2)] == b[:max(4, min(len(a), len(b)) - 2)])


def check_end(env, c, ae, last, fmt, pw, cover):
    """[(level, message)] and the wanted audible end (session s) for one cut end; ae = audible end now.
    Levels CUT/DROP/END/TIGHT get an auto fix; LISTEN needs a human ear (no safe automatic fix)."""
    found, want, i = [], ae, env.i(ae)
    words = [w for w in c.get("text", "").split() if norm(w)]
    covered = pw and words and any(a <= ae <= b for a, b in cover)
    hits = [t for t, w in pw if c["start"] - 0.3 <= t <= ae + RESUME and same(w, words[-1])] if covered else []
    # the cut's own last word: latest hit before the cut, else the first after ("Kreis." 3354.62, not 3356.20)
    hits = [t for t in hits if t <= ae + 0.3][-1:] or hits[:1]
    ref = hits[-1] if hits else ae - 0.2  # probe words after the cut's last word are not in the subtitles

    def extra(until):
        return [w for t, w in pw if ref < t <= until] if covered else []

    j = env.sound(i, -1, 0.6, loud=True)  # anchor on a real word, not a room-tone blip
    over = 0.0
    if j is not None:
        r = env.pause_after(j)
        # a short dip at the cut is inside the word: it goes on, unless Whisper starts a new word there
        while env.t(r) <= ae + MARGIN and (n := env.sound(r, 1, SPLIT, loud=True)) is not None \
                and not extra(env.t(n)):
            r = env.pause_after(n)
        nxt = env.island(r, RESUME)
        cap = env.t(nxt[0]) - 0.05 if nxt else 1e9  # never reach into the next phrase
        over = env.t(r) - ae
        if over > LONG:
            found.append(("LISTEN", f"sound runs on {over:.2f}+ s past the cut (next speaker, cross-talk or mid-phrase)"))
        elif over > 0.05 and (x := extra(env.t(r))):
            found.append(("LISTEN", (f"sound runs {over:.2f} s past the cut, but extending pulls in "
                                    f"'{' '.join(x[:5])}' (Whisper): clipped tail or next phrase?")))
            over = LONG + 1  # no DROP / END guess on top
        elif over > 0.05:
            found.append(("CUT", f"word tail clipped: sound runs {over:.2f} s past the cut"))
            want = min(env.t(r) + MARGIN, cap)
        elif ae - env.t(r) < MARGIN - 0.01 and cap > ae + 0.01:  # no room before the next sound: nothing to fix
            found.append(("TIGHT", f"{ae - env.t(r):+.2f} s between last sound and cut"))
            want = min(env.t(r) + MARGIN, cap)
        need = SETTLE.get(fmt, SETTLE["mid"])
        if last and over <= LONG and want - env.t(r) < need - 0.01:
            if min(env.t(r) + need, cap) > want + 0.01:
                found.append(("END", f"clip stops {max(0.0, ae - env.t(r)):.2f} s after the last word (want {need})"))
                want = min(env.t(r) + need, cap)
            else:
                found.append(("LISTEN", (f"ending: next sound {cap + 0.05 - env.t(r):.2f} s after the last word; "
                                        "include it (reaction?) or keep the short ending")))
    if last and words and not re.search(r"[.!?…]\W*$", c["text"].strip()):
        found.append(("LISTEN", f"text ends mid-sentence ('{words[-1]}'): does the line finish after the cut?"))
    if covered and over <= LONG:
        lw = words[-1]
        if not hits:
            found.append(("LISTEN", f"last word '{lw}' not among the probe words near the cut"))
        elif hits[-1] + 0.06 * len(norm(lw)) + 0.1 > ae + 0.05:
            isl = env.island(env.pause_after(i), RESUME)
            # the island after the cut holds the word only if Whisper puts no later word there (its times run early)
            if isl and not extra(env.t(isl[1])):
                n2 = env.island(isl[1], RESUME)
                want = max(want, min(env.t(isl[1]) + MARGIN, env.t(n2[0]) - 0.05 if n2 else 1e9))
                found.append(("DROP", (f"'{lw}' (probe {hits[-1]:.2f}) misses the cut; it is likely the speech at "
                                      f"{env.t(isl[0]):.2f}-{env.t(isl[1]):.2f} right after")))
    return found, want


def check_start(env, as_):
    found, want = [], as_
    j = env.sound(env.i(as_), 1, 0.4, loud=True)
    if j is not None:
        o = env.pause_before(j)
        early = as_ - env.t(o)
        if early > 0.4:
            found.append(("LISTEN", f"speech already running {early:.2f}+ s before the cut (cross-talk or clipped word)"))
        elif early > 0.02:
            found.append(("CUT", f"word onset clipped: sound starts {early:.2f} s before the cut"))
            p = env.sound(o - 1, -1, 1.0)  # previous sound: do not reach into it
            want = max(env.t(o) - 0.1, env.t(p) + 0.08 if p is not None else 0.0)
    return found, want


def main(stem, cid, *flags):
    p = edl_path(stem, cid)
    if not p.exists():
        sys.exit("single-window clip (±2 s pad): no cut edges to check")
    edl = load(p)
    cuts, fmt = edl["cuts"], edl.get("format", "mid")
    spans = padded(cuts)
    pw, cover = probe_words(stem)
    src = source_path(stem)
    silent_end = fmt == "short" or not edl.get("endcard_audio", 1)  # audio under the card fades 1 s: no END check
    off, count, apply = 0.0, {}, "--apply" in flags
    for k, (c, s) in enumerate(zip(cuts, spans)):
        off += s["end"] - s["start"]
        joined_prev = k and abs(cuts[k - 1]["end"] - c["start"]) < 0.05
        joined_next = k + 1 < len(cuts) and abs(cuts[k + 1]["start"] - c["end"]) < 0.05
        last = k == len(cuts) - 1
        words = c.get("text", "").split()
        if not joined_prev:
            as_ = s["start"] + FADE
            f, want = check_start(Env(src, as_), as_)
            lead = round(c["start"] - want + FADE, 2)
            fix = any(lv != "LISTEN" for lv, _ in f)
            for lv, m in f:
                count[lv] = count.get(lv, 0) + 1
                print(f"{lv:6} cut {k:2} start {c['start']:.2f} @{off - s['end'] + s['start']:5.1f}s "
                      f"'{' '.join(words[:3])}…': {m}" + (f" -> lead {lead}" if lv != "LISTEN" else ""))
            if apply and fix:
                c["lead"] = max(lead, c.get("lead", 0.0))
        if not joined_next and (silent_end or not last):
            ae = s["end"] - (0.05 if last and fmt != "short" else FADE)  # seam fade / silent-card fade
            f, want = check_end(Env(src, ae), c, ae, last, fmt, pw, cover)
            tail = round(want - ae + s["end"] - c["end"], 2)
            fix = tail > s["end"] - c["end"] + 0.005
            for lv, m in f:
                count[lv] = count.get(lv, 0) + 1
                print(f"{lv:6} cut {k:2} end   {c['end']:.2f} @{off:5.1f}s '…{' '.join(words[-3:])}': {m}"
                      + (f" -> tail {tail}" if lv != "LISTEN" and fix else ""))
            if apply and fix:
                c["tail"] = tail
    print(f"== {cid}: " + (", ".join(f"{v} {k}" for k, v in sorted(count.items())) or "clean")
          + ("" if pw else " (no probe*.txt: DROP not checked)"))
    if apply and any(k != "LISTEN" for k in count):
        v = 1
        while p.with_suffix(f".v{v}.json").exists():
            v += 1
        p.with_suffix(f".v{v}.json").write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
        dump(edl, p)
        print(f"applied lead/tail; old EDL -> {p.with_suffix(f'.v{v}.json').name}. "
              "Next: fetch, words, ass, render, then edgecheck again (LISTEN items stay for the human)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(*sys.argv[1:])
