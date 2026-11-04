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
    d = project.pdir(name) / "frames"
    d.mkdir(exist_ok=True)
    k = len(list(d.glob("frame_*.jpg"))) + 1
    f = d / f"frame_{k:02d}.jpg"
    import cv2
    cv2.imwrite(str(f), fr, [cv2.IMWRITE_JPEG_QUALITY, 92])
    project.update(name, lambda q: q.setdefault("frames", []).append({"file": config.rel(f), "t": round(t_out, 2)}))
    return config.rel(f)


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
    imgs = [config.absolute(f["file"]) for f in p.get("frames", [])]
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
