"""Self-check for subtitle cards, shot planning, consent gate. Run: python scripts/test_core.py"""
from itertools import pairwise

from ass import ass_color, build, cards, seams, ts, warnings
from candidates import merge
from dice import validate
from edgecheck import Env, check_end, pick_words
from fetch import concat_filter, padded
from glaze import ass_cards, chain, focus_px, plan
from hearcheck import fragment, interior, seam_status, walk
from render import (
    bleep_filter,
    consent_missing,
    dice_filter,
    multi_shots,
    pip_filter,
    shot_filter,
    shots,
)
from retime import uncovered
from words import align_text, apply_corrections, assign_multi, keep_in_cut


def W(w, s, e, p):
    return {"w": w, "s": s, "e": e, "person": p}


words = [W("a", 0.0, 0.2, "tim"), W("b", 0.2, 0.4, "tim"), W("c", 0.4, 0.6, "tim"), W("d", 0.6, 0.8, "tim"),
         W("e", 0.8, 1.0, "tim"),                       # 5th word -> new card
         W("f", 2.0, 2.2, "tim"),                       # pause > 0.4 -> new card
         W("g", 2.3, 2.5, "deniz"),                     # speaker change -> new card
         W("h", 3.0, 3.2, "celin"), W("i", 3.3, 9.0, "celin")]
c = cards(words)
assert [len(x["words"]) for x in c] == [3, 2, 1, 1, 2], c  # 5th word "e" (0.2 s) borrows "d" from card 1
assert all(len(x["words"]) <= 4 for x in c)
assert ass_color("#FFAA00") == "&H00AAFF&"
assert ts(61.5) == "0:01:01.50"
cc = [{"offset": 0.0, "card": "x"}, {"offset": 3.0, "card": "x"}, {"offset": 4.0, "card": "y"}]
hooks = [ln for ln in build([], "", {}, cc).splitlines() if ",Hook," in ln]
assert hooks[0].startswith("Dialogue: 1,0:00:00.00,0:00:05.00,") and len(hooks) == 2, hooks  # same card on next cut extends
hooks = [ln for ln in build([], "H", {}, [{"offset": 0.0, "card": "x"}]).splitlines() if ",Hook," in ln]
assert hooks == ["Dialogue: 1,0:00:00.00,0:00:03.00,Hook,,0,0,0,,H",
                 "Dialogue: 1,0:00:03.00,0:00:05.00,Hook,,0,0,0,,x"], hooks  # card on cut 0 waits for the hook

p = shots(words, 10.0)
assert p[0]["s"] == 0.0 and p[-1]["e"] == 10.0
assert all(b["s"] == a["e"] for a, b in pairwise(p)), "shots must be contiguous"
assert [x["person"] for x in p] == ["tim", "celin"], p  # deniz 0.3 s turn merged away
assert all(x["e"] - x["s"] >= 1.5 for x in p)
assert shots([], 4.0) == [{"person": None, "s": 0.0, "e": 4.0}]

ok = {"date": "2026-10-01", "platforms": ["tiktok"], "ai_processing": True, "revoked": False}
consent = {"tim": ok, "deniz": {**ok, "revoked": True}, "celin": {**ok, "date": ""},
           "marco": {**ok, "platforms": ["youtube"]}, "heiko": {**ok, "ai_processing": False}}
assert consent_missing({"tim"}, consent) == []
assert consent_missing({"tim", "deniz", "celin", "marco", "heiko", "nobody"}, consent) == \
    ["celin", "deniz", "heiko", "marco", "nobody"]
fixed = apply_corrections([W("x", 0, 1, "tim"), W("y", 1, 2, "tim"), W("z", 2, 3, "tim")],
                          [{"from": 1, "to": 2, "person": "deniz"}])
assert [w["person"] for w in fixed] == ["tim", "deniz", "deniz"]
# multi-cut
cuts = [{"start": 100.0, "end": 103.0, "person": "celin", "offset": 0.0, "dur": 3.0},
        {"start": 50.0, "end": 54.0, "person": "deniz", "cam": "celin", "card": "vorher", "offset": 3.0, "dur": 4.0},
        {"start": 70.0, "end": 72.0, "offset": 7.0, "dur": 2.0}]
