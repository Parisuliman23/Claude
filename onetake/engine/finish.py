"""Finish-step outputs: saved frames, carousel, story, trial reels, CapCut layer pack."""
import copy
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from . import analyze, config, draw, project, render, timeline


# ---------- frames ----------

def save_frame(name, t_out):
    """Grab a clean still (no captions) at output time t_out."""
    p = project.load(name)
    fr = _grab(p, t_out)
    d = project.pdir(name) / "frames"
    d.mkdir(exist_ok=True)
    k = len(list(d.glob("frame_*.jpg"))) + 1
    f = d / f"frame_{k:02d}.jpg"
    import cv2
    cv2.imwrite(str(f), fr, [cv2.IMWRITE_JPEG_QUALITY, 92])
    project.update(name, lambda q: q.setdefault("frames", []).append({"file": config.rel(f), "t": round(t_out, 2)}))
    return config.rel(f)


def refresh_frames(name):
    """Re-grab saved frames that are older than the footage (e.g. after `remaster` fixed the colours), so the
    carousel, story and cover use the same colours as the reel. Same files, same moments."""
    import cv2
    p = project.load(name)
    src = config.absolute(p["source"])
    if not src.exists():
        return 0
    n = 0
    for fm in p.get("frames", []):
        f = config.absolute(fm["file"])
        if fm.get("t") is None or (f.exists() and f.stat().st_mtime >= src.stat().st_mtime):
            continue
        try:
            cv2.imwrite(str(f), _grab(p, float(fm["t"])), [cv2.IMWRITE_JPEG_QUALITY, 92])
            n += 1
        except Exception:  # noqa: BLE001  (a moment that's no longer in the edit: keep the old still)
            pass
    return n


def _grab(p, t_out):
    segs = project.segments(p)
    _, ts = timeline.out_to_src(segs, t_out)
    fr = render.FrameReader(config.absolute(p["source"])).at(ts)
    s = config.settings()
    fr = render.cover_fit(fr, s["width"], s["height"])
    bc = p.get("burned_captions") or {}
    if bc.get("remove"):
        analyze.remove_burned_text(fr, bc.get("band"))
    tracks = {f["id"]: f["track"] for f in p.get("faces", {}).get("detected", [])}
    for c in p.get("faces", {}).get("covers", []):
        if c.get("face") in tracks:
            pos = analyze.face_at(tracks[c["face"]], ts)
            if pos:
                render._cover(fr, pos, c, s["width"], s["height"])
    return fr


def auto_frames(name, n=4):
    """If none were saved, pick frames spread across the reel."""
    p = project.load(name)
    T = timeline.total(project.segments(p))
    return [save_frame(name, T * (k + 0.5) / n) for k in range(n)]


# ---------- text helpers ----------

def kept_lines(p):
    return [l for l in project.lines(p) if not l["cut"]]


def hook_text(p):
    for ov in p.get("overlays", []):
        if ov.get("role") == "hook":
            return ov.get("params", {}).get("text", "")
    ls = kept_lines(p)
    return ls[0]["text"] if ls else ""


def _clean(t):
    return re.sub(r"\s+", " ", t).strip()


def auto_carousel(p, max_slides=7):
    ls = kept_lines(p)
    slides = [{"title": hook_text(p), "body": ""}]
    chunk = ""
    for l in ls[1:]:
        if len(chunk) + len(l["text"]) > 140 and chunk:
            slides.append({"title": "", "body": _clean(chunk)})
            chunk = ""
        chunk += " " + l["text"]
    if chunk.strip():
        slides.append({"title": "", "body": _clean(chunk)})
    slides = slides[:max_slides - 1]
    slides.append({"title": "Save this for later", "body": "and follow for more like this"})
    return slides


# ---------- slide drawing ----------

def _bg(path, W, H):
    img = Image.open(path).convert("RGB")
    sc = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * sc + 1), int(img.height * sc + 1)), Image.LANCZOS)
    x, y = (img.width - W) // 2, (img.height - H) // 3
    return img.crop((x, y, x + W, y + H))


def _wrap(text, f, maxw):
    lines, cur = [], ""
    for w in text.split():
        nxt = (cur + " " + w).strip()
        if cur and f.getlength(nxt) > maxw:
            lines.append(cur)
            cur = w
        else:
            cur = nxt
    if cur:
        lines.append(cur)
    return lines


