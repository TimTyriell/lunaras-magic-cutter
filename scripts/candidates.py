"""Merge clip-scout outputs into work/<stem>/candidates.json.

Usage: python scripts/candidates.py <stem>
Reads work/<stem>/scouts/*.json (one JSON array per chunk). Drops windows outside 8-90 s,
dedups overlaps > 50 % within the same format (keeps higher score), sorts by score, assigns ids c01, c02, ...
"""
import sys

from paths import dump, load, session_dir

MIN_LEN, MAX_LEN = 8, 90  # format short from ~8 s, mid up to the story (rules.md Formats); 90 s guards runaway windows


def overlap(a, b):
    inter = min(a["end"], b["end"]) - max(a["start"], b["start"])
    return max(0.0, inter) / min(a["end"] - a["start"], b["end"] - b["start"])


def merge(items):
    items = [c for c in items if MIN_LEN <= c["end"] - c["start"] <= MAX_LEN]
    kept = []
    for c in sorted(items, key=lambda c: -c["score"]):
        if all(overlap(c, k) <= 0.5 for k in kept if k.get("format") == c.get("format")):  # a short may sit in a mid
            kept.append(c)
    for i, c in enumerate(kept, 1):
        c["id"] = f"c{i:02d}"
    return kept


def main(stem):
    d = session_dir(stem)
    items = [c for f in sorted((d / "scouts").glob("*.json")) for c in load(f)]
    kept = merge(items)
    dump(kept, d / "candidates.json")
    print(f"{len(items)} raw -> {len(kept)} candidates -> {d / 'candidates.json'}")


if __name__ == "__main__":
    main(sys.argv[1])