assert [(m["person"], m["speaker"], m["s"], m["e"]) for m in multi_shots(cuts)] == \
    [("celin", "celin", 0.0, 3.0), ("celin", "deniz", 3.0, 7.0), (None, None, 7.0, 9.0)]
assert bleep_filter(cuts) == "[0:a]anull[a0]"
assert "between(t,4.000,4.500)" in bleep_filter([{**cuts[1], "bleep": [[51.0, 51.5]]}])  # session -> clip time
segs = [{"start": 69.0, "end": 73.0, "person": "heiko"}]
mw = assign_multi([W("a", 1.0, 1.2, "?"), W("b", 3.5, 3.7, "?"), W("c", 7.5, 7.7, "?")], segs, cuts)
assert [w["person"] for w in mw] == ["celin", "deniz", "heiko"]  # EDL person, else segment at session time
same = [W("x", 2.6, 2.8, "deniz"), W("y", 3.1, 3.3, "deniz")]
assert len(cards(same)) == 1 and len(cards(same, [3.0])) == 2  # no card across a jump cut
assert seams([{"offset": 0, "person": "tim"}, {"offset": 2, "person": "tim"},  # same cam: card may span
              {"offset": 3, "person": "deniz", "cam": "map"}, {"offset": 5, "person": "celin", "cam": "map"}]) == [3]
long = [W("Meme-Sprache", 0, 0.3, "heiko"), W("zu", 0.3, 0.4, "heiko"), W("sagen:", 0.4, 0.6, "heiko"),
        W("shoppie,", 0.6, 0.9, "heiko")]
assert [" ".join(c["words"]) for c in cards(long)] == ["Meme-Sprache zu", "sagen:", "shoppie,"]  # char cap, ":" ends
roll = [W("Das", 0, 0.3, "deniz"), W("ist", 0.3, 0.5, "deniz"), W("21", 0.5, 0.9, "deniz"),
        W("mit", 0.9, 1.2, "deniz"), W("Hope.", 1.2, 1.42, "deniz"), W("Du", 1.5, 1.7, "deniz"),
        W("springst", 1.7, 2.1, "deniz")]
assert [" ".join(c["words"]) for c in cards(roll)] == ["Das ist 21", "mit Hope.", "Du springst"]  # orphan, sentence
assert warnings(roll, cards(roll)) == []
held = [W("Und", 0, 0.5, "deniz"), W("damit", 0.6, 1.2, "deniz"), W("trägt", 1.3, 2.6, "deniz"), W("Dodo", 2.65, 3, "deniz")]
assert [" ".join(c["words"]) for c in cards(held)] == ["Und damit trägt", "Dodo"]  # pause hidden in "trägt"
squeezed = [W(x, 5 + k / 10, 5.1 + k / 10, "celin") for k, x in enumerate(["Und", "Lunaras", "Blick"])]
assert warnings(squeezed, cards(squeezed))[-1].startswith("3+ words under 0.12 s")
fc = concat_filter([2.0, 3.5])
assert "afade=t=out:st=3.470" in fc and fc.endswith("[0:v][a0][1:v][a1]concat=n=2:v=1:a=1[v][a]")
fj = concat_filter([2.0, 3.5], [True])  # source runs on (cam switch mid-line): no fade dip at the seam
assert "[0:a]afade=t=in:d=0.03[a0]" in fj and "[1:a]afade=t=out:st=3.470:d=0.03[a1]" in fj
kc = keep_in_cut([W("vor", 0.5, 0.9, None), W("drin", 3.2, 3.6, None), W("raus", 3.9, 4.6, None)],
                 {"start": 103.0, "end": 104.2, "offset": 10.0}, 100.0)
assert [(w["w"], w["s"], w["e"]) for w in kc] == [("drin", 10.2, 10.6), ("raus", 10.9, 11.2)]  # end clamped
al = align_text("acht Säcke Gold, wirklich?", [W("18", 1.0, 1.3, None), W("Säcke", 1.4, 1.7, None),
                                                W("gold", 1.8, 2.0, None)], 0.5, 3.0)
