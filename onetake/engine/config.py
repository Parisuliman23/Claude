"""Paths and settings shared by every part of the engine."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DROP = ROOT / "drop-in-order"
PROJECTS = ROOT / "projects"
LIBRARY = ROOT / "library"
LOOKBOOK = ROOT / "lookbook"
ASSETS = ROOT / "assets"
FONTS = ASSETS / "fonts"
EMOJI = ASSETS / "emoji"
APP = ROOT / "app"

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
AUDIO_EXT = {".mp3", ".m4a", ".wav", ".aac", ".ogg", ".flac"}

DEFAULTS = {
    "width": 1080,
    "height": 1920,
    "fps": 30,
    "whisper_model": "small.en",
    "max_gap": 0.35,          # longer silences than this get cut
    "pad_before": 0.06,       # breathing room kept before a word
    "pad_after": 0.12,        # and after it
    "default_caption_style": "warm-chest",
    "default_hook_look": "typed_title",
    "music_volume": 0.12,
    "claude_bridge": "auto",  # auto | off  — let the studio send requests to Claude Code
    "port": 5178,
}


def settings():
    s = dict(DEFAULTS)
    f = ROOT / "settings.json"
    if f.exists():
        s.update(json.loads(f.read_text()))
    return s


def rel(p):
    """Path relative to ROOT, with forward slashes (what project.json stores)."""
    return Path(p).resolve().relative_to(ROOT).as_posix()


def absolute(r):
    p = (ROOT / r).resolve()
    if ROOT not in p.parents and p != ROOT:
        raise ValueError(f"path escapes the studio folder: {r}")
    return p


def is_chromebook():
    """Running in ChromeOS's Linux (Crostini)? There, Chrome's 'localhost' forwarding into Linux can
    break (ERR_CONNECTION_RESET), but penguin.linux.test always reaches the Linux container."""
    import os
    import socket
    return os.path.exists("/opt/google/cros-containers") or socket.gethostname() == "penguin"


def studio_host():
    """(address to listen on, name to open in the browser)."""
    s = settings()
    if s.get("bind"):
        return s["bind"], s.get("browser_host", "localhost")
    if is_chromebook():
        # the Linux container is only reachable from this Chromebook, so listening on all of its
        # addresses doesn't expose the studio to the network
        return "0.0.0.0", "penguin.linux.test"
    return "127.0.0.1", "localhost"


def studio_url(port=None):
    return f"http://{studio_host()[1]}:{port or settings()['port']}/"
