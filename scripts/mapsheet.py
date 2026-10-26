"""Contact sheet of the VTT map region over a clip's source spans: pick map shots (cam "map") where the map is clean.

Usage: python scripts/mapsheet.py <stem> <id> [--step 3]
Samples every --step s inside each cut of scripts/<id>.edl.json (or, with <id> = <start>-<end>, a session-seconds
range), crops the layouts.toml map box and tiles 4 per row -> work/<stem>/mapsheets/<id>.jpg.
Prints the session time of each tile, row-major. Look for: VTT editor panels / asset bar / toolbars (not clean: use
the speaker cam there), and for tokens that match the line being spoken (father on the balcony, guard at the arch).
"""
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

from paths import CONFIG, edl_path, load, session_dir, source_path, team

COLS, TILE_W = 4, 420


def spans(stem, cid):
    if "-" in cid and cid.replace("-", "").replace(".", "").isdigit():
        a, b = map(float, cid.split("-"))
        return [(a, b)]
    return [(c["start"], c["end"]) for c in load(edl_path(stem, cid))["cuts"]]


def main(stem, cid, *flags):
    step = float(flags[flags.index("--step") + 1]) if "--step" in flags else 3.0
    x, y, w, h = tomllib.loads((CONFIG / "layouts.toml").read_text(encoding="utf-8"))[team(stem)]["map"]
    times = sorted({round(a + 0.3 + k * step, 1) for a, b in spans(stem, cid) for k in range(int((b - a - 0.5) / step) + 1)})
    out = session_dir(stem) / "mapsheets"
    out.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for i, t in enumerate(times):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(source_path(stem)), "-frames:v", "1",
                            "-vf", f"crop={w}:{h}:{x}:{y},scale={TILE_W}:-2", str(Path(tmp) / f"t_{i:03d}.png")], check=True)
        sheet = out / f"{cid}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(Path(tmp) / "t_%03d.png"),
                        "-vf", f"tile={COLS}x{-(-len(times) // COLS)}", "-frames:v", "1", "-q:v", "3", str(sheet)], check=True)
    print(sheet)
    print("tiles (row-major):", " ".join(f"{t:.1f}" for t in times))


if __name__ == "__main__":
    main(*sys.argv[1:])
