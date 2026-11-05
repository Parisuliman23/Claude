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
import math
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

    # ---- your style's type system: one LOUD face + one HUMAN face
    LOUD = "Montserrat_900Black"          # heavy geometric caps
    HAND = "NanumPenScript_400Regular"    # thin handwritten pen
    BRUSH = "CaveatBrush_400Regular"      # brush handwriting (editorial look)
    SERIF = "InstrumentSerif_400Regular"  # high-contrast serif titles (editorial look)
    SANS = "Inter_700Bold"                # cinematic finance look
    SANS_X = "Inter_800ExtraBold"
    WHITE, HIGHLIGHT, CTA, RED, BLUE, GREEN = "#FFFFFF", "#FCFC04", "#FCF46C", "#FC1404", "#0444A4", "#044C34"

    def typed(self, text, cps=30.0, delay=0.0):
        """Typewriter: how much of `text` is visible now."""
        n = int(max(0.0, self.t - delay) * cps)
        return text[:n]

    def typed_done(self, text, cps=30.0, delay=0.0):
        return delay + len(text) / cps

    def image(self, rel):
        from . import config as _c
        return draw.load_image(str(_c.absolute(rel)))

    def shadowed(self, img, blur=6, offset=3, alpha=150):
        """Soft drop shadow behind white text/graphics so they read on any background."""
        pad = blur * 3
        out = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
        a = img.getchannel("A").point(lambda v: v * alpha // 255)
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sh.putalpha(a)
        out.alpha_composite(sh, (pad + offset, pad + offset))
        out = out.filter(ImageFilter.GaussianBlur(blur))
        out.alpha_composite(img, (pad, pad))
        return out

    def card(self, w, h, radius=18, fill="#FFFFFF", shadow=True):
        """White rounded card with a soft shadow (screenshots, badges, receipts)."""
        pad = 24 if shadow else 0
        img = Image.new("RGBA", (int(w) + pad * 2, int(h) + pad * 2), (0, 0, 0, 0))
        if shadow:
            sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(sh).rounded_rectangle([pad, pad + 6, pad + w, pad + h + 6], radius=radius, fill=(0, 0, 0, 90))
            img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(10)))
        ImageDraw.Draw(img).rounded_rectangle([pad, pad, pad + w, pad + h], radius=radius, fill=self.rgba(fill))
        return img, pad

    def curve(self, d, p0, p1, p2, progress, width=8, fill="#FFFFFF", head=True):
        """Hand-drawn style curved arrow: quadratic curve p0 -> p2 bent toward p1, drawn up to `progress` (0..1)."""
        progress = max(0.0, min(1.0, progress))
        if progress <= 0:
            return
        n = 40
        pts = []
        for i in range(int(n * progress) + 1):
            u = i / n
            pts.append(((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * p1[0] + u * u * p2[0],
                        (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * p1[1] + u * u * p2[1]))
        col = self.rgba(fill)
        if len(pts) > 1:
            d.line(pts, fill=col, width=width, joint="curve")
        if head and len(pts) > 1:
            (x1, y1), (x2, y2) = pts[-2], pts[-1]
            ang = math.atan2(y2 - y1, x2 - x1)
            L = width * 3.2
            for da in (2.6, -2.6):
                d.line([(x2, y2), (x2 + L * math.cos(ang + da), y2 + L * math.sin(ang + da))], fill=col, width=width)

    def write(self, text, font, size, maxw=None, chars=None, fill="#FFFFFF", align="center",
              line_gap=1.15, cursor=False, upper=False):
        """Lay out `text` (wrapped to maxw px) and draw the first `chars` characters of it.
        The image is always the size of the FULL text, so typing doesn't make it jump around.
        Words wrapped in _underscores_ are underlined (emphasis by style switch)."""
        if upper:
            text = text.upper()
        f = self.font(font, size)
        maxw = maxw or self.W * 0.84
        lines = []
        for para in text.split("\n"):
            lines += self.wrap(para, f, maxw) or [""]
        clean = [l.replace("_", "") for l in lines]
        widths = [f.getlength(l) for l in clean]
        lh = int(size * line_gap)
        W = int(max(widths + [1]) + size * 0.4)
        H = int(lh * len(lines) + size * 0.4)
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        left = chars if chars is not None else 10 ** 9
        col = self.rgba(fill)
        cur_xy = None
        for i, (raw, w) in enumerate(zip(lines, widths)):
            x = (W - w) / 2 if align == "center" else size * 0.2
            y = size * 0.2 + i * lh
            under = False
            for ch in raw:
                if ch == "_":
                    under = not under
                    continue
                if left <= 0:
                    break
                cw = f.getlength(ch)
                d.text((x, y + size * 0.85), ch, font=f, fill=col, anchor="ls")
                if under and ch != " ":
                    d.line([(x, y + size * 0.98), (x + cw, y + size * 0.98)], fill=col, width=max(2, size // 18))
                x += cw
                left -= 1
                cur_xy = (x, y)
            if left <= 0:
                break
            left -= 1  # the line break counts as a character
        if cursor and cur_xy and int(self.t * 2.5) % 2 == 0 and chars is not None and chars < len(text):
            d.line([(cur_xy[0] + 4, cur_xy[1] + size * 0.1), (cur_xy[0] + 4, cur_xy[1] + size * 0.95)], fill=col, width=3)
        return img

    def stack(self, parts, gap=10, align="center"):
        """Stack images vertically into one."""
        parts = [p for p in parts if p is not None]
        if not parts:
            return None
        W = max(p.width for p in parts)
        H = sum(p.height for p in parts) + gap * (len(parts) - 1)
        out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        y = 0
        for p in parts:
            out.alpha_composite(p, ((W - p.width) // 2 if align == "center" else 0, y))
            y += p.height + gap
        return out

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
