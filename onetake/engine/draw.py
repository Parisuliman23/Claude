"""Drawing helpers for the renderer: fonts, captions, animations, blending.
app/app.js mirrors captionLayout/animState so the preview matches."""
import math
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import config

ANIM_DUR = 0.3
# Your style: pops are near-instant (40->100% in ~3 frames), headline cards slide up in 0.2 s.
ANIM_DURS = {"snap": 0.1, "slide-up": 0.2, "slide-down": 0.2, "rise": 0.2, "fade-quick": 0.1}


def anim_dur(kind):
    return ANIM_DURS.get(kind, ANIM_DUR)


@lru_cache(maxsize=64)
def font(name, size):
    f = config.FONTS / f"{name}.ttf"
    return ImageFont.truetype(str(f), int(size))


def rgba(hexstr, alpha=None):
    h = hexstr.lstrip("#")
    if len(h) == 6:
        h += "FF"
    r, g, b, a = (int(h[i:i + 2], 16) for i in (0, 2, 4, 6))
    return (r, g, b, a if alpha is None else alpha)


def ease_out_cubic(x):
    return 1 - (1 - x) ** 3


def ease_out_back(x):
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def anim_state(kind, p):
    """p: 0 = fully out, 1 = fully in. Returns dx, dy (fraction of frame), scale, alpha, rot (deg)."""
    p = max(0.0, min(1.0, p))
    e = ease_out_cubic(p)
    st = {"dx": 0.0, "dy": 0.0, "scale": 1.0, "alpha": 1.0, "rot": 0.0}
    if kind == "fade":
        st["alpha"] = p
    elif kind == "pop":
        st["scale"] = max(0.0, ease_out_back(p))
        st["alpha"] = min(1.0, p * 3)
    elif kind == "slide-left":
        st["dx"] = -(1 - e) * 0.7
    elif kind == "slide-right":
        st["dx"] = (1 - e) * 0.7
    elif kind == "slide-up":
        st["dy"] = (1 - e) * 0.5
    elif kind == "slide-down":
        st["dy"] = -(1 - e) * 0.5
    elif kind == "spin":
        st["rot"] = (1 - e) * 360
        st["scale"] = e
    elif kind == "snap":
        st["scale"] = 0.4 + 0.6 * e
    elif kind == "rise":  # notebook cards: fade in while lifting a little (6 frames)
        st["alpha"] = p
        st["dy"] = (1 - e) * 0.015
    elif kind == "fade-quick":
        st["alpha"] = p
    elif kind == "zoom":
        st["scale"] = 1 + (1 - e) * 1.5
        st["alpha"] = p
    return st


def overlay_state(ov, t, s, e):
    """Animation state for an overlay visible from s to e at time t."""
    ai, ao = ov.get("anim_in", "pop"), ov.get("anim_out", "fade")
    if ai and ai != "none" and t - s < anim_dur(ai):
        return anim_state(ai, (t - s) / anim_dur(ai))
    if ao and ao != "none" and e - t < anim_dur(ao):
        return anim_state(ao, (e - t) / anim_dur(ao))
    return anim_state("none", 1)


def push_scale(ov, t, s, e):
    """Slow push-in on static screenshots/cards: grows ~6% over the time it's on screen."""
    if not ov.get("push"):
        return 1.0
    return 1.0 + 0.06 * max(0.0, min(1.0, (t - s) / max(0.1, e - s)))


_arr_cache = {}


def _arrays(img):
    """BGR pixels + blend weights for a PIL RGBA image, cached for reused (cached) images."""
    k = id(img)
    hit = _arr_cache.get(k)
    if hit and hit[0] is img:
        return hit[1:]
    a = np.asarray(img)
    bgr = np.ascontiguousarray(a[:, :, 2::-1])
    w1 = a[:, :, 3].astype(np.float32) / 255.0
    w2 = 1.0 - w1
    if len(_arr_cache) > 128:
        _arr_cache.clear()
    _arr_cache[k] = (img, bgr, w1, w2)
    return bgr, w1, w2


def blend(frame, img, cx, cy):
    """Alpha-blend a PIL RGBA image onto a BGR uint8 numpy frame, centered at (cx, cy)."""
    H, W = frame.shape[:2]
    w, h = img.size
    x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
    fx0, fy0, fx1, fy1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    bgr, w1, w2 = _arrays(img)
    sl = (slice(fy0 - y0, fy1 - y0), slice(fx0 - x0, fx1 - x0))
    dst = frame[fy0:fy1, fx0:fx1]
    frame[fy0:fy1, fx0:fx1] = cv2.blendLinear(np.ascontiguousarray(bgr[sl]), np.ascontiguousarray(dst),
                                              np.ascontiguousarray(w1[sl]), np.ascontiguousarray(w2[sl]))