assert [w["w"] for w in al] == ["acht", "Säcke", "Gold,", "wirklich?"]  # text from EDL, not Whisper
assert (al[0]["s"], al[2]["e"]) == (1.0, 2.0) and al[3]["s"] == 2.0 and al[3]["e"] == 3.0  # tail spread to hi
spill = align_text("a b c d e", [W("a", 0.0, 0.95, None)], 0.0, 1.0)  # 4 unheard words, 0.05 s left
assert spill[-1]["e"] <= 1.0 and all(w["s"] >= 0.0 for w in spill)  # stays inside the cut
empty = align_text("ich so", [], 4.0, 5.0)
assert [(w["s"], w["e"]) for w in empty] == [(4.0, 4.571), (4.571, 5.0)]  # spread by length
# gold-saga bug: Whisper missed "zwei drei" and stretched "vier" over them -> no 0.1 s squeeze
st = align_text("eins zwei drei vier", [W("eins", 0.0, 0.3, None), W("vier", 0.5, 4.0, None)], 0.0, 4.0)
assert min(w["e"] - w["s"] for w in st[1:]) > 0.8 and st[-1]["e"] == 4.0, st
lead = align_text("Ich sag so", [W("sag", 3.0, 3.2, None), W("so", 3.2, 3.4, None)], 0.0, 4.0)
assert (lead[0]["s"], lead[0]["e"]) == (2.68, 3.0)  # cut opens on silence: "Ich" sits right before "sag"
pc = padded([{"start": 10.0, "end": 12.0}, {"start": 12.0, "end": 13.0}, {"start": 5.0, "end": 6.0, "lead": 0.0}])
assert [(c["start"], c["end"]) for c in pc] == [(9.8, 12.0), (12.0, 13.3), (5.0, 6.3)]  # no pad at joined seam
for f in (shot_filter(0, {"s": 0, "e": 1}, None), shot_filter(1, {"s": 0, "e": 1}, [1, 2, 3, 4], [5, 6, 7, 8]),
          pip_filter(2, {"s": 0, "e": 1}, [1, 2, 3, 4], [5, 6, 7, 8], [9, 9, 9, 9])):
    assert "]," not in f and ",," not in f, f  # no empty filter after a label / between filters
mid = {"start": 100, "end": 170, "score": 8, "format": "mid"}
inside = {"start": 120, "end": 132, "score": 7, "format": "short"}
dup = {"start": 101, "end": 165, "score": 6, "format": "mid"}
assert [c["format"] for c in merge([mid, inside, dup])] == ["mid", "short"]  # dedup only within a format

assert plan([{"beats": 4}, {"beats": 1}], 120) == [(0.0, 2.0), (2.0, 2.5)]  # shots sit on the beat grid
vf = chain({"fx": ["slow", "punch", "glow", "flash"]}, [1, 2, 3, 4], 1.0)
assert vf.startswith("crop=3:4:1:2,") and "setpts=PTS/0.7" in vf and "zoompan" in vf and vf.endswith("color=white")
assert "zoompan" not in chain({}, [0, 0, 8, 8], 1.0)  # no zoom without punch/push
assert chain({"delogo": [5, 6, 7, 8]}, [1, 2, 3, 4], 1.0).startswith("delogo=x=5:y=6:w=7:h=8,crop=")  # before crop
assert "floor(on/7.500)" in chain({"fx": ["stutter"]}, [0, 0, 8, 8], 1.0, 0.5)  # zoom step every half beat
assert "pow(on/30,2)" in chain({"fx": ["glide"]}, [0, 0, 8, 8], 1.0)  # smooth zoom over the whole shot
assert focus_px([150, 300], [100, 100, 540, 960]) == (200, 800)  # 4x scale, no crop
assert focus_px([100, 100], [0, 0, 400, 400]) == (120, 960)  # square box: cover 9.6x, 840 px cropped per side
assert "(1080-iw/2)" in chain({"fx": ["glide"], "focus": [370, 580]}, [100, 100, 540, 960], 1.0)
assert "mod(on,15.000)" in chain({"fx": ["pulse"]}, [0, 0, 8, 8], 1.0, 0.5)  # bounce every beat (15 frames)
assert "mod(t,0.5000)" in chain({"fx": ["strobe"]}, [0, 0, 8, 8], 1.0, 0.5)
assert "Dialogue: 0,0:00:01.00,0:00:02.50,Card" in ass_cards([(1.0, 2.5, "JOAR")])