NO_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]")


def slide_image(slide, image, W, H, idx, total, theme):
    # the bundled fonts have no emoji; drop them rather than draw empty boxes
    slide = {k: NO_EMOJI.sub("", v).strip() if isinstance(v, str) else v for k, v in slide.items()}
    base = _bg(image, W, H) if image else Image.new("RGB", (W, H), draw.rgba(theme["accent"])[:3])
    base = base.convert("RGBA")
    grad = Image.new("L", (1, H))
    for y in range(H):
        grad.putpixel((0, y), int(225 * max(0, (y / H - 0.35) / 0.65) ** 1.3))
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    shade.putalpha(grad.resize((W, H)))
    img = Image.alpha_composite(base, shade)
    d = ImageDraw.Draw(img)
    ft = draw.font("Montserrat_900Black", 82)
    fb = draw.font("Montserrat_600SemiBold", 50)
    y = H - 110
    body = _wrap(slide.get("body", ""), fb, W - 160)
    title = _wrap(slide.get("title", "").upper(), ft, W - 200)
    blocks_h = len(title) * 100 + (30 if title and body else 0) + len(body) * 66
    y = H - 120 - blocks_h
    for l in title:
        w = ft.getlength(l)
        d.rounded_rectangle([80 - 14, y - 4, 80 + w + 18, y + 92], radius=12, fill=draw.rgba(theme["highlight"]))
        d.text((80, y + 44), l, font=ft, fill=draw.rgba(theme["highlight_text"]), anchor="lm")
        y += 100
    if title and body:
        y += 30
    for l in body:
        d.text((80, y + 30), l, font=fb, fill=(255, 255, 255, 255), anchor="lm", stroke_width=2, stroke_fill=(0, 0, 0, 160))
        y += 66
    if total > 1:
        for k in range(total):
            cx = W / 2 + (k - (total - 1) / 2) * 30
            d.ellipse([cx - 7, H - 52, cx + 7, H - 38], fill=(255, 255, 255, 255 if k == idx else 110))
    return img.convert("RGB")


THEME = {"accent": "#5B4BDB", "highlight": "#FFE14D", "highlight_text": "#111111"}


def _images(name, p, n):
    if refresh_frames(name):
        p = project.load(name)
    frs = sorted(p.get("frames", []), key=lambda f: 0 if f.get("star") else 1)  # starred cover first
    imgs = [config.absolute(f["file"]) for f in frs]
    imgs += [config.absolute(x) for x in p.get("finish_images", [])]
    if not imgs:
        imgs = [config.absolute(x) for x in auto_frames(name)]
    return [imgs[k % len(imgs)] for k in range(n)]


def carousel(name, slides=None):
    p = project.load(name)
    slides = slides or p.get("carousel", {}).get("slides") or auto_carousel(p)
    imgs = _images(name, p, len(slides))
    out = project.pdir(name) / "exports" / "carousel"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    files = []
    for k, sl in enumerate(slides):
        img = config.absolute(sl["image"]) if sl.get("image") else imgs[k]
        f = out / f"slide_{k + 1:02d}.jpg"
        slide_image(sl, img, 1080, 1350, k, len(slides), THEME).save(f, quality=92)
        files.append(config.rel(f))
    project.update(name, lambda q: q.setdefault("exports", {}).update({"carousel": files}))
    return files


def story(name, slides=None):
    p = project.load(name)
    slides = slides or p.get("story", {}).get("slides") or [
        {"title": hook_text(p), "body": "New reel is up. Tap to watch!"}]
    imgs = _images(name, p, len(slides))
    out = project.pdir(name) / "exports" / "story"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    files = []
    for k, sl in enumerate(slides):
        img = config.absolute(sl["image"]) if sl.get("image") else imgs[k]
        f = out / f"story_{k + 1:02d}.jpg"
        slide_image(sl, img, 1080, 1920, k, len(slides), THEME).save(f, quality=92)
        files.append(config.rel(f))
    project.update(name, lambda q: q.setdefault("exports", {}).update({"story": files}))
    return files


# ---------- trial reels ----------