@lru_cache(maxsize=256)
def _resized(key, w, h):
    kind, ref = key
    img = emoji(ref) if kind == "emoji" else (load_image(ref) if kind == "image" else None)
    return img.resize((max(1, w), max(1, h)), Image.LANCZOS)


def resized(kind, ref, w, h):
    """Cached resize of a static emoji/image; sizes are rounded so moving faces reuse the cache."""
    q = 4
    return _resized((kind, ref), int(round(w / q)) * q or q, int(round(h / q)) * q or q)


def transform(img, st):
    """Apply scale/rotation/alpha from an anim state to an RGBA image."""
    if st["scale"] != 1.0:
        sc = max(0.01, st["scale"])
        img = img.resize((max(1, int(img.width * sc)), max(1, int(img.height * sc))), Image.LANCZOS)
    if st["rot"]:
        img = img.rotate(st["rot"], resample=Image.BICUBIC, expand=True)
    if st["alpha"] < 1.0:
        img = img.copy()  # never touch cached images
        a = img.getchannel("A").point(lambda v: int(v * st["alpha"]))
        img.putalpha(a)
    return img


def case(text, style):
    if style.get("uppercase"):
        return text.upper()
    if style.get("lowercase"):
        return text.lower()
    return text


def caption_layout(words, idxs, style, W):
    """Lay out a caption group. Returns (lines, total_w, total_h) where lines =
    [[(i, text, fontname, size, x), ...], ...] with widths."""
    size = style["size"]
    maxw = W * 0.84
    items = []
    for i in idxs:
        w = words[i]
        emph = bool(w.get("hl"))
        fn = style.get("emph_font", style["font"]) if emph else style["font"]
        sz = size * (style.get("emph_scale", 1.0) if emph else 1.0)
        text = case(w["t"], style)
        f = font(fn, sz)
        items.append({"i": i, "text": text, "font": fn, "size": sz, "w": f.getlength(text), "emph": emph})
    space = font(style["font"], size).getlength(" ")
    lines, cur, cw = [], [], 0.0
    for it in items:
        add = it["w"] + (space if cur else 0)
        if cur and cw + add > maxw:
            lines.append((cur, cw))
            cur, cw = [], 0.0
            add = it["w"]
        cur.append(it)
        cw += add
    if cur:
        lines.append((cur, cw))
    return lines, space


