"""A growing collection of the user's REAL voice (no AI voices), for training a professional ElevenLabs clone.

Lives in Google Drive "One Take/My voice". Every reel imported into One Take adds its speech there automatically
(pauses removed, volume evened out, cut into files under ElevenLabs' 11 MB limit). The user can also drop their own
old videos / recordings into that folder; `voice-bank` cleans them too. Goal: ~30 minutes, then the user creates a
Professional Voice Clone in ElevenLabs with these files.
"""
import json
import subprocess
from pathlib import Path

from . import config

GOAL_MIN = 30
CLEAN = "highpass=f=70,silenceremove=stop_periods=-1:stop_duration=0.6:stop_threshold=-40dB,loudnorm=I=-18:TP=-2:LRA=11"
VIDEO_AUDIO = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".m4a", ".wav", ".aac", ".ogg"}


def root():
    base = Path("/mnt/chromeos/shared/GoogleDrive/MyDrive/One Take")
    if not base.exists():
        return None
    r = base / "My voice"
    (r / "clean").mkdir(parents=True, exist_ok=True)
    return r


def _dur(f):
    try:
        return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                                    capture_output=True, text=True, timeout=60).stdout.strip() or 0)
    except Exception:  # noqa: BLE001
        return 0.0


def add(src, name):
    """Clean the speech in `src` (video or audio) into My voice/clean/<name>-NN.mp3 pieces. Returns minutes added."""
    r = root()
    if not r:
        return 0.0
    out = r / "clean"
    if list(out.glob(f"{name}-*.mp3")):
        return 0.0  # already in the bank
    tmp = out / f".{name}.mp3"
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "44100",
                    "-af", CLEAN, "-c:a", "libmp3lame", "-b:a", "128k", str(tmp)], check=True, timeout=1800)
    secs = _dur(tmp)
    if secs < 10:  # (almost) no speech
        tmp.unlink(missing_ok=True)
        return 0.0
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(tmp), "-f", "segment", "-segment_time", "300",
                    "-c", "copy", str(out / f"{name}-%02d.mp3")], check=True, timeout=600)
    tmp.unlink(missing_ok=True)
    _log(name, secs)
    return secs / 60


def _log(name, secs):
    r = root()
    f = r / "bank.json"
    d = json.loads(f.read_text()) if f.exists() else {}
    d[name] = round(secs, 1)
    f.write_text(json.dumps(d, indent=1))


def add_project(name):
    """Called after an import: the reel's own speech goes in the bank (skipped for AI-voice projects)."""
    from . import project
    p = project.load(name)
    if p.get("ai_voice"):
        return 0.0
    return add(config.absolute(p["source"]), f"reel-{name}")


def scan():
    """Clean any video/audio the user dropped straight into the My voice folder."""
    r = root()
    added = 0.0
    for f in sorted(r.iterdir()) if r else []:
        if f.is_file() and f.suffix.lower() in VIDEO_AUDIO:
            added += add(f, "own-" + "".join(c if c.isalnum() else "-" for c in f.stem)[:40])
    return added


def status():
    r = root()
    if not r:
        return "No Google Drive, so no voice bank."
    secs = sum(_dur(f) for f in (r / "clean").glob("*.mp3"))
    m = secs / 60
    return (f"Your real voice collected: {m:.1f} of {GOAL_MIN} minutes"
            + (" - enough for a Professional Voice Clone!" if m >= GOAL_MIN else f" ({GOAL_MIN - m:.1f} to go)")
            + f"\n  {r / 'clean'}")