def env(frames):  # synthetic 10 ms envelope from 0 s, floor -60 dB
    e = Env.__new__(Env)
    e.a, e.e, e.q, e.loud = 0.0, frames, -52.0, -46.0
    return e


word, quiet = [-25.0] * 30, [-60.0] * 30  # 0.3 s word / pause
tail = env(quiet + word + quiet + quiet)  # word 0.3-0.6 s
assert check_end(tail, {"start": 0, "text": "a"}, 0.45, False, "mid", [], [])[0][0][0] == "CUT"  # cut mid-word
f, want = check_end(tail, {"start": 0, "text": "a"}, 0.75, False, "mid", [], [])
assert not f and want == 0.75  # 0.15 s after the word: clean
# "niemandem": Whisper times it inside the cut, the sound comes after a pause -> DROP, extend over that island
drop = env(quiet + word + quiet + word + quiet)  # 0.3-0.6 "bitte", 0.9-1.2 "niemandem"
f, want = check_end(drop, {"start": 0, "text": "bitte niemandem."}, 0.75, False, "mid",
                    [(0.3, "bitte"), (0.5, "niemandem.")], [(0, 2)])
assert [lv for lv, _ in f] == ["DROP"] and abs(want - 1.32) < 0.01, (f, want)
f, _ = check_end(drop, {"start": 0, "text": "bitte niemandem."}, 0.75, False, "mid",
                 [(0.3, "bitte"), (0.5, "niemandem."), (0.95, "Das")], [(0, 2)])
assert not f  # Whisper hears the next word in that island: no DROP
f, _ = check_end(tail, {"start": 0, "text": "a"}, 0.45, False, "mid", [(0.3, "a"), (0.5, "und")], [(0, 2)])
assert [lv for lv, _ in f] == ["LISTEN"]  # extending would pull in an unsubtitled word
syl = env(quiet + word + [-60.0] * 8 + word + quiet + quiet)  # "Verdamm" 0.3-0.6, 80 ms dip, "nis" 0.68-0.98
f, want = check_end(syl, {"start": 0, "text": "Verdammnis"}, 0.64, False, "mid", [], [])
assert [lv for lv, _ in f] == ["CUT"] and abs(want - 1.1) < 0.01, (f, want)  # cut in the dip clips "-nis"
f, want = check_end(tail, {"start": 0, "text": "a."}, 0.65, True, "mid", [], [])
assert "END" in [lv for lv, _ in f] and abs(want - 1.1) < 0.01  # last cut: 0.5 s settle after the last word
# probe windows: a narrow re-probe beats a wide garbled window (Folge 6 seil), else the most central window wins
wide = (3255.0, 3325.0, [(3270.17, "das"), (3270.57, "ist")])
narrow = (3268.6, 3272.4, [(3268.84, "wieso"), (3269.48, "habe"), (3270.42, "Hand?")])
assert pick_words([wide, narrow]) == narrow[2]
assert pick_words([(0.0, 20.0, [(9.0, "mitte")]), (8.0, 30.0, [(9.1, "rand")])]) == [(9.0, "mitte")]
assert pick_words([(0.0, 20.0, [(10.0, "a")]), (0.0, 20.0, [(10.0, "a")])]) == [(10.0, "a")]  # tie: one copy
# hear-check: what the viewer hears at a seam vs. the subtitle words on both sides
a, b = ["sag", "das", "bitte", "niemandem"], ["das", "bleibt"]
assert not any(seam_status(a, b, a + b).values())
assert seam_status(a, b, ["sag", "das", "bitte", "das", "bleibt"])["miss_a"] == ["niemandem"]  # zebros cut 8
assert seam_status(["sein", "verdammnis"], [], ["aber", "sein", "verdamm"])["miss_a"] == ["verdammnis"]
assert seam_status(a, b, ["bitte", "niemanden", "versprochen", "das", "bleibt"])["extra"] == ["versprochen"]
st = seam_status(["eine", "beängstigende"], ["macht"], ["habe", "eine", "beängstigende", "macht"])
assert not any(st.values())  # word split across a jump cut: heard in order = fine
assert not any(seam_status(["schaut", "gunther"], [], ["schaut", "ganter"]).values())  # ASR spelling
assert not any(seam_status(["du", "*"], [], ["du", "piep"]).values())  # bleeped word matches anything
assert seam_status([], ["zu", "anfang"], ["anfang"])["miss_b"] == ["zu"]
assert seam_status([], ["es", "tut"], ["ey", "es", "tut"])["extra"] == []  # "ey" = misheard "Es", noise
assert seam_status([], ["mein", "name"], ["brüllt", "mein", "name"])["extra"] == ["brüllt"]  # real leak
assert seam_status(["lachen"], [], ["haha", "ja"], a_known=False)["extra"] == []  # reaction cut: nothing expected
# edge search: clean from 0.15 s further out, one more step for the release; connected speech gives None
assert walk(lambda x: {"m": [] if x >= 0.149 else ["w"], "extra": []}) == 0.2
assert walk(lambda x: {"m": [] if x >= 0.149 else ["w"], "extra": ["n"] if x >= 0.099 else []}) is None