def caption_image(words, group, active, style, W, t_in=None, chars=None):
    lines, space = caption_layout(words, group["w"], style, W)
    size = style["size"]
    lh = size * 1.18
    sw = int(style.get("stroke_w", 0))
    pad = sw + 24
    tw = max(lw for _, lw in lines) if lines else 0
    th = lh * len(lines)
    img = Image.new("RGBA", (int(tw + pad * 2), int(th + pad * 2)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    stroke = rgba(style.get("stroke_color", "#000000"))
    if style.get("box"):
        for li, (items, lw) in enumerate(lines):
            x0 = pad + (tw - lw) / 2 - size * 0.25
            y0 = pad + li * lh - size * 0.02
            d.rounded_rectangle([x0, y0, x0 + lw + size * 0.5, y0 + lh * 0.98], radius=size * 0.22, fill=rgba(style["box"]))
    if style.get("shadow"):
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        _draw_words(sd, lines, space, pad, tw, lh, size, style, active, shadow=True, chars=chars)
        sh = sh.filter(ImageFilter.GaussianBlur(size * 0.08))
        img = Image.alpha_composite(sh, img)
        d = ImageDraw.Draw(img)
    _draw_words(d, lines, space, pad, tw, lh, size, style, active, stroke=stroke, sw=sw, chars=chars)
    if style.get("pop") and t_in is not None and t_in < 0.15:
        img = transform(img, {"scale": 0.75 + 0.25 * ease_out_back(t_in / 0.15), "rot": 0, "alpha": 1, "dx": 0, "dy": 0})
    return img


def _draw_words(d, lines, space, pad, tw, lh, size, style, active, stroke=None, sw=0, shadow=False, chars=None):
    """chars: typewriter captions: only this many characters are drawn, then an underscore cursor."""
    left = 10 ** 9 if chars is None else chars
    for li, (items, lw) in enumerate(lines):
        x = pad + (tw - lw) / 2
        base = pad + li * lh + size * 0.92  # baseline
        for it in items:
            f = font(it["font"], it["size"])
            if style.get("active_box") and it["i"] == active and not shadow:
                pad_x, h = size * 0.16, size * 1.08
                d.rounded_rectangle([x - pad_x, base - size * 0.86, x + it["w"] + pad_x, base - size * 0.86 + h],
                                    radius=size * 0.2, fill=rgba(style["active_box"]))
            if shadow:
                fill = (0, 0, 0, 150)
            elif it["emph"]:
                fill = rgba(style.get("emph_color", style["color"]))
            elif it["i"] == active:
                fill = rgba(style.get("active_color", style["color"]))
            else:
                fill = rgba(style["color"])
            kw = {}
            if sw and not shadow:
                kw = {"stroke_width": sw, "stroke_fill": stroke}
            yoff = size * 0.06 if shadow else 0
            text = it["text"]
            if left <= 0:
                return
            if left < len(text):
                text = text[:left] + "_"
            d.text((x + yoff, base + yoff), text, font=f, fill=fill, anchor="ls", **kw)
            left -= len(it["text"]) + 1
            x += it["w"] + space


@lru_cache(maxsize=64)
def load_image(path, maxside=1400):
    img = Image.open(path)
    if getattr(img, "is_animated", False):
        return None
    img = img.convert("RGBA")
    if max(img.size) > maxside:
        r = maxside / max(img.size)
        img = img.resize((int(img.width * r), int(img.height * r)), Image.LANCZOS)
    return img


@lru_cache(maxsize=32)
def gif_frames(path, maxside=900):
    """[(frame RGBA, duration_s)] for animated GIF/WebP."""
    im = Image.open(path)
    out = []
    for n in range(getattr(im, "n_frames", 1)):
        im.seek(n)
        fr = im.convert("RGBA")
        if max(fr.size) > maxside:
            r = maxside / max(fr.size)
            fr = fr.resize((int(fr.width * r), int(fr.height * r)), Image.LANCZOS)
        out.append((fr, max(0.02, im.info.get("duration", 100) / 1000.0)))
    return out


def gif_frame_at(path, t):
    frames = gif_frames(path)
    total = sum(d for _, d in frames)
    t = t % total if total > 0 else 0
    for fr, d in frames:
        if t < d:
            return fr
        t -= d
    return frames[-1][0]


def media_image(path, t):
    img = load_image(path)
    return img if img is not None else gif_frame_at(path, t)


def emoji(code):
    return load_image(str(config.EMOJI / f"{code}.png"), 512)


def emoji_codes():
    return sorted(p.stem for p in config.EMOJI.glob("*.png"))


def filter_matrix(fl):
    """The filter's steps (gray, saturation, contrast, brightness, warmth, lift) are all linear per pixel, so they
    combine into one 3x4 color matrix: applying it once is several times faster than step by step."""
    luma = np.array([0.114, 0.587, 0.299], np.float64)  # B, G, R
    M, b = np.eye(3), np.zeros(3)

    def then(A, c=0.0):
        nonlocal M, b
        M, b = A @ M, A @ b + c
    if fl.get("gray"):
        g = fl["gray"]
        then((1 - g) * np.eye(3) + g * np.outer(np.ones(3), luma))
    sat = fl.get("sat", 1.0)
    if sat != 1.0:
        then(sat * np.eye(3) + (1 - sat) * np.outer(np.ones(3), luma))
    c = fl.get("contrast", 1.0)
    if c != 1.0:
        then(c * np.eye(3), 128.0 * (1 - c))
    then(fl.get("bright", 1.0) * np.eye(3))
    w = fl.get("warm", 0.0)
    if w:
        then(np.diag([1 - w, 1.0, 1 + w]))  # less blue, more red
    lift = fl.get("lift", 0.0)
    if lift:
        then((1 - lift) * np.eye(3), lift * 255.0)
    return np.hstack([M, b[:, None]])


def apply_filter(frame, fl):
    """Color filter on a BGR frame. Mirrored (approximately) by CSS filters in the studio preview."""
    if not fl or fl.get("id") in (None, "none"):
        return frame
    return cv2.transform(frame, filter_matrix(fl))  # rounds and clips to 0-255
