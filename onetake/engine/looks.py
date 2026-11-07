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


_card_cache = {}


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

    # ---- notebook style (look D): cream paper cards, handwriting typed on, yellow accents
    NB = {"cream": "#F1EDE3", "rule": "#DFDACF", "ink": "#1D1912", "gray": "#908B86", "faint": "#C9C4BA",
          "yellow": "#F2E07F", "sticky": "#EBD56E", "gold": "#EED98A", "white": "#FBFAF7", "navy": "#0C1522"}
    NB_LABEL = "Poppins_500Medium"
    NB_BOLD = "Poppins_700Bold"
    NB_SEMI = "Poppins_600SemiBold"
    NB_SERIF = "PlayfairDisplay_400Regular_Italic"
    NB_HAND = "ArchitectsDaughter_400Regular"

    def paper(self, w, h, ruled=0, grid=0, fill=None, radius=10, shadow=True, top=0):
        """A notebook card: cream paper with a soft shadow, optional ruled lines (every `ruled` px from `top`)
        or a faint grid. Returns (image, pad) like card(). Cached."""
        key = ("paper", int(w), int(h), ruled, grid, fill, radius, shadow, top)
        if key in _card_cache:
            img, pad = _card_cache[key]
            return img.copy(), pad
        img, pad = self.card(w, h, radius=radius, fill=fill or self.NB["cream"], shadow=shadow)
        d = ImageDraw.Draw(img)
        col = self.rgba(self.NB["rule"])
        if ruled:
            y = top + ruled
            while y < h - 4:
                d.line([(pad + 2, pad + y), (pad + w - 2, pad + y)], fill=col, width=2)
                y += ruled
        if grid:
            gc = self.rgba("#E8E4DA")  # a faint grid (opaque: drawing with alpha would punch holes in the card)
            for x in range(grid, int(w), grid):
                d.line([(pad + x, pad + 2), (pad + x, pad + h - 2)], fill=gc, width=1)
            for y in range(grid, int(h), grid):
                d.line([(pad + 2, pad + y), (pad + w - 2, pad + y)], fill=gc, width=1)
        _card_cache[key] = (img, pad)
        return img.copy(), pad

    def hand(self, d, xy, text, size, chars=None, fill=None, anchor="ls", track=0.07):
        """Handwriting (typed on when `chars` is given), letters spaced out a little like neat print.
        Returns the width of the full text."""
        f = self.font(self.NB_HAND, size)
        col = self.rgba(fill or self.NB["ink"])
        sp = size * track
        full = sum((f.getlength("mm") if c in "→←" else f.getlength(c)) + sp for c in text)
        shown = text if chars is None else text[:max(0, int(chars))]
        x, y = xy
        if anchor[0] == "m":
            x -= full / 2
        for c in shown:  # drawn twice, half a pixel apart: the weight of a fine felt-tip
            if c in "→←":  # the handwriting font has no arrows: draw one
                w = f.getlength("mm")
                yy = y - size * 0.3
                x1, x2 = (x, x + w) if c == "→" else (x + w, x)
                d.line([(x1, yy), (x2, yy)], fill=col, width=max(2, size // 14))
                k = 1 if c == "→" else -1
                d.line([(x2, yy), (x2 - k * size * 0.25, yy - size * 0.18)], fill=col, width=max(2, size // 14))
                d.line([(x2, yy), (x2 - k * size * 0.25, yy + size * 0.18)], fill=col, width=max(2, size // 14))
                x += w + sp
                continue
            d.text((x, y), c, font=f, fill=col, anchor="l" + anchor[1])
            d.text((x + max(1, size // 40), y), c, font=f, fill=col, anchor="l" + anchor[1])
            x += f.getlength(c) + sp
        return full

    def check(self, d, cx, cy, s, fill=None, width=None, progress=1.0):
        """A hand-drawn checkmark centered at (cx, cy), size s, drawn up to `progress`."""
        col = self.rgba(fill or self.NB["ink"])
        w = width or max(3, int(s * 0.1))
        p0, p1, p2 = (cx - s * 0.42, cy + s * 0.02), (cx - s * 0.12, cy + s * 0.32), (cx + s * 0.45, cy - s * 0.36)
        a = min(1.0, progress / 0.35)
        if a > 0:
            d.line([p0, (p0[0] + (p1[0] - p0[0]) * a, p0[1] + (p1[1] - p0[1]) * a)], fill=col, width=w, joint="curve")
        b = max(0.0, (progress - 0.35) / 0.65)
        if b > 0:
            d.line([p1, (p1[0] + (p2[0] - p1[0]) * b, p1[1] + (p2[1] - p1[1]) * b)], fill=col, width=w, joint="curve")

    ICONS = ("smile", "pages", "mic", "film", "photos", "bookmark", "follow", "chat", "search", "dollar", "card",
             "chart", "house", "calendar", "check")

    def icon(self, d, name, cx, cy, s, fill=None, width=3):
        """Simple line icons in the notebook style (no emoji): one of Ctx.ICONS, size s, centered."""
        col = self.rgba(fill or self.NB["ink"])
        h = s / 2
        L = lambda pts: d.line(pts, fill=col, width=width, joint="curve")
        box = lambda x0, y0, x1, y1, r=4: d.rounded_rectangle([cx + x0 * h, cy + y0 * h, cx + x1 * h, cy + y1 * h], radius=r, outline=col, width=width)
        if name == "smile":
            d.ellipse([cx - h, cy - h, cx + h, cy + h], outline=col, width=width)
            d.ellipse([cx - h * .4 - 2, cy - h * .3 - 2, cx - h * .4 + 2, cy - h * .3 + 2], fill=col)
            d.ellipse([cx + h * .4 - 2, cy - h * .3 - 2, cx + h * .4 + 2, cy - h * .3 + 2], fill=col)
            d.arc([cx - h * .5, cy - h * .3, cx + h * .5, cy + h * .5], 20, 160, fill=col, width=width)
        elif name == "pages":
            box(-.4, -.7, .8, .7); L([(cx - h * .8, cy - h * .3), (cx - h * .8, cy + h), (cx + h * .4, cy + h)])
        elif name == "mic":
            box(-.3, -1, .3, .25, r=int(h * .3)); d.arc([cx - h * .6, cy - h * .5, cx + h * .6, cy + h * .55], 0, 180, fill=col, width=width)
            L([(cx, cy + h * .55), (cx, cy + h)])
        elif name == "film":
            box(-.75, -.95, .75, .95)
            for x in (-.45, .45):
                L([(cx + x * h, cy - h * .95), (cx + x * h, cy + h * .95)])
            L([(cx - h * .45, cy), (cx + h * .45, cy)])
        elif name == "photos":
            box(-.6, -.6, .9, .9); L([(cx - h * .9, cy + h * .5), (cx - h * .9, cy - h * .9), (cx + h * .5, cy - h * .9)])
            L([(cx - h * .5, cy + h * .7), (cx, cy + h * .1), (cx + h * .3, cy + h * .4), (cx + h * .5, cy + h * .2), (cx + h * .8, cy + h * .7)])
        elif name == "bookmark":
            L([(cx - h * .6, cy - h), (cx + h * .6, cy - h), (cx + h * .6, cy + h), (cx, cy + h * .45), (cx - h * .6, cy + h), (cx - h * .6, cy - h)])
        elif name == "follow":
            d.ellipse([cx - h * .7, cy - h, cx + h * .1, cy - h * .2], outline=col, width=width)
            d.arc([cx - h * 1.1, cy - h * .1, cx + h * .5, cy + h * 1.5], 180, 360, fill=col, width=width)
            L([(cx + h * .7, cy - h * .5), (cx + h * .7, cy + h * .1)]); L([(cx + h * .4, cy - h * .2), (cx + h, cy - h * .2)])
        elif name == "chat":
            d.rounded_rectangle([cx - h, cy - h * .8, cx + h, cy + h * .5], radius=int(h * .4), outline=col, width=width)
            L([(cx - h * .4, cy + h * .5), (cx - h * .6, cy + h), (cx, cy + h * .5)])
        elif name == "search":
            d.ellipse([cx - h * .9, cy - h * .9, cx + h * .4, cy + h * .4], outline=col, width=width)
            L([(cx + h * .3, cy + h * .3), (cx + h, cy + h)])
        elif name == "dollar":
            d.text((cx, cy), "$", font=self.font(self.NB_BOLD, int(s * 1.1)), fill=col, anchor="mm")
        elif name == "card":
            box(-1, -.65, 1, .65); L([(cx - h, cy - h * .25), (cx + h, cy - h * .25)]); L([(cx - h * .7, cy + h * .3), (cx - h * .2, cy + h * .3)])
        elif name == "chart":
            L([(cx - h, cy - h), (cx - h, cy + h), (cx + h, cy + h)])
            L([(cx - h * .7, cy + h * .5), (cx - h * .2, cy), (cx + h * .2, cy + h * .3), (cx + h * .9, cy - h * .6)])
        elif name == "house":
            L([(cx - h, cy - h * .05), (cx, cy - h), (cx + h, cy - h * .05)]); box(-.7, -.25, .7, 1)
        elif name == "calendar":
            box(-.9, -.75, .9, .95); L([(cx - h * .9, cy - h * .3), (cx + h * .9, cy - h * .3)])
            L([(cx - h * .45, cy - h), (cx - h * .45, cy - h * .55)]); L([(cx + h * .45, cy - h), (cx + h * .45, cy - h * .55)])
        elif name == "check":
            self.check(d, cx, cy, s, fill=fill, width=width)

    def appear(self, t0, dur=0.1):
        """0 -> 1 as time passes t0 (quick fade, for parts of a card that come in one after another)."""
        return max(0.0, min(1.0, (self.t - t0) / dur)) if dur > 0 else float(self.t >= t0)

    def faded(self, img, a):
        if a >= 1:
            return img
        img = img.copy()
        img.putalpha(img.getchannel("A").point(lambda v: int(v * a)))
        return img

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
        """White rounded card with a soft shadow (screenshots, badges, receipts). Cached: looks redraw every frame."""
        key = (int(w), int(h), radius, str(fill), shadow)
        if key not in _card_cache:
            if len(_card_cache) > 64:
                _card_cache.clear()
            _card_cache[key] = self._card(*key)
        img, pad = _card_cache[key]
        return img.copy(), pad

    def shadows(self, size, rects, radius=8, blur=6, alpha=70, dy=4):
        """One soft shadow layer for several rounded rectangles (cached)."""
        key = (tuple(size), tuple(tuple(int(v) for v in r) for r in rects), radius, blur, alpha, dy)
        if key not in _card_cache:
            sh = Image.new("RGBA", tuple(size), (0, 0, 0, 0))
            d = ImageDraw.Draw(sh)
            for x0, y0, x1, y1 in key[1]:
                d.rounded_rectangle([x0, y0 + dy, x1, y1 + dy], radius=radius, fill=(0, 0, 0, alpha))
            _card_cache[key] = sh.filter(ImageFilter.GaussianBlur(blur))
        return _card_cache[key]

    def _card(self, w, h, radius, fill, shadow):
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


def _no_cues(v):
    """Word cues ({"w": i}) that weren't turned into seconds (no project at hand): show them right away."""
    if isinstance(v, dict):
        if isinstance(v.get("w"), int) and set(v) <= {"w", "dt"}:
            return 0.0
        return {k: _no_cues(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_no_cues(x) for x in v]
    return v


def params_for(look_id, params):
    m = load(look_id)
    p = dict(getattr(m, "META", {}).get("params", {}))
    p.update(_no_cues(params or {}))
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
