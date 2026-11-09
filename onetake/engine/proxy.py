"""A small, light copy of the footage for the studio's live preview (540x960, keyframe every 0.5 s), so playing and
scrubbing stay smooth on a Chromebook. Renders always use the full-quality source; the proxy is only for watching."""
import subprocess
import threading

from . import config, project

_busy = set()


def path(name):
    return project.pdir(name) / "cache" / "proxy.mp4"


def ready(name):
    """The proxy's media path if it's there and up to date with the source, else None (and start making one)."""
    p = path(name)
    src = config.absolute(project.load(name)["source"])
    if p.exists() and p.stat().st_mtime >= src.stat().st_mtime:
        return config.rel(p)
    start(name)
    return None


def start(name):
    if name in _busy:
        return
    _busy.add(name)
    threading.Thread(target=_make, args=(name,), daemon=True).start()


def _make(name):
    try:
        src = config.absolute(project.load(name)["source"])
        out = path(name)
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_name("proxy.part.mp4")
        subprocess.run(["nice", "-n", "15", "ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(src),
                        "-vf", "scale=540:960", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-g", "15",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(tmp)],
                       check=True)
        tmp.replace(out)
    except Exception as e:  # noqa: BLE001 — the preview just keeps using the full-size video
        print("proxy:", e)
    finally:
        _busy.discard(name)