def auto_trials(p):
    ls = kept_lines(p)
    T = timeline.total(project.segments(p))

    def punch(l):
        t = l["text"]
        return (3 if re.search(r"[$\d]", t) else 0) + (2 if "!" in t or "?" in t else 0) + (1 if len(t) < 70 else 0)

    cand = sorted(ls[1:], key=punch, reverse=True)
    trials = []
    if cand:
        trials.append({"name": "Cold open", "open_line": cand[0]["id"], "hook_text": cand[0]["text"]})
    trials.append({"name": "Short cut", "max_len": round(max(7.0, T * 0.6), 1),
                   "hook_text": " ".join(hook_text(p).split()[:7]) + "…"})
    if len(cand) > 1:
        trials.append({"name": "Different hook", "hook_text": cand[1]["text"]})
    return trials[:3]


def trials(name, specs=None, progress=None):
    p = project.load(name)
    specs = specs or p.get("trials") or auto_trials(p)
    files = []
    for k, v in enumerate(specs):
        f = project.pdir(name) / "exports" / f"trial_{k + 1}.mp4"
        render.render(name, f, variant=v,
                      progress=(lambda x, k=k: progress((k + x) / len(specs))) if progress else None)
        files.append({"file": config.rel(f), "name": v.get("name", f"Trial {k + 1}"), "hook": v.get("hook_text", "")})
    project.update(name, lambda q: (q.update({"trials": specs}), q.setdefault("exports", {}).update({"trials": files})))
    return files


# ---------- CapCut ----------

def srt(name, out):
    p = project.load(name)
    segs = project.segments(p)
    style = next((c for c in project.caption_styles() if c["id"] == p.get("caption_style")), project.caption_styles()[0])
    groups = timeline.caption_groups(p["words"], segs, style)

    def ts(x):
        ms = int(round(x * 1000))
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"

    lines = []
    for k, g in enumerate(groups):
        lines += [str(k + 1), f"{ts(g['start'])} --> {ts(g['end'])}", " ".join(p["words"][i]["t"] for i in g["w"]), ""]
    Path(out).write_text("\n".join(lines))


CAPCUT_README = """HOW TO OPEN THIS IN CAPCUT
=========================
Every file starts at 0:00 and is the full length of the reel, so they line up
automatically.

1. Open CapCut (desktop) and start a new project at 9:16.
2. Import all the files in this folder.
3. Drag 1_video.mp4 onto the main track at 0:00.
4. Drag 2_graphics.mov onto a track above it at 0:00 (stickers, GIFs, looks).
5. Drag 3_captions.mov onto a track above that at 0:00.
   (Prefer CapCut's own captions? Skip 3 and import captions.srt instead.)
6. Drag 4_music.m4a onto an audio track at 0:00.

The .mov layers have transparent backgrounds, so everything under them shows through.
"""


def capcut(name, progress=None):
    p = project.load(name)
    out = project.pdir(name) / "exports" / "capcut"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    voice_only = copy.deepcopy(p)
    voice_only["sound"] = {"src": None}
    steps = [("base", out / "1_video.mp4"), ("graphics", out / "2_graphics.mov"), ("captions", out / "3_captions.mov")]
    for k, (layer, f) in enumerate(steps):
        render.render(name, f, layer=layer, p=voice_only,
                      progress=(lambda x, k=k: progress((k + x) / 3.2)) if progress else None)
    snd = p.get("sound") or {}
    if snd.get("src"):
        T = timeline.total(project.segments(p))
        off = float(snd.get("offset", 0))
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-stream_loop", "-1", "-i",
                        str(config.absolute(snd["src"])), "-ss", str(off), "-t", f"{T:.3f}",
                        "-af", f"volume={float(snd.get('volume', 0.12))},afade=t=out:st={max(0, T - 1.5):.3f}:d=1.5",
                        "-c:a", "aac", "-b:a", "192k", str(out / "4_music.m4a")], check=True)
    srt(name, out / "captions.srt")
    (out / "HOW TO OPEN IN CAPCUT.txt").write_text(CAPCUT_README)
    z = out.with_suffix(".zip")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_STORED) as zf:
        for f in sorted(out.iterdir()):
            zf.write(f, f"{name}-capcut/{f.name}")
    if progress:
        progress(1.0)
    project.update(name, lambda q: q.setdefault("exports", {}).update({"capcut": config.rel(z)}))
    return config.rel(z)


# ---------- safe zone (edge check) ----------
# Instagram/TikTok cover the top bar, the caption + username at the bottom, and the like/comment/share
# buttons down the right. Looks there may be partly hidden; looks off the frame get cut.
SAFE = {"top": 0.045, "bottom": 0.80, "right_buttons_x": 0.86, "right_buttons_y": 0.45, "edge": 0.03}


