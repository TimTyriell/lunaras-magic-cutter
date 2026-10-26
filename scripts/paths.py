"""Shared paths. Source repos are read-only."""
import json
import os
import re
import subprocess
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_env(path):
    """Minimal .env reader (KEY=VALUE, # comments). Real environment variables win."""
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            key, sep, val = line.partition("=")
            if sep and not key.lstrip().startswith("#"):
                os.environ.setdefault(key.strip(), val.strip().strip("\"'"))


_load_env(ROOT / ".env")  # see .env.example
# Unset PNP_ROOT stays an obviously wrong path: imports (self-check) work, real runs fail with a clear name.
PNP = Path(os.environ.get("PNP_ROOT") or ROOT / "PNP_ROOT-not-set-see-.env.example")
FINAL = PNP / "pnp-crawl" / "transcripts_final"
OKF_SESSIONS = PNP / "pnp-knowledge" / "knowledge" / "bundle" / "splitter_des_ewigen" / "sessions"
YTDLP = os.environ.get("YTDLP") or (
    str(Path(os.environ["PY"]).parent / "yt-dlp.exe") if "PY" in os.environ else "yt-dlp")
CONFIG = ROOT / "config"
WORK = ROOT / "work"


def ytdlp_auth():
    """YouTube bot check needs cookies: config/cookies.txt (gitignored) or env YTDLP_BROWSER (default firefox).
    Signature challenge needs a JS runtime: node (yt-dlp defaults to deno only)."""
    cookies = CONFIG / "cookies.txt"
    auth = (["--cookies", str(cookies)] if cookies.exists()
            else ["--cookies-from-browser", os.environ.get("YTDLP_BROWSER", "firefox")])
    return [*auth, "--js-runtimes", "node"]


@lru_cache
def session_name(stem):
    """'Daggerheart - DSdE | Season 1 Folge 8 | Team A' -> 'Season 1 Folge 8 Team A'."""
    title = load(FINAL / f"{stem}.json")["video_title"]
    return re.sub(r'[<>:"/\\|?*]', "", " ".join(p.strip() for p in title.split("|")[1:])).strip() or stem


def session_dir(stem):
    return WORK / session_name(stem)


def clip_dir(stem, cid):
    return session_dir(stem) / "clips" / cid


def source_path(stem):
    """Full episode video, cached once by fetch.py."""
    return session_dir(stem) / "source.mp4"


def edl_path(stem, cid):
    """Multi-cut script for clip <cid> (written by hand or by Claude from a clip script)."""
    return session_dir(stem) / "scripts" / f"{cid}.edl.json"


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def team(stem):
    """'2026-09-22_Team-A_xyz' -> 'team-a'."""
    return stem.split("_")[1].lower()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(obj, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
