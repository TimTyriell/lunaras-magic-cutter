"""Dice-roll insert: PNG frames (1080x1920, alpha) of a Daggerheart duality roll, overlaid by render.py.

Usage: python scripts/dice.py --check            every d12/d6 value lands face up (prints ok)
       python scripts/dice.py --demo <out_dir>    renders the Folge 8 roll (3 s) for a look
EDL cut: "dice": {"hope": 12, "fear": 9, "adv": [6, 4], "mod": 5, "total": 36, "label": "Success with Hope"}
The cut keeps its session span, so the table audio runs under the insert; text "" = no subtitles.
assets/dice.html (three.js, scripted tumble) runs in headless Edge with SwiftShader (CPU WebGL, same pixels on
every machine) and POSTs each frame to a stdlib http server here. Frames are cached by spec + dice.html hash.
"""
import hashlib
import json
import subprocess
import sys
import tempfile
import threading
import urllib.parse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from paths import ROOT

FPS = 30
ASSETS = ROOT / "assets"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


def validate(spec):
    """Values in die range and the sum adds up (Daggerheart: advantage d6 are added, user 2026-10-25)."""
    assert 1 <= spec["hope"] <= 12 and 1 <= spec["fear"] <= 12, spec
    assert all(1 <= v <= 6 for v in spec.get("adv", [])), spec
    total = spec["hope"] + spec["fear"] + sum(spec.get("adv", [])) + spec.get("mod", 0)
    assert total == spec["total"], f"dice sum {total} != total {spec['total']}"
    assert spec.get("label"), "label, e.g. 'Success with Hope'"


def run_page(query, out=None, timeout=900):
    """Serve assets/, open dice.html?<query> in headless Edge, collect POSTs. Returns the /check or /done body."""
    result, done = {}, threading.Event()

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if self.path.startswith("/frame/"):
                (out / f"{int(self.path[7:]):03d}.png").write_bytes(body)
            else:
                result[self.path] = body.decode("utf-8", "replace")
                done.set()
            self.send_response(204)
            self.end_headers()

    srv = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(ASSETS)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with tempfile.TemporaryDirectory() as prof:  # own profile: never attaches to the user's open Edge
        p = subprocess.Popen([str(EDGE), "--headless=new", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                              f"--user-data-dir={prof}", "--no-first-run", "--window-size=1080,1920",
                              f"http://127.0.0.1:{srv.server_port}/dice.html?{query}"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            ok = done.wait(timeout)
        finally:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
            p.wait()
            srv.shutdown()
    if not ok:
        sys.exit("dice.html: timeout, no result")
    if "/error" in result:
        sys.exit(f"dice.html error: {result['/error']}")
    return result.get("/check") or result.get("/done")


def frames(spec, dur, root):
    """Render (or reuse) the frames for one insert -> dir with 000.png.. (dur * FPS frames)."""
    validate(spec)
    n = round(dur * FPS)
    key = hashlib.sha1(json.dumps([spec, n], sort_keys=True).encode() + (ASSETS / "dice.html").read_bytes()).hexdigest()
    out = Path(root) / f"dice_{key[:10]}"
    if not (out / f"{n - 1:03d}.png").exists():
        out.mkdir(parents=True, exist_ok=True)
        run_page(urllib.parse.urlencode({"spec": json.dumps(spec), "n": n, "fps": FPS}), out)
    return out


def check():
    got = json.loads(run_page("check=1", timeout=120))
    for sides in ("12", "6"):
        assert got[sides] == list(range(1, int(sides) + 1)), (sides, got[sides])
    print("ok")


if __name__ == "__main__":
    if sys.argv[1] == "--check":
        check()
    else:
        print(frames({"hope": 12, "fear": 9, "adv": [6, 4], "mod": 5, "total": 36, "label": "Success with Hope"},
                     3.0, sys.argv[2]))