def _box(p, ov, words, segs, W=1080, H=1920):
    """The overlay's box (x0, y0, x1, y1 as fractions) at the middle of its time on screen."""
    from . import looks as _looks
    sp = timeline.overlay_span(p, words, segs, ov)
    if not sp:
        return None
    a, b = sp
    ov = timeline.with_cues(ov, words, segs, a)
    if ov["kind"] == "look":
        img = _looks.frame(ov["look"], ov.get("params", {}), max(0.0, (b - a) - 0.05), b - a, W, H)  # fully built
        if img is None:
            return None
        sc = float(ov.get("scale", 1.0))
        bb = img.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox()  # visible pixels only
        if not bb:
            return None
        cx, cy = float(ov.get("x", 0.5)) * W, float(ov.get("y", 0.5)) * H
        x0 = cx + (bb[0] - img.width / 2) * sc
        x1 = cx + (bb[2] - img.width / 2) * sc
        y0 = cy + (bb[1] - img.height / 2) * sc
        y1 = cy + (bb[3] - img.height / 2) * sc
        return (x0 / W, y0 / H, x1 / W, y1 / H), a
    else:
        src = draw.emoji(ov["emoji"]) if ov["kind"] == "emoji" else draw.media_image(str(config.absolute(ov["src"])), 0)
        if src is None:
            return None
        w = float(ov.get("scale", 0.45)) * W
        h = w * src.height / max(1, src.width)
    cx, cy = float(ov.get("x", 0.5)) * W, float(ov.get("y", 0.5)) * H
    return ((cx - w / 2) / W, (cy - h / 2) / H, (cx + w / 2) / W, (cy + h / 2) / H), a


def caption_band(p):
    """(y0, y1) the captions occupy, or None when captions are off."""
    if not p.get("captions", True):
        return None
    st = next((s for s in project.caption_styles() if s["id"] == p.get("caption_style")), None) or {}
    cy = float(p["caption_y"]) if p.get("caption_y") is not None else float(st.get("y", 0.7))
    lines = 1 if (st.get("mode") == "single" or int(st.get("max_words", 3)) <= 2) else 2
    half = float(st.get("size", 80)) * 1.18 * lines / 2 / 1920 + 0.008
    return cy - half, cy + half


FULL_BLEED = {"jess_chalkboard", "jess_apples", "confetti", "title_card"}


def edge_check(p):
    """[{id, name, at, issue}] for looks that are partly hidden by the app's buttons/text, cover the captions, or
    run off the frame."""
    words, segs = p["words"], project.segments(p)
    band = caption_band(p)
    out = []
    for ov in p.get("overlays", []):
        r = _box(p, ov, words, segs)
        if not r:
            continue
        (x0, y0, x1, y1), at = r
        name = ov.get("look") or ov.get("emoji") or (ov.get("src") or "").split("/")[-1]
        if ov.get("look") in FULL_BLEED:  # meant to fill the frame edge to edge (chalkboard, confetti, apples…)
            continue
        issue = None
        if x0 < 0 or y0 < 0 or x1 > 1 or y1 > 1:
            issue = "runs off the edge"
        elif y0 < SAFE["top"]:
            issue = "under the top bar"
        elif y1 > SAFE["bottom"]:
            issue = "under your caption and username"
        elif x1 > SAFE["right_buttons_x"] and y1 > SAFE["right_buttons_y"]:
            issue = "under the like / comment / share buttons"
        elif band and ov.get("kind") == "look" and y0 < band[1] and y1 > band[0] and not ov.get("over_captions"):
            issue = "covers the captions"
        if issue:
            out.append({"id": ov["id"], "name": name, "at": round(at, 2), "issue": issue})
    return out


