"""More places to get B-roll, and a way for Claude to check a clip shows what was said.

- Pexels (pexels.com/api): free stock videos, free key ("pexels_key" in settings.json or PEXELS_API_KEY).
  Pexels License: free to use, no attribution needed (credits are kept in library/broll/credits.json anyway).
- Internet Archive (archive.org): real archival footage (old trading floors, news broadcasts, newsreels). No key.
  Only the curated public-domain Prelinger and Universal Newsreels collections are searched; long films are cut to the seconds you pick.
- check(files): one contact sheet (4 frames per clip, labelled) that Claude looks at before using any clip.
"""
import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request

from . import config

UA = {"User-Agent": "OneTakeStudio/1.0 (reels editor)"}
BROLL = config.LIBRARY / "broll"


def _json(url, headers=None):
    req = urllib.request.Request(url, headers=dict(UA, **(headers or {})))
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode())


def _download(url, dest, headers=None):
    tmp = dest.with_suffix(".part")
    req = urllib.request.Request(url, headers=dict(UA, **(headers or {})))
    with urllib.request.urlopen(req, timeout=180) as r, open(tmp, "wb") as fh:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            fh.write(chunk)
    tmp.rename(dest)


def _credit(dest, **kw):
    cf = BROLL / "credits.json"
    credits = json.loads(cf.read_text()) if cf.exists() else {}
    credits[dest.name] = kw
    cf.write_text(json.dumps(credits, indent=1))


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "clip"


# ---------- Pexels ----------

def pexels_key():
    return (os.environ.get("PEXELS_API_KEY") or config.settings().get("pexels_key") or "").strip()


def save_pexels_key(k):
    f = config.ROOT / "settings.json"
    s = json.loads(f.read_text()) if f.exists() else {}
    s["pexels_key"] = k.strip()
    f.write_text(json.dumps(s, indent=1))


def pexels(query, n=3, max_secs=30):
    """Download up to n Pexels clips for `query` (portrait first). Returns library paths."""
    k = pexels_key()
    if not k:
        raise RuntimeError("Add a free Pexels key first: pexels.com/api → 'Get started', then "
                           "python3 -m engine broll-key --pexels YOUR_KEY")
    q = urllib.parse.urlencode({"query": query, "per_page": max(5, min(40, n * 4)), "size": "medium"})
    try:
        hits = _json("https://api.pexels.com/videos/search?" + q, {"Authorization": k}).get("videos", [])
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            raise RuntimeError("Pexels didn't accept the key. Copy it again from pexels.com/api and save it.")
        raise
    hits = [h for h in hits if (h.get("duration") or 0) <= max_secs]
    hits.sort(key=lambda h: 0 if h.get("height", 0) > h.get("width", 0) else 1)
    BROLL.mkdir(parents=True, exist_ok=True)
    got = []
    for h in hits:
        if len(got) >= n:
            break
        files = [f for f in h.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width")]
        if not files:
            continue
        # about 1080 on the short side is plenty; avoid 4K downloads on a small computer
        f = sorted(files, key=lambda f: abs(min(f["width"], f["height"]) - 1080))[0]
        dest = BROLL / f"{_slug(query)}-px{h['id']}.mp4"
        if not dest.exists():
            _download(f["link"], dest)
        _credit(dest, by=(h.get("user") or {}).get("name"), url=h.get("url"), source="Pexels", search=query)
        got.append(config.rel(dest))
    return got


# ---------- Internet Archive ----------

# curated public-domain collections only (anyone can upload to archive.org, so open search returns junk):
# the Prelinger Archives (industrial / educational films) and Universal Newsreels (real news, 1929-1967)
PD = "collection:(prelinger OR prelinger_library OR universal_newsreels)"


def archive_search(query, n=8):
    """Public-domain films matching `query`: [{id, title, year, minutes}]. Nothing is downloaded."""
    q = urllib.parse.urlencode({"q": f"(title:({query}) OR subject:({query}) OR description:({query})) AND mediatype:movies AND {PD}", "fl[]": ["identifier", "title", "year"],
                                "rows": n, "output": "json", "sort[]": "downloads desc"}, doseq=True)
    docs = _json("https://archive.org/advancedsearch.php?" + q).get("response", {}).get("docs", [])
    return [{"id": d["identifier"], "title": d.get("title", ""), "year": d.get("year", "")} for d in docs]


def _archive_mp4(ident):
    meta = _json(f"https://archive.org/metadata/{urllib.parse.quote(ident)}")
    files = [f for f in meta.get("files", []) if f.get("name", "").lower().endswith(".mp4")]
    if not files:
        raise RuntimeError(f"{ident} has no MP4 version to cut from.")
    f = sorted(files, key=lambda f: int(f.get("size") or 0))[-1] if len(files) > 1 else files[0]
    # prefer the h.264 derivative (small, plays everywhere) when there is one
    h264 = [x for x in files if "h.264" in (x.get("format") or "").lower()]
    f = h264[0] if h264 else f
    return f"https://archive.org/download/{urllib.parse.quote(ident)}/{urllib.parse.quote(f['name'])}", meta


def archive_clip(ident, start=0.0, dur=8.0):
    """Cut `dur` seconds from `start` of an Internet Archive film straight into library/broll (only that part is
    downloaded)."""
    url, meta = _archive_mp4(ident)
    BROLL.mkdir(parents=True, exist_ok=True)
    dest = BROLL / f"archive-{_slug(ident)}-{int(start)}s.mp4"
    if not dest.exists():
        subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-ss", str(start), "-i", url, "-t", str(dur),
                        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                        *config.BT709_TAGS, str(dest)], check=True)
    title = (meta.get("metadata") or {}).get("title", ident)
    _credit(dest, by=title, url=f"https://archive.org/details/{ident}", source="Internet Archive (public domain)",
            search=ident)
    return config.rel(dest)


