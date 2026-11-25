"""Free stock B-roll from Pixabay (pixabay.com/api/docs): search, pick a good-size file, download
into library/broll/. Pixabay clips are free to use in your videos (Pixabay Content License);
credits are kept in library/broll/credits.json anyway.

The API key is free. It's stored only on this computer, in settings.json ("pixabay_key"),
or in the PIXABAY_API_KEY environment variable."""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from . import config

API = "https://pixabay.com/api/videos/"

# A starter pack for money / debt / investing content: (search, how many clips)
STARTER = [
    ("counting money", 2), ("credit card", 2), ("stock market", 2), ("wall street", 1),
    ("paying bills", 2), ("calculator", 2), ("stress bills", 1), ("piggy bank", 1),
    ("dollar bills", 2), ("coins", 1), ("stock ticker", 1), ("trading phone", 2),
    ("shopping bags", 1), ("bank", 1), ("savings", 1), ("house keys", 1),
    ("laptop finance", 2), ("budget", 1), ("happy couple home", 1), ("casino slot machine", 1),
    ("city skyline night", 1), ("office work laptop", 1),
]


class NoKey(Exception):
    pass


def key():
    k = os.environ.get("PIXABAY_API_KEY") or config.settings().get("pixabay_key")
    if not k:
        raise NoKey("Add your free Pixabay API key first (studio: Add media → Videos → Find B-roll).")
    return k.strip()


def has_key():
    return bool(os.environ.get("PIXABAY_API_KEY") or config.settings().get("pixabay_key"))


def save_key(k):
    f = config.ROOT / "settings.json"
    s = json.loads(f.read_text()) if f.exists() else {}
    s["pixabay_key"] = k.strip()
    f.write_text(json.dumps(s, indent=1))


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "OneTakeStudio/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code in (400, 401, 403):
            raise RuntimeError("Pixabay didn't accept the API key. Copy the whole key from pixabay.com/api/docs "
                               "(the green one next to 'key') and save it again.")
        if e.code == 429:
            raise RuntimeError("Pixabay says too many searches right now. Wait a minute and try again.")
        raise


def best_file(hit):
    """Prefer a vertical clip; otherwise the smallest rendition that's still at least 720 px tall
    (split screens only need the top half, and full-screen clips get cropped to 9:16)."""
    vids = [v for v in (hit.get("videos") or {}).values() if v and v.get("url")]
    if not vids:
        return None

    def score(v):
        h, w = v.get("height") or 0, v.get("width") or 0
        return (0 if h >= 720 else 1, abs(h - (1920 if h > w else 1080)))
    return sorted(vids, key=score)[0]


def is_vertical(hit):
    v = best_file(hit) or {}
    return (v.get("height") or 0) > (v.get("width") or 0)


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "clip"


def credits_file():
    return config.LIBRARY / "broll" / "credits.json"


def search(query, n=5, max_secs=30, fetch=_get):
    """Find up to n clips for `query` (vertical ones first) and download them. Returns their library paths."""
    url = API + "?" + urllib.parse.urlencode({"key": key(), "q": query, "video_type": "film", "safesearch": "true",
                                               "per_page": max(3, min(50, n * 4))})
    hits = [h for h in fetch(url).get("hits", []) if (h.get("duration") or 0) <= max_secs]
    hits.sort(key=lambda h: 0 if is_vertical(h) else 1)
    out_dir = config.LIBRARY / "broll"
    out_dir.mkdir(parents=True, exist_ok=True)
    cf = credits_file()
    credits = json.loads(cf.read_text()) if cf.exists() else {}
    got = []
    for h in hits:
        if len(got) >= n:
            break
        f = best_file(h)
        if not f:
            continue
        # neutral name: the search words are NOT what's in the clip (Pixabay results are often off-topic), so a
        # filename must never pass for a description. What it really shows goes in library/broll/index.json.
        dest = out_dir / f"pixabay-{h['id']}.mp4"
        if not dest.exists():
            req = urllib.request.Request(f["url"], headers={"User-Agent": "OneTakeStudio/1.0"})
            tmp = dest.with_suffix(".part")
            with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as fh:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    fh.write(chunk)
            tmp.rename(dest)
        credits[dest.name] = {"by": h.get("user"), "url": h.get("pageURL"), "source": "Pixabay", "search": query}
        got.append(config.rel(dest))
    cf.write_text(json.dumps(credits, indent=1))
    index_unchecked([config.absolute(g).name for g in got], query)
    return got


def index_file():
    return config.LIBRARY / "broll" / "index.json"


