"""Grab still frames per candidate for the review board, without downloading the video.

Usage: python scripts/screens.py <stem> [--n 3]
Resolves the YouTube stream URL once (yt-dlp -g), then ffmpeg seeks each timestamp over HTTP.
Writes work/<stem>/screens/<id>_<k>.jpg (frames evenly inside the window). Re-run board.py after.
"""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from paths import FINAL, YTDLP, load, session_dir, ytdlp_auth


def times(c, n):
    span = c["end"] - c["start"]
    return [c["start"] + span * (k + 0.5) / n for k in range(n)]


def grab(url, t, out):
    if out.exists():
        return True
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", url, "-frames:v", "1",
                        "-vf", "scale=640:-2", "-q:v", "4", str(out)], check=False, capture_output=True)
    return r.returncode == 0


def main(stem, *flags):
    n = int(flags[flags.index("--n") + 1]) if "--n" in flags else 3
    d = session_dir(stem)
    url = load(FINAL / f"{stem}.json")["video_url"]
    r = subprocess.run([str(YTDLP), *ytdlp_auth(), "-g", "-f", "bv*[height<=720][ext=mp4]/bv*[height<=720]", url],
                       check=False, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"yt-dlp failed (cookies? see paths.ytdlp_auth):\n{r.stderr.strip()[-400:]}")
    stream = r.stdout.strip().splitlines()[0]
    (d / "screens").mkdir(exist_ok=True)
    jobs = [(t, d / "screens" / f"{c['id']}_{k}.jpg")
            for c in load(d / "candidates.json") for k, t in enumerate(times(c, n))]
    with ThreadPoolExecutor(6) as pool:  # ponytail: stream URL expires after ~6 h; rerun resolves a fresh one
        ok = sum(pool.map(lambda j: grab(stream, *j), jobs))
    print(f"{ok}/{len(jobs)} frames -> {d / 'screens'}")


if __name__ == "__main__":
    main(*sys.argv[1:])
