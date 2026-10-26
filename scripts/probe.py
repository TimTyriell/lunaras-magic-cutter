"""Word-level timing of a session window, for setting EDL cut points (GPU, faster-whisper).

Usage: <ttrpg_env python> scripts/probe.py <stem> <start_s> <end_s> [<start_s> <end_s> ...]
Prints `time:word` (session seconds) per window, read from work/<session>/source.mp4.
Several windows share one model load (~10 s each otherwise).
Use it before writing/refining scripts/<id>.edl.json: pnp-crawl segments are coarse and their
speaker labels unreliable; these word times show where sentences really start and end.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from paths import source_path


def windows(stem, bounds):
    """Yield (a, b, lines) per window, lines = one string of `time:word` per Whisper segment. One model load."""
    import torch  # noqa: F401  ponytail: puts torch/lib (cublas64_12.dll) on the DLL path for ctranslate2
    from faster_whisper import WhisperModel

    model = WhisperModel("large-v3", device="cuda", compute_type="float16")
    wav = Path(tempfile.gettempdir()) / f"lmc_probe_{os.getpid()}.wav"  # per process: sessions can probe in parallel
    for a, b in zip(map(float, bounds[::2]), map(float, bounds[1::2]), strict=True):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}",
                        "-i", str(source_path(stem)), "-ac", "1", "-ar", "16000", str(wav)], check=True)
        segs, _ = model.transcribe(str(wav), language="de", word_timestamps=True, vad_filter=True, beam_size=5)
        yield a, b, [" ".join(f"{a + w.start:.2f}:{w.word.strip()}" for w in s.words) for s in segs]
    wav.unlink(missing_ok=True)


def main(stem, *bounds):
    for a, b, lines in windows(stem, bounds):
        print(f"== {a:.2f}-{b:.2f}")
        print("\n".join(lines))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # PowerShell redirects would otherwise write cp1252 (umlauts)
    main(*sys.argv[1:])
