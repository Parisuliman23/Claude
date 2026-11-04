"""Looks are small animated graphics written in Python (lookbook/looks/*.py,
custom ones in lookbook/looks/custom/). Each file defines:

    META = {"name": "...", "description": "...", "params": {...defaults...}}
    def render(ctx):   # -> PIL RGBA image (just the graphic, not the full frame) or None

ctx gives: t (seconds since the look appeared), dur, W, H, p (params merged
with defaults), font(name, size), rgba("#hex"), emoji(code), ease(x),
ease_back(x), Image, ImageDraw, ImageFilter.
The renderer positions/animates the returned image like any sticker.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from . import config, draw

LOOK_DIRS = [config.LOOKBOOK / "looks", config.LOOKBOOK / "looks" / "custom"]


class Ctx:
    Image = Image
    ImageDraw = ImageDraw
    ImageFilter = ImageFilter

    def __init__(self, t, dur, W, H, p):
        self.t, self.dur, self.W, self.H, self.p = t, dur, W, H, p

    font = staticmethod(draw.font)
    rgba = staticmethod(draw.rgba)
    emoji = staticmethod(draw.emoji)
    ease = staticmethod(draw.ease_out_cubic)
    ease_back = staticmethod(draw.ease_out_back)

    def text_size(self, text, f):
        l, t, r, b = f.getbbox(text)
        return r - l, b - t

    def wrap(self, text, f, maxw):
        words, lines, cur = text.split(), [], ""
        for w in words:
            nxt = (cur + " " + w).strip()
            if cur and f.getlength(nxt) > maxw:
                lines.append(cur)
                cur = w
            else:
                cur = nxt
        if cur:
            lines.append(cur)
        return lines


_cache = {}


def find(look_id):
    for d in LOOK_DIRS:
        f = d / f"{look_id}.py"
        if f.exists():
            return f
    raise KeyError(f"no look named {look_id}")


def load(look_id):
    f = find(look_id)
    key = (str(f), f.stat().st_mtime)
    if key not in _cache:
        spec = importlib.util.spec_from_file_location(f"look_{look_id}", f)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _cache[key] = mod
    return _cache[key]


def all_looks():
    out = []
    for d in LOOK_DIRS:
        for f in sorted(d.glob("*.py")):
            if f.name.startswith("_"):
                continue
            try:
                m = load(f.stem)
                meta = dict(getattr(m, "META", {}))
                out.append({"id": f.stem, "custom": d.name == "custom", "name": meta.get("name", f.stem),
                            "description": meta.get("description", ""), "params": meta.get("params", {}),
                            "group": meta.get("group", "custom" if d.name == "custom" else "look")})
            except Exception as e:  # a broken custom look shouldn't break the studio
                out.append({"id": f.stem, "custom": True, "name": f.stem, "error": str(e), "params": {}})
    return out


def params_for(look_id, params):
    m = load(look_id)
    p = dict(getattr(m, "META", {}).get("params", {}))
    p.update(params or {})
    return p


def frame(look_id, params, t, dur, W, H):
    m = load(look_id)
    return m.render(Ctx(t, dur, W, H, params_for(look_id, params)))


def sprite(look_id, params, dur, out_dir, W=1080, H=1920, fps=10, scale=0.5, max_len=6.0):
    """Render a preview sprite sheet (frames side by side) for the browser.
    Returns {url, fps, n, w, h} where w/h are the full-size graphic dimensions."""
    dur = max(0.5, min(dur, max_len))
    key = hashlib.sha1(json.dumps([look_id, params, round(dur, 2), str(find(look_id).stat().st_mtime)],
                                  sort_keys=True).encode()).hexdigest()[:16]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    png, meta_f = out_dir / f"look_{key}.png", out_dir / f"look_{key}.json"
    if meta_f.exists() and png.exists():
        return json.loads(meta_f.read_text())
    n = max(1, int(dur * fps))
    frames = [frame(look_id, params, i / fps, dur, W, H) for i in range(n)]
    frames = [f if f is not None else Image.new("RGBA", (2, 2)) for f in frames]
    fw = max(f.width for f in frames)
    fh = max(f.height for f in frames)
    cw, ch = max(1, int(fw * scale)), max(1, int(fh * scale))
    sheet = Image.new("RGBA", (cw * n, ch), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        cell = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
        cell.paste(f, ((fw - f.width) // 2, (fh - f.height) // 2))
        sheet.paste(cell.resize((cw, ch), Image.LANCZOS), (i * cw, 0))
    sheet.save(png)
    meta = {"url": "/media/" + config.rel(png), "fps": fps, "n": n, "w": fw, "h": fh}
    meta_f.write_text(json.dumps(meta))
    return meta


def still(look_id, params, out_png, at=None, dur=3.0):
    """A single preview image (used for option thumbnails and by Claude to check its work)."""
    img = frame(look_id, params, at if at is not None else dur * 0.6, dur, 1080, 1920)
    bg = Image.new("RGBA", (img.width + 80, img.height + 80), (40, 40, 48, 255))
    bg.alpha_composite(img, (40, 40))
    bg.convert("RGB").save(out_png)
    return out_png
