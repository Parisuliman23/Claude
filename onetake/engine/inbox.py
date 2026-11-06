"""Film on your phone, upload, done.

Your phone puts videos in a Google Drive folder ("One Take/Inbox"). On a Chromebook, Drive shows up
inside Linux once you share it (Files app: right-click "Google Drive" → Share with Linux), at
/mnt/chromeos/GoogleDrive/MyDrive. The studio watches the Inbox; each new video is edited in your
style, rendered, and the finished reel lands in "One Take/Ready", so it's on your phone again.
Originals move to "One Take/Originals". Any synced folder works (settings.json "inbox" / "outbox").
"""
import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

from . import config

DRIVE_ROOTS = [Path("/mnt/chromeos/GoogleDrive/MyDrive"), Path.home() / "Google Drive" / "My Drive",
               Path.home() / "GoogleDrive"]
STATE = config.PROJECTS / ".inbox.json"


def base():
    s = config.settings()
    if s.get("inbox"):
        return None
    return next((r for r in DRIVE_ROOTS if r.is_dir()), None)


def folders():
    """(inbox, ready, originals) or (None, None, None) when no synced folder is available."""
    s = config.settings()
    if s.get("inbox"):
        inbox = Path(os.path.expanduser(s["inbox"]))
        ready = Path(os.path.expanduser(s.get("outbox") or str(inbox.parent / "Ready")))
        return inbox, ready, inbox.parent / "Originals"
    b = base()
    if not b:
        return None, None, None
    root = b / "One Take"
    return root / "Inbox", root / "Ready", root / "Originals"


def ensure():
    inbox, ready, orig = folders()
    if not inbox:
        return False
    for d in (inbox, ready, orig):
        try:
            d.mkdir(parents=True, exist_ok=True)
        except OSError:
            return False
    return True


def status():
    inbox, ready, _ = folders()
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    return {"connected": bool(inbox and inbox.is_dir()), "inbox": str(inbox) if inbox else None,
            "ready": str(ready) if ready else None, **st}


def _videos(d):
    try:
        return sorted([f for f in d.iterdir() if f.is_file() and f.suffix.lower() in config.VIDEO_EXT
                       and not f.name.startswith(".")], key=lambda f: f.stat().st_mtime)
    except OSError:
        return []


def _busy():
    f = config.PROJECTS / ".newreel.json"
    return f.exists() and '"running"' in f.read_text()


_sizes = {}


def tick():
    """Take ONE finished upload from the Inbox (size unchanged since the last check) and start it."""
    if not ensure() or _busy():
        return None
    inbox, _, orig = folders()
    for f in _videos(inbox):
        try:
            size = f.stat().st_size
        except OSError:
            continue
        if size == 0 or _sizes.get(str(f)) != size:  # still uploading / syncing: check again next time
            _sizes[str(f)] = size
            continue
        _sizes.pop(str(f), None)
        config.DROP.mkdir(exist_ok=True)
        for old in config.DROP.iterdir():  # one reel at a time from the phone
            if old.suffix.lower() in config.VIDEO_EXT:
                return None
        dest = config.DROP / f"01_{f.stem}{f.suffix.lower()}"
        shutil.copy2(f, dest)
        try:
            orig.mkdir(parents=True, exist_ok=True)
            f.rename(orig / f.name)
        except OSError:
            pass
        STATE.write_text(json.dumps({"last": f.name, "started": time.time(), "status": "editing"}))
        (config.PROJECTS / ".newreel.json").write_text(json.dumps({"status": "running", "started": time.time()}))
        env = dict(os.environ, ONETAKE_NO_BROWSER="1", ONETAKE_AUTO_RENDER="1")
        subprocess.Popen(["bash", str(config.ROOT / "new-reel.sh")], cwd=config.ROOT, env=env,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        return f.name
    return None


def deliver(name):
    """Render the reel and put the MP4 in the Ready folder (called by new-reel.sh for phone uploads)."""
    from . import finish, project, render
    p = project.load(name)
    out = render.render(name, project.pdir(name) / "exports" / "reel.mp4", p=p)
    edit_rev = p.get("edit_rev", 0)
    phone = finish.phone_copy(out, out.with_name("reel_phone.mp4"))
    project.update(name, lambda q: q.update({"render": {"status": "done", "file": config.rel(out), "edit_rev": edit_rev,
                                                        "phone": config.rel(phone)}}))
    _, ready, _ = folders()
    dest = None
    if ready and ensure():
        title = "".join(ch for ch in (p.get("title") or name) if ch.isalnum() or ch in " -_").strip()[:60] or name
        dest = ready / f"{title} - One Take.mp4"
        shutil.copy2(out, dest)
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    st.update({"status": "ready", "ended": time.time(), "reel": name, "file": str(dest) if dest else None,
               "mp4": config.rel(out)})
    STATE.write_text(json.dumps(st))
    return dest


def watch(every=20):
    def loop():
        while True:
            try:
                tick()
            except Exception as e:  # never let the watcher take the studio down
                print("inbox:", e)
            time.sleep(every)
    threading.Thread(target=loop, daemon=True).start()
