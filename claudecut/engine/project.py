"""Loading and saving projects (projects/<name>/project.json)."""
import json
import os
import re
import threading
import time
from pathlib import Path

from . import config, timeline

_lock = threading.RLock()


def slug(s):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s or time.strftime("reel-%Y%m%d-%H%M")


def pdir(name):
    d = config.PROJECTS / name
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name):
        raise ValueError(f"bad project name: {name}")
    return d


def exists(name):
    return (pdir(name) / "project.json").exists()


def load(name):
    with open(pdir(name) / "project.json") as f:
        return json.load(f)


def save(name, p, expect_rev=None):
    """Write atomically and bump rev. If expect_rev is given and the file on
    disk has moved on (Claude edited it), raise ConflictError."""
    with _lock:
        f = pdir(name) / "project.json"
        if expect_rev is not None and f.exists():
            cur = json.loads(f.read_text()).get("rev", 0)
            if cur != expect_rev:
                raise ConflictError(cur)
        p["rev"] = int(p.get("rev", 0)) + 1 if expect_rev is None else expect_rev + 1
        p["updated"] = time.time()
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(p, indent=1))
        os.replace(tmp, f)
        return p["rev"]


def update(name, fn):
    """Load, let fn mutate, save. Used by CLI/Claude so the studio sees the change."""
    with _lock:
        p = load(name)
        fn(p)
        save(name, p)
        return p


class ConflictError(Exception):
    def __init__(self, rev):
        self.rev = rev


def list_projects():
    out = []
    for d in sorted(config.PROJECTS.iterdir(), key=lambda d: -d.stat().st_mtime) if config.PROJECTS.exists() else []:
        f = d / "project.json"
        if f.exists():
            try:
                p = json.loads(f.read_text())
                out.append({"name": d.name, "title": p.get("title", d.name), "duration": p.get("duration"),
                            "updated": p.get("updated"), "render": p.get("render", {}).get("status")})
            except Exception:
                pass
    return out


def segments(p, words=None, order=None):
    s = config.settings()
    return timeline.build_segments(words or p["words"], p["duration"], s["max_gap"], s["pad_before"], s["pad_after"], order=order)


def lines(p):
    """Group word indices by line: [{id, w0, w1, text}]"""
    out = {}
    for i, w in enumerate(p["words"]):
        l = out.setdefault(w["l"], {"id": w["l"], "w0": i, "w1": i})
        l["w1"] = i
    res = sorted(out.values(), key=lambda l: l["w0"])
    for l in res:
        l["text"] = " ".join(p["words"][i]["t"] for i in range(l["w0"], l["w1"] + 1))
        l["cut"] = all(p["words"][i].get("cut") for i in range(l["w0"], l["w1"] + 1))
    return res


def new_id(prefix="o"):
    return f"{prefix}{int(time.time() * 1000) % 10**9:x}"


def caption_styles():
    return json.loads((config.LOOKBOOK / "captions.json").read_text())


def saved_looks():
    f = config.LOOKBOOK / "saved.json"
    return json.loads(f.read_text()) if f.exists() else []


def save_look(entry):
    looks = saved_looks()
    looks = [l for l in looks if l.get("id") != entry.get("id")]
    looks.append(entry)
    (config.LOOKBOOK / "saved.json").write_text(json.dumps(looks, indent=1))