def fix_edges(p):
    """Move (and if needed shrink) the flagged looks into the safe area. Returns how many moved."""
    words, segs = p["words"], project.segments(p)
    flagged = {x["id"] for x in edge_check(p)}
    n = 0
    for ov in p.get("overlays", []):
        if ov["id"] not in flagged:
            continue
        r = _box(p, ov, words, segs)
        if not r:
            continue
        (x0, y0, x1, y1), _ = r
        w, h = x1 - x0, y1 - y0
        top, bottom, edge = SAFE["top"], SAFE["bottom"], SAFE["edge"]
        band = caption_band(p)
        if band and y0 < band[1] and y1 > band[0]:  # covers the captions: keep it on its side of them
            if (y0 + y1) / 2 < (band[0] + band[1]) / 2:
                bottom = band[0] - 0.01
            else:
                top = band[1] + 0.01
        right = SAFE["right_buttons_x"] if (y1 > SAFE["right_buttons_y"]) else 1 - edge
        maxw, maxh = right - edge, bottom - top
        k = min(1.0, maxw / max(w, 1e-6), maxh / max(h, 1e-6))
        if k < 1.0:
            ov["scale"] = round(float(ov.get("scale", 1.0 if ov["kind"] == "look" else 0.45)) * k * 0.98, 3)
        r2 = _box(p, ov, words, segs)  # after any shrink
        (x0, y0, x1, y1), _ = r2
        m = 0.01  # land a little inside the safe area, not on its edge
        dx = (max(0.0, edge - x0) + (m if x0 < edge else 0)) - (max(0.0, x1 - right) + (m if x1 > right else 0))
        dy = (max(0.0, top - y0) + (m if y0 < top else 0)) - (max(0.0, y1 - bottom) + (m if y1 > bottom else 0))
        ov["x"] = round(float(ov.get("x", 0.5)) + dx, 3)
        ov["y"] = round(float(ov.get("y", 0.5)) + dy, 3)
        n += 1
    return n


# ---------- storyboard ----------

def storyboard(name, progress=None, cols=4):
    """Every line of the reel as a numbered still (what it will really look like), in one image."""
    from PIL import ImageFont
    p = project.load(name)
    comp = render.Composer(name, p=p)
    segs = comp.segs
    ls = [l for l in project.lines(p) if not l["cut"]]
    shots = []
    for k, l in enumerate(ls):
        sp = timeline.range_out(p["words"], segs, l["w0"], l["w1"])
        if not sp:
            continue
        t = min(sp[0] + min(1.2, (sp[1] - sp[0]) * 0.6), comp.T - 0.05)
        import cv2
        fr = comp.frame(t)
        im = Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)).resize((270, 480))
        shots.append((im, t, l["text"]))
        if progress:
            progress((k + 1) / max(1, len(ls)))
    rows = (len(shots) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 290 + 20, rows * 560 + 20), (245, 243, 238))
    d = ImageDraw.Draw(sheet)
    fb = draw.font("Montserrat_900Black", 26)
    ft = draw.font("Inter_700Bold", 15)
    for k, (im, t, text) in enumerate(shots):
        x, y = 20 + (k % cols) * 290, 20 + (k // cols) * 560
        sheet.paste(im, (x, y))
        d.rounded_rectangle([x + 8, y + 430, x + 62, y + 466], radius=8, fill=(20, 20, 24))
        d.text((x + 35, y + 448), f"{k + 1:02d}", font=fb, fill=(255, 255, 255), anchor="mm")
        label = f"{int(t // 60)}:{int(t % 60):02d}  {text}"
        while ft.getlength(label) > 268 and len(label) > 8:
            label = label[:-2]
        if label != f"{int(t // 60)}:{int(t % 60):02d}  {text}":
            label = label.rstrip() + "…"
        d.text((x, y + 492), label, font=ft, fill=(40, 40, 48))
    out = project.pdir(name) / "exports" / "storyboard.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=88)
    project.update(name, lambda q: q.setdefault("exports", {}).update({"storyboard": config.rel(out)}))
    return config.rel(out)


# ---------- phone copy + cover ----------

def phone_copy(src, out):
    """A small copy to check on your phone like a viewer would (540x960, small file)."""
    subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(src), "-vf", "scale=540:960",
                    "-c:v", "libx264", *config.x264_light(), "-preset", "veryfast", "-crf", "28", "-pix_fmt", "yuv420p",
                    *config.BT709_TAGS, "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(out)], check=True)
    return out


def cover(name):
    """Copy the starred frame (or the first saved one) to exports/cover.jpg."""
    refresh_frames(name)
    p = project.load(name)
    fr = [f for f in p.get("frames", []) if f.get("star")] or p.get("frames", [])
    if not fr:
        return None
    out = project.pdir(name) / "exports" / "cover.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(config.absolute(fr[0]["file"]), out)
    return config.rel(out)