def archive_preview(ident, out, every=20, cols=6, rows=5):
    """A sheet of frames every `every` seconds of an Archive film (to choose where to cut), labelled with times."""
    url, _ = _archive_mp4(ident)
    _sheet_from(url, out, every, cols, rows)
    return out


# ---------- checking clips ----------

def _sheet_from(src, out, every, cols, rows):
    from PIL import Image, ImageDraw
    from . import draw
    W, H = 220, 140
    sheet = Image.new("RGB", (cols * W, rows * H), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    f = draw.font("Inter_700Bold", 16)
    for k in range(cols * rows):
        t = k * every
        r = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", str(t), "-i", str(src), "-frames:v", "1",
                            "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease", "-f", "image2pipe", "-vcodec",
                            "png", "-"], capture_output=True, timeout=120)
        if not r.stdout:
            break
        import io
        im = Image.open(io.BytesIO(r.stdout)).convert("RGB")
        x, y = (k % cols) * W, (k // cols) * H
        sheet.paste(im, (x + (W - im.width) // 2, y + (H - im.height) // 2))
        d.text((x + 6, y + 4), f"{int(t // 60)}:{int(t % 60):02d}", font=f, fill=(255, 230, 80))
    sheet.save(out)


def check(files, out):
    """One image with 4 frames from each clip (start, 1/3, 2/3, end), labelled with the file name, so Claude can look
    at it and keep only clips that really show what's being said."""
    from PIL import Image, ImageDraw
    from . import draw, ingest
    W, H = 180, 240
    sheet = Image.new("RGB", (4 * W + 260, max(1, len(files)) * H), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    f = draw.font("Inter_700Bold", 15)
    for i, rel in enumerate(files):
        src = config.absolute(rel)
        try:
            dur = ingest.duration(src)
        except Exception:  # noqa: BLE001
            dur = 0
        for j, k in enumerate((0.05, 0.35, 0.65, 0.95)):
            r = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", str(dur * k), "-i", str(src),
                                "-frames:v", "1", "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease",
                                "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, timeout=60)
            if r.stdout:
                import io
                im = Image.open(io.BytesIO(r.stdout)).convert("RGB")
                sheet.paste(im, (260 + j * W + (W - im.width) // 2, i * H + (H - im.height) // 2))
        name = src.name
        lines = [name[x:x + 26] for x in range(0, len(name), 26)][:5] + [f"{dur:.1f}s"]
        for k2, line in enumerate(lines):
            d.text((8, i * H + 10 + k2 * 20), line, font=f, fill=(255, 255, 255))
    sheet.save(out)
    return out
