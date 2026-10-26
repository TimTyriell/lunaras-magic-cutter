"""Ingest board feedback: log every verdict as a learning, apply window tweaks, list picks.

Usage: python scripts/feedback.py <path-to-feedback_<stem>.json>
- copies file to work/<stem>/feedback.json
- appends one line per judged candidate to knowledge/decisions.jsonl (stage "candidate")
- writes adjusted start/end back into candidates.json
- prints picked ids (input for /cut-clip)
"""
import json
import sys
from datetime import UTC, datetime

from paths import ROOT, dump, load, session_dir


def apply(cands, items):
    by_id = {c["id"]: c for c in cands}
    log = []
    for it in items:
        c = by_id.get(it["id"])
        if not c or not it.get("verdict"):
            continue
        if it.get("start") is not None and it.get("end") is not None:
            c["start"], c["end"] = float(it["start"]), float(it["end"])
        c["verdict"], c["note"] = it["verdict"], it.get("note", "")
        log.append({"stage": "candidate", "id": c["id"], "window": [c["start"], c["end"]], "type": c["type"],
                    "score": c["score"], "hook_line": c["hook_line"], "why": c["why"],
                    "verdict": it["verdict"], "reason": it.get("note", "")})
    return log


def main(path):
    fb = load(path)
    d = session_dir(fb["stem"])
    dump(fb, d / "feedback.json")
    cands = load(d / "candidates.json")
    log = apply(cands, fb["items"])
    dump(cands, d / "candidates.json")
    ts = datetime.now(UTC).isoformat(timespec="seconds")
    with open(ROOT / "knowledge" / "decisions.jsonl", "a", encoding="utf-8") as f:
        f.writelines(json.dumps({"ts": ts, "stem": fb["stem"], **e}, ensure_ascii=False) + "\n" for e in log)
    picks = [e["id"] for e in log if e["verdict"] == "pick"]
    print(f"logged {len(log)} verdicts; picks: {' '.join(picks) or '-'}")


if __name__ == "__main__":
    main(sys.argv[1])
