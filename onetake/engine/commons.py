"""Real photos and videos from Wikimedia Commons (no key needed): the NYSE, the Fed, company headquarters and
factories, CEOs and other public figures — things stock sites don't have.

Only files whose licence allows use in a monetised reel are kept: public domain, CC0, CC BY and CC BY-SA
(never NC "non-commercial" or ND "no derivatives"). CC BY / BY-SA need a credit line: it's saved in the folder's
credits.json and `python3 -m engine credits NAME` prints every credit a reel needs, ready to paste into the caption.
"""
import html
import json
import re
import subprocess
import time
import urllib.parse
import urllib.request

from . import config

API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "OneTakeStudio/1.0 (personal video editing tool)"}
OK_LICENCES = ("public domain", "pd", "cc0", "cc by", "cc-by")
BAD = ("nc", "nd", "non-commercial", "noncommercial", "no derivatives", "fair use")


def _get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read()


def _clean(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def _licence_ok(short):
    s = (short or "").lower()
    if not s or any(re.search(rf"\b{re.escape(b)}\b", s) for b in BAD):
        return False
    return any(s.startswith(ok) or ok in s for ok in OK_LICENCES)


def _needs_credit(short):
    s = (short or "").lower()
    return not (s.startswith("public domain") or s.startswith("pd") or "cc0" in s)


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "commons"


def search(query, n=3, kind="photo", fetch=_get):
    """Download up to n matching files. kind: "photo" (into library/images) or "video" (into library/broll, as mp4)."""
    ft = "filetype:video" if kind == "video" else "filetype:bitmap"
    params = {"action": "query", "format": "json", "generator": "search", "gsrsearch": f"{query} {ft}",
              "gsrnamespace": "6", "gsrlimit": "30", "prop": "imageinfo",
              "iiprop": "url|extmetadata|size|mime", "iiurlwidth": "1600"}
    if kind == "video":  # videos: Commons blocks bulk downloads of the originals, so use its ready-made smaller copies
        params.update({"prop": "videoinfo", "viprop": "url|extmetadata|size|mime|derivatives"})
        for k in ("iiprop", "iiurlwidth"):
            params.pop(k)
    data = json.loads(fetch(API + "?" + urllib.parse.urlencode(params)))
    pages = sorted((data.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    folder = config.LIBRARY / ("broll" if kind == "video" else "images")
    folder.mkdir(parents=True, exist_ok=True)
    cf = folder / "credits.json"
    credits = json.loads(cf.read_text()) if cf.exists() else {}
    got = []
    for pg in pages:
        if len(got) >= n:
            break
        ii = (pg.get("imageinfo") or pg.get("videoinfo") or [{}])[0]
        meta = ii.get("extmetadata") or {}
        lic = _clean((meta.get("LicenseShortName") or {}).get("value"))
        if not _licence_ok(lic):
            continue
        mime = ii.get("mime", "")
        if kind == "photo" and not mime.startswith("image/"):
            continue
        if kind == "video" and not (mime.startswith("video/") or mime == "application/ogg"):
            continue
        if kind == "photo" and min(ii.get("width", 0), ii.get("height", 0)) < 600:
            continue  # too small to look sharp in a reel
        artist = _clean((meta.get("Artist") or {}).get("value")) or "Unknown"
        page = ii.get("descriptionurl") or f"https://commons.wikimedia.org/?curid={pg.get('pageid')}"
        base = f"commons-{_slug(query)}-{pg.get('pageid')}"
        try:
            if kind == "video":
                dest = folder / f"{base}.mp4"
                raw = folder / f".{base}.download"
                ders = [d for d in ii.get("derivatives", []) if "webm" in d.get("type", "") or "mp4" in d.get("type", "")]
                if not ders:
                    continue
                best = max(ders, key=lambda d: int(d.get("height") or 0))
                if int(best.get("height") or 0) < 360:
                    continue  # too blurry for a reel
                time.sleep(1)  # be gentle with Wikimedia's servers
                raw.write_bytes(fetch(best["src"]))
                r = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", str(raw), "-t", "20", "-an",
                                    "-vf", "scale='min(1920,iw)':-2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dest)], capture_output=True)
                raw.unlink(missing_ok=True)
                if r.returncode != 0:
                    dest.unlink(missing_ok=True)
                    continue
            else:
                src = ii.get("thumburl") or ii["url"]
                ext = ".png" if src.lower().endswith(".png") else ".jpg"
                dest = folder / f"{base}{ext}"
                dest.write_bytes(fetch(src))
        except Exception:  # noqa: BLE001 — one broken file shouldn't stop the search
            continue
        credits[dest.name] = {"by": artist, "url": page, "source": "Wikimedia Commons", "license": lic,
                              "credit_needed": _needs_credit(lic), "search": query,
                              "credit": f"{'Video' if kind == 'video' else 'Photo'}: {artist} / {lic} (Wikimedia Commons)"}
        got.append(f"{config.rel(dest)}  ({lic}{', credit needed' if _needs_credit(lic) else ''})")
    cf.write_text(json.dumps(credits, indent=1))
    return got


def reel_credits(p):
    """Credit lines for every library file a reel uses that needs one (CC BY / BY-SA from Commons)."""
    used = {b.get("src") for b in p.get("broll", []) if b.get("src")}
    used |= {o.get("src") for o in p.get("overlays", []) if o.get("src")}
    lines = []
    for rel in sorted(u for u in used if u):
        path = config.absolute(rel)
        cf = path.parent / "credits.json"
        if not cf.exists():
            continue
        c = json.loads(cf.read_text()).get(path.name)
        if c and c.get("credit_needed"):
            lines.append(c["credit"])
    return lines
