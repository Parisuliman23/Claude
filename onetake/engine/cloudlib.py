"""The B-roll library in Google Drive ("One Take/B-roll Library"), so the small Chromebook disk only holds the clips a reel
is using. Every clip in it is checked and described in the cloud index.json (same format as library/broll/index.json).

  push FILE…   move checked clips (and photos) from the Chromebook to the cloud library
  pull FILE…   copy clips from the cloud library back into library/broll or library/images for a reel
  search       broll-index also searches the cloud index (results say "cloud:" — pull them before using)
"""
import json
import shutil

from . import config

def root():
    """The cloud library folder, or None if Google Drive isn't shared with Linux."""
    from pathlib import Path
    d = config.drive_root()
    if not d:
        return None
    base = d / "One Take"
    if not base.exists():
        return None
    r = base / "B-roll Library"
    (r / "videos").mkdir(parents=True, exist_ok=True)
    (r / "photos").mkdir(parents=True, exist_ok=True)
    return r


def index_path():
    r = root()
    return r / "index.json" if r else None


def load():
    f = index_path()
    return json.loads(f.read_text()) if f and f.exists() else {}


def save(idx):
    f = index_path()
    if f:
        f.write_text(json.dumps(idx, indent=1))


def _local_index(kind):
    f = config.LIBRARY / ("broll" if kind == "video" else "images") / "index.json"
    return f, (json.loads(f.read_text()) if f.exists() else {})


def push(names, keep_local=False):
    """Copy checked clips/photos to the cloud library (with their description and credit), then remove the local copy
    unless keep_local. Unchecked or 'avoid' files are refused: the cloud library only holds good clips."""
    r = root()
    if not r:
        raise SystemExit("Google Drive isn't shared with Linux, so there's no cloud library.")
    cloud = load()
    done = []
    for name in names:
        name = name.split("/")[-1]
        kind = "photo" if name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")) else "video"
        f_idx, idx = _local_index(kind)
        e = idx.get(name)
        src = config.LIBRARY / ("broll" if kind == "video" else "images") / name
        if not src.exists() or not isinstance(e, dict) or not e.get("shows") or e.get("avoid"):
            print(f"  skipped {name}: " + ("not on this computer" if not src.exists() else "not checked / marked avoid"))
            continue
        cf = src.parent / "credits.json"
        credit = (json.loads(cf.read_text()).get(name) if cf.exists() else None) or {}
        dest = r / ("videos" if kind == "video" else "photos") / name
        if not dest.exists():
            shutil.copy2(src, dest)
        cloud[name] = {**e, "kind": kind, "credit": credit.get("credit"), "credit_needed": credit.get("credit_needed", False),
                       "source": credit.get("source"), "by": credit.get("by"), "url": credit.get("url")}
        if not keep_local:
            src.unlink()
            e["in_cloud"] = True
            f_idx.write_text(json.dumps(idx, indent=1))
        done.append(name)
    save(cloud)
    return done


def pull(names):
    """Copy files from the cloud library into the local library (and their index + credit entries)."""
    r = root()
    if not r:
        raise SystemExit("Google Drive isn't shared with Linux, so there's no cloud library.")
    cloud = load()
    got = []
    for name in names:
        name = name.split("/")[-1].replace("cloud:", "")
        e = cloud.get(name)
        if not e:
            print(f"  {name} isn't in the cloud library")
            continue
        kind = e.get("kind", "video")
        src = r / ("videos" if kind == "video" else "photos") / name
        folder = config.LIBRARY / ("broll" if kind == "video" else "images")
        folder.mkdir(parents=True, exist_ok=True)
        dest = folder / name
        if not dest.exists():
            shutil.copy2(src, dest)
        f_idx, idx = _local_index(kind)
        idx[name] = {k: v for k, v in e.items() if k in ("shows", "use_for", "not_for", "weak", "checked")}
        f_idx.write_text(json.dumps(idx, indent=1))
        if e.get("credit"):
            cf = folder / "credits.json"
            cr = json.loads(cf.read_text()) if cf.exists() else {}
            cr[name] = {"credit": e["credit"], "credit_needed": e.get("credit_needed", False), "source": e.get("source"),
                        "by": e.get("by"), "url": e.get("url")}
            cf.write_text(json.dumps(cr, indent=1))
        got.append(f"{config.rel(dest)}  ({e.get('shows')})")
    return got


def status():
    r = root()
    if not r:
        return "No cloud library (Google Drive isn't shared with Linux)."
    c = load()
    v = sum(1 for e in c.values() if isinstance(e, dict) and e.get("kind") == "video")
    ph = sum(1 for e in c.values() if isinstance(e, dict) and e.get("kind") == "photo")
    return f"Cloud B-roll library: {v} videos, {ph} photos  ({r})"