assert uncovered([{"start": 10, "end": 12, "text": "a"}, {"start": 13, "end": 14, "text": "b"},
                  {"start": 100, "end": 101, "text": "c"}, {"start": 50, "end": 51, "text": ""}],
                 [(9.0, 200.0)]) == [], "inside a window"
assert uncovered([{"start": 10, "end": 12, "text": "a"}, {"start": 13, "end": 14, "text": "b"}], []) == [[8.5, 15.5]]  # merged
assert uncovered([{"start": 10, "end": 12, "text": "a"}, {"start": 50, "end": 51, "text": "b"}], [(9.0, 13.9)]) == [[48.5, 52.5]]
assert fragment("zusammen", "zusammenbricht") and fragment("vertrag", "verdammnis") and not fragment("kurz", "tomate")
st = seam_status(["sein", "verdammnis"], ["wie"], ["sein", "vertrag", "wie"])  # clipped word heard as a piece
assert st["miss_a"] == ["verdammnis"] and not st["extra"], st
st = seam_status(["sein", "ende"], ["und", "dann"], ["sein", "ende", "also", "und", "dann"])  # next phrase leaks in
assert st["extra"] == ["also"] and not st["miss_a"], st
aud, unh = interior(["a", "bbb", "ccc", "ddd", "eee", "fff"], ["a", "bbb", "xxx", "yyy", "zzz", "ccc", "ddd", "eee", "fff"])
assert aud == ["xxx yyy zzz"] and unh == [], (aud, unh)  # 3 audible words the subtitles lack
aud, unh = interior(["a", "bbb", "ccc", "ddd", "eee", "fff"], ["a", "bbb", "ccc", "fff"])
assert aud == [] and unh == [], (aud, unh)  # 2 missing words: below the run threshold

bad, ok = {"miss_a": ["x"], "extra": []}, {"miss_a": [], "extra": []}
noisy = {0.05: bad, 0.1: {"miss_a": [], "extra": ["pool"]}, 0.15: ok, 0.2: ok, 0.25: ok}
assert walk(lambda x: noisy.get(round(x, 2), bad)) == 0.2  # transient hallucination skipped, release step added
assert walk(lambda x: bad) is None and walk(lambda x: {"miss_a": [], "extra": ["w"]}) is None

roll = {"hope": 12, "fear": 9, "adv": [6, 4], "mod": 5, "total": 36, "label": "Success with Hope"}
validate(roll)  # Folge 8 dodo-streitkolben: advantage d6 are added
for bad in ({**roll, "total": 35}, {**roll, "hope": 13}, {**roll, "adv": [7]}):
    try:
        validate(bad)
        raise SystemExit(f"validate passed {bad}")
    except AssertionError:
        pass
f = dice_filter(4, {"s": 20.5, "e": 23.9}, [560, 66, 806, 548], 2)
assert "trim=start=20.500:end=23.900" in f and "[2:v]format=rgba" in f and f.endswith("[v4]"), f
print("ok")
