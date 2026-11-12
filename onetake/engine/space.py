"""Free up the Chromebook's disk once a reel is finished and saved on the phone.

A reel's big files are its original clips (raw/), the full-size footage (source.mp4), the preview copies (cache/)
and the rendered videos (exports/). Once the finished MP4 is on the phone, none of them are needed: `free(name)`
deletes them for the reel and its versions, keeps the edit (project.json, small images like the carousel), and
marks the reel "archived" so the studio shows it as saved to the phone instead of opening a reel with no footage.
"""
import shutil
import time

from . import config, project

BIG_EXPORTS = {".mp4", ".mov", ".m4a", ".zip", ".wav"}


def _files(d):
    return [f for f in d.rglob("*") if f.is_file() and not f.is_symlink()] if d.exists() else []


def _big(d):
    """The files `free` would delete in one project folder."""
    out = _files(d / "raw") + _files(d / "cache") + [f for f in _files(d / "exports") if f.suffix.lower() in BIG_EXPORTS]
    src = d / "source.mp4"
    if src.is_file():
        out.append(src)
    return out


def family(name):
    """The reel and its versions (they share the footage, so they're freed together)."""
    root = project.load(name).get("variant_of") or name
    return [root] + [p["name"] for p in project.list_projects()
                     if p["name"] != root and project.load(p["name"]).get("variant_of") == root]


def freeable(name):
    """Bytes `free(name)` would give back (shared/hard-linked footage counted once)."""
    seen, total = set(), 0
    for n in family(name):
        for f in _big(project.pdir(n)):
            st = f.stat()
            if (st.st_dev, st.st_ino) not in seen:
                seen.add((st.st_dev, st.st_ino))
                total += st.st_size
    return total


def disk_free():
    return shutil.disk_usage(config.PROJECTS if config.PROJECTS.exists() else config.ROOT).free


def finished_file(name):
    """The rendered reel, if it's really there and complete (not a render that stopped partway)."""
    p = project.load(name)
    r = p.get("render") or {}
    f = config.absolute(r["file"]) if r.get("file") else None
    if r.get("status") != "done" or not f or not f.is_file() or f.stat().st_size < 1_000_000:
        return None
    try:
        import subprocess
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1",
                              str(f)], capture_output=True, text=True, timeout=30).stdout.strip()
        if float(out) < 0.9 * project.timeline.total(project.segments(p)):
            return None
    except Exception:  # noqa: BLE001
        return None
    return f


def free(name, force=False):
    """Delete the big files of a finished reel (and its versions). Returns bytes freed.
    Refuses unless the reel has a complete render (the video the user saved to their phone)."""
    if not force and not finished_file(name):
        raise SystemExit("This reel doesn't have a complete rendered video yet, so its footage wasn't deleted. "
                         "Render it (Lock in my looks), save it to your phone, then free up the space.")
    before = disk_free()
    names = family(name)
    for n in names:
        d = project.pdir(n)
        for sub in ("raw", "cache"):
            shutil.rmtree(d / sub, ignore_errors=True)
        for f in _big(d):
            f.unlink(missing_ok=True)

        def mark(q):
            q["archived"] = {"at": time.strftime("%Y-%m-%d %H:%M"), "freed_mb": 0}
            q.pop("render", None)  # the video is on the phone now, not here
            ex = q.get("exports") or {}
            for k in ("trials", "capcut", "capcut_project", "storyboard"):
                ex.pop(k, None)
        project.update(n, mark)
    freed = max(0, disk_free() - before)
    project.update(names[0], lambda q: q["archived"].update(freed_mb=round(freed / 1e6)))
    return freed
