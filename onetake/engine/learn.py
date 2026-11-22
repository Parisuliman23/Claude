"""One Take learns from the user's own edits.

Every time the studio saves, the new edit is compared with the old one. What the user changes after Claude's edit is
the clearest signal of their taste: a cut-away they delete or swap, a graphic they remove or add, captions, music,
filter. Each change is written to lookbook/learned.jsonl with the words being said at that moment.

`python3 -m engine learned` sums it up (counts + recent examples). Claude reads it before every edit, follows the
patterns, and moves lasting ones into lookbook/STYLE.md ("Learned from my edits"). Cut-aways the user removes are
also marked in the B-roll index so they aren't picked for those words again.
"""
import json
import time

from . import config

LOG = config.LOOKBOOK / "learned.jsonl"


def _said(p, w0, w1):
    ws = p.get("words") or []
    try:
        return " ".join(w["t"] for w in ws[int(w0):int(w1) + 1] if not w.get("cut"))[:120]
    except (TypeError, ValueError):
        return ""


def _short(src):
    return (src or "white panel").split("/")[-1]


def changes(old, new):
    """What the user changed, as a list of small dicts."""
    out = []
    ob = {b.get("id"): b for b in old.get("broll", []) if b.get("id")}
    nb = {b.get("id"): b for b in new.get("broll", []) if b.get("id")}
    for i, b in ob.items():
        said = _said(old, b.get("w0"), b.get("w1"))
        if i not in nb:
            out.append({"type": "cutaway_removed", "clip": _short(b.get("src")), "said": said})
        elif nb[i].get("src") != b.get("src"):
            out.append({"type": "cutaway_swapped", "from": _short(b.get("src")), "to": _short(nb[i].get("src")), "said": said})
        elif nb[i].get("layout") != b.get("layout"):
            out.append({"type": "cutaway_layout", "from": b.get("layout"), "to": nb[i].get("layout"), "said": said})
    for i, b in nb.items():
        if i not in ob:
            out.append({"type": "cutaway_added", "clip": _short(b.get("src")), "layout": b.get("layout"),
                        "said": _said(new, b.get("w0"), b.get("w1"))})
    oo = {o.get("id"): o for o in old.get("overlays", []) if o.get("id")}
    no = {o.get("id"): o for o in new.get("overlays", []) if o.get("id")}
    for i, o in oo.items():
        if i not in no:
            out.append({"type": "graphic_removed", "look": o.get("look") or o.get("kind"),
                        "said": _said(old, o.get("w0"), o.get("w1"))})
        elif no[i].get("look") != o.get("look"):
            out.append({"type": "graphic_swapped", "from": o.get("look"), "to": no[i].get("look"),
                        "said": _said(old, o.get("w0"), o.get("w1"))})
    for i, o in no.items():
        if i not in oo:
            out.append({"type": "graphic_added", "look": o.get("look") or o.get("kind"),
                        "said": _said(new, o.get("w0"), o.get("w1"))})
    for key in ("caption_style", "filter"):
        if old.get(key) != new.get(key):
            out.append({"type": f"{key}_changed", "from": old.get(key), "to": new.get(key)})
    os_, ns = (old.get("sound") or {}), (new.get("sound") or {})
    if os_.get("src") != ns.get("src"):
        out.append({"type": "music_changed", "from": _short(os_.get("src")), "to": _short(ns.get("src"))})
    elif os_.get("volume") != ns.get("volume") and ns.get("volume") is not None:
        out.append({"type": "music_volume", "from": os_.get("volume"), "to": ns.get("volume")})
    return out


def record(name, old, new, who="user"):
    """Log what changed between two saves of a project (called by the studio on every save)."""
    if not old or not new:
        return []
    ch = changes(old, new)
    if not ch:
        return []
    now = time.time()
    with open(LOG, "a") as f:
        for c in ch:
            f.write(json.dumps({"t": round(now), "reel": name, "who": who, **c}) + "\n")
    _teach_index(ch)
    return ch


def _teach_index(ch):
    """A cut-away the user deleted or replaced: don't offer that clip for those words again."""
    from . import stock
    idx = stock.load_index()
    changed = False
    for c in ch:
        clip = c.get("clip") if c["type"] == "cutaway_removed" else c.get("from") if c["type"] == "cutaway_swapped" else None
        if clip and clip in idx and isinstance(idx[clip], dict) and c.get("said"):
            nf = idx[clip].setdefault("not_for", [])
            if c["said"] not in nf:
                nf.append(c["said"][:60])
                idx[clip]["rejected_by_user"] = idx[clip].get("rejected_by_user", 0) + 1
                changed = True
    if changed:
        stock.index_file().write_text(json.dumps(idx, indent=1))


def summary(last=40):
    """Counts by kind + the most recent changes, for Claude to read before an edit."""
    if not LOG.exists():
        return "Nothing learned yet: no studio changes recorded."
    rows = [json.loads(x) for x in LOG.read_text().splitlines() if x.strip()]
    from collections import Counter
    c = Counter(r["type"] for r in rows)
    looks_removed = Counter(r.get("look") for r in rows if r["type"] == "graphic_removed")
    looks_added = Counter(r.get("look") for r in rows if r["type"] == "graphic_added")
    clips_removed = Counter(r.get("clip") or r.get("from") for r in rows if r["type"] in ("cutaway_removed", "cutaway_swapped"))
    lines = [f"{len(rows)} changes learned from {len({r['reel'] for r in rows})} reel(s).",
             "By kind: " + ", ".join(f"{k} x{v}" for k, v in c.most_common())]
    if looks_removed:
        lines.append("Graphics the user deletes most: " + ", ".join(f"{k} x{v}" for k, v in looks_removed.most_common(6)))
    if looks_added:
        lines.append("Graphics the user adds themselves: " + ", ".join(f"{k} x{v}" for k, v in looks_added.most_common(6)))
    if clips_removed:
        lines.append("Cut-aways the user rejected: " + ", ".join(f"{k} x{v}" for k, v in clips_removed.most_common(8)))
    lines.append("Most recent:")
    for r in rows[-last:]:
        d = {k: v for k, v in r.items() if k not in ("t", "who")}
        lines.append("  " + time.strftime("%b %d", time.localtime(r["t"])) + " " + json.dumps(d)[:220])
    return "\n".join(lines)