def load_index():
    f = index_file()
    return json.loads(f.read_text()) if f.exists() else {}


def index_unchecked(names, query):
    """New clips go in the index as NOT CHECKED until someone has looked at them (broll-check) and written what they
    really show with `broll-describe`."""
    idx = load_index()
    for n in names:
        idx.setdefault(n, {"shows": None, "searched_for": query, "checked": False})
    index_file().write_text(json.dumps(idx, indent=1))


def describe(name, shows, use_for=(), not_for=(), avoid=False):
    if name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):  # photos have their own index (library/images)
        f = config.LIBRARY / "images" / "index.json"
        idx = json.loads(f.read_text()) if f.exists() else {}
        e = idx.setdefault(name, {})
        e.update({"shows": shows, "use_for": list(use_for), "not_for": list(not_for), "checked": True})
        if avoid:
            e["avoid"] = True
        else:
            e.pop("avoid", None)
        f.write_text(json.dumps(idx, indent=1))
        return
    idx = load_index()
    e = idx.setdefault(name, {})
    e.update({"shows": shows, "use_for": list(use_for), "not_for": list(not_for), "checked": True})
    if avoid:
        e["avoid"] = True
    else:
        e.pop("avoid", None)
    index_file().write_text(json.dumps(idx, indent=1))


def find_in_index(words):
    """Clips whose real description / uses match the words (checked, not 'avoid'), best first."""
    ws = [w for w in re.split(r"\W+", words.lower()) if len(w) > 2]
    out = []
    imgs = config.LIBRARY / "images" / "index.json"  # real photos (commons-find) count too
    items = [(n, e, "broll") for n, e in load_index().items()]
    if imgs.exists():
        items += [(n, e, "images") for n, e in json.loads(imgs.read_text()).items()]
    try:  # the cloud library in Google Drive (pull before use)
        from . import cloudlib
        local = {n for n, e, _ in items if isinstance(e, dict) and not e.get("in_cloud")}
        items += [(n, e, "cloud") for n, e in cloudlib.load().items() if n not in local]
    except Exception:  # noqa: BLE001
        pass
    for name, e, folder in items:
        if name.startswith("_") or not isinstance(e, dict) or e.get("avoid") or not e.get("shows") or e.get("in_cloud"):
            continue
        text = " ".join([e.get("shows", "")] + list(e.get("use_for", []))).lower()
        bad = " ".join(e.get("not_for", [])).lower()
        score = sum(w in text for w in ws) - 2 * sum(w in bad for w in ws) - (0.5 if e.get("weak") else 0)
        if score > 0:
            out.append((score, f"{folder}/{name}", e))
    return sorted(out, key=lambda x: -x[0])


IMG_API = "https://pixabay.com/api/"


def image_search(query, n=3, kind="all", fetch=_get):
    """Images for stickers, memes-style cut-outs and illustrations (Pixabay, free to use) into library/images/.
    kind: all | photo | illustration | vector (vectors usually come as PNGs with a transparent background)."""
    url = IMG_API + "?" + urllib.parse.urlencode({"key": key(), "q": query, "image_type": kind, "safesearch": "true",
                                                   "per_page": max(3, min(50, n * 3))})
    hits = fetch(url).get("hits", [])
    out_dir = config.LIBRARY / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    cf = config.LIBRARY / "images" / "credits.json"
    credits = json.loads(cf.read_text()) if cf.exists() else {}
    got = []
    for h in hits[:n]:
        src = h.get("largeImageURL") or h.get("webformatURL")
        if not src:
            continue
        ext = ".png" if src.lower().endswith(".png") else ".jpg"
        dest = out_dir / f"{slug(query)}-{h['id']}{ext}"
        if not dest.exists():
            req = urllib.request.Request(src, headers={"User-Agent": "OneTakeStudio/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                dest.write_bytes(r.read())
        credits[dest.name] = {"by": h.get("user"), "url": h.get("pageURL"), "source": "Pixabay", "search": query}
        got.append(config.rel(dest))
    cf.write_text(json.dumps(credits, indent=1))
    return got


def starter_pack(progress=None, fetch=_get):
    got = []
    for k, (q, n) in enumerate(STARTER):
        try:
            got += search(q, n, fetch=fetch)
        except NoKey:
            raise
        except RuntimeError as e:  # bad key / rate limit: stop and say why
            if not got:
                raise
            print(f"  stopped early: {e}")
            break
        except Exception as e:  # one bad search shouldn't stop the pack
            print(f"  skipped '{q}': {e}")
        if progress:
            progress((k + 1) / len(STARTER))
    return got
