"""Company logos for the `logo_row` look: say "NVIDIA, AMD and Intel" and each logo pops up on its word.

`find("NVIDIA")` looks the company up on Wikidata (its "logo image" property, P154), downloads the logo from
Wikimedia Commons as a PNG (SVG logos are rendered there at the size asked), trims the empty border and saves it
in library/logos/<slug>.png, so it's only fetched once. The user can drop their own logo files in the same folder
(a file named after the company wins). No key or account needed.
"""
import json
from pathlib import Path
import re
import urllib.parse
import urllib.error
import urllib.request

from . import config

DIR = config.ROOT / "library" / "logos"
UA = {"User-Agent": "OneTakeStudio/1.0 (reels editor; logo lookup)"}
# names people say that Wikidata's search doesn't put first
ALIASES = {"amd": "Advanced Micro Devices", "meta": "Meta Platforms", "google": "Google", "alphabet": "Alphabet Inc.",
           "tsmc": "TSMC", "jpm": "JPMorgan Chase", "jp morgan": "JPMorgan Chase", "palantir": "Palantir Technologies",
           "broadcom": "Broadcom Inc.", "oracle": "Oracle Corporation", "intel": "Intel", "apple": "Apple Inc.",
           "amazon": "Amazon (company)", "microsoft": "Microsoft", "tesla": "Tesla, Inc.", "netflix": "Netflix",
           "uber": "Uber", "vertiv": "Vertiv", "nvidia": "Nvidia", "coca cola": "The Coca-Cola Company",
           "costco": "Costco", "walmart": "Walmart", "berkshire": "Berkshire Hathaway", "visa": "Visa Inc.",
           "mastercard": "Mastercard", "shopify": "Shopify", "spotify": "Spotify", "disney": "The Walt Disney Company",
           "nike": "Nike, Inc.", "starbucks": "Starbucks", "mcdonalds": "McDonald's", "mcdonald's": "McDonald's"}
COMPANY_TYPES = {"Q4830453", "Q891723", "Q6881511", "Q783794", "Q43229", "Q167037", "Q1058914"}  # business, public co…


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "logo"


INDEX = DIR / "index.json"  # from `logo-pack`: {"tickers": {"NVDA": "nvidia"}, "names": {"nvidia": "nvidia"}}
_index = None


def _idx():
    global _index
    if _index is None:
        try:
            _index = json.loads(INDEX.read_text())
        except (OSError, ValueError):
            _index = {"tickers": {}, "names": {}}
    return _index


def key_for(name):
    """The file stem for a company, said as a name or a ticker ("Nvidia", "NVIDIA", "NVDA", "$NVDA")."""
    n = name.strip().lstrip("$")
    ix = _idx()
    return ix["tickers"].get(n.upper()) or ix["names"].get(slug(n)) or ix["names"].get(slug(ALIASES.get(n.lower(), n))) or slug(n)


def cached(name):
    """The saved logo for this company (library/logos/<slug>.png/.jpg/.webp), or None. Never goes online."""
    for stem in dict.fromkeys([slug(name), key_for(name)]):
        for ext in (".png", ".webp", ".jpg", ".jpeg"):
            f = DIR / (stem + ext)
            if f.is_file():
                return f
    return None


def _get(url, tries=4):
    import time
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 or k == tries - 1:  # Wikimedia asks us to slow down: wait and try again
                raise
            time.sleep(3 * (k + 1))


def _api(**q):
    q.update(format="json")
    return json.loads(_get("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(q)))


def _logo_file(name):
    """Wikimedia Commons file name of the company's logo, via Wikidata."""
    query = ALIASES.get(name.lower().strip(), name)
    hits = _api(action="wbsearchentities", search=query, language="en", type="item", limit=8).get("search", [])
    if not hits:
        return None
    ents = _api(action="wbgetentities", ids="|".join(h["id"] for h in hits), props="claims").get("entities", {})
    best = None
    for h in hits:  # in search order: prefer a company with a logo, else anything with a logo
        cl = ents.get(h["id"], {}).get("claims", {})
        logo = _current_logo(cl.get("P154", []))
        if not logo:
            continue
        kinds = {c["mainsnak"].get("datavalue", {}).get("value", {}).get("id") for c in cl.get("P31", [])}
        if kinds & COMPANY_TYPES or "P414" in cl or "P249" in cl:  # a company / listed on an exchange / has a ticker
            return logo
        best = best or logo
    return best


def _current_logo(claims):
    """Today's logo: the one marked preferred, else one without an end date (old logos stay listed with one)."""
    ok = [c for c in claims if c["mainsnak"].get("datavalue") and c.get("rank") != "deprecated"]
    if not ok:
        return None
    pick = ([c for c in ok if c.get("rank") == "preferred"]
            or [c for c in ok if "P582" not in (c.get("qualifiers") or {})] or ok)
    def start(c):
        q = (c.get("qualifiers") or {}).get("P580") or [{}]
        return (q[0].get("datavalue") or {}).get("value", {}).get("time", "")
    return sorted(pick, key=start)[-1]["mainsnak"]["datavalue"]["value"]  # newest start date last


def _trim(im):
    """Cut the empty (transparent or white) border around a logo."""
    from PIL import Image, ImageChops
    im = im.convert("RGBA")
    box = im.getchannel("A").getbbox()
    if box and box != (0, 0, im.width, im.height):
        return im.crop(box)
    bg = Image.new("RGB", im.size, (255, 255, 255))
    diff = ImageChops.difference(im.convert("RGB"), bg).convert("L").point(lambda v: 255 if v > 18 else 0)
    box = diff.getbbox()
    return im.crop(box) if box else im


def find(name, width=640):
    """Path to this company's logo (downloaded once), or None if Wikidata has none."""
    hit = cached(name)
    if hit:
        return hit
    builtin_index()
    key = key_for(name)
    fname = _idx().get("files", {}).get(key) or _logo_file(name)  # known company: straight to its logo
    if not fname:
        return None
    url = "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(fname.replace(" ", "_")) + f"?width={width}"
    data = _get(url)
    import io
    from PIL import Image
    im = _trim(Image.open(io.BytesIO(data)))
    DIR.mkdir(parents=True, exist_ok=True)
    out = DIR / ((key if key in _idx().get("files", {}) else slug(name)) + ".png")
    im.save(out)
    return out


SPARQL = """SELECT ?item ?itemLabel ?ticker ?logo ?links WHERE {
  VALUES ?ex { wd:Q13677 wd:Q82059 wd:Q1150384 }
  ?item p:P414 ?st . ?st ps:P414 ?ex . ?st pq:P249 ?ticker .
  ?item p:P154 ?ls . ?ls ps:P154 ?logo . ?ls wikibase:rank ?rk . FILTER(?rk != wikibase:DeprecatedRank)
  FILTER NOT EXISTS { ?ls pq:P582 ?ended }
  FILTER NOT EXISTS { ?item wdt:P576 ?dissolved }
  ?item wikibase:sitelinks ?links .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
} ORDER BY DESC(?links)"""


def pack_list():
    """Every NYSE / NASDAQ / NYSE American company on Wikidata with a current logo, most-known first:
    [{"key", "name", "tickers", "file"}]. One request."""
    q = urllib.parse.urlencode({"query": SPARQL})
    req = urllib.request.Request("https://query.wikidata.org/sparql?" + q,
                                 headers=dict(UA, Accept="application/sparql-results+json"))
    with urllib.request.urlopen(req, timeout=180) as r:
        rows = json.loads(r.read())["results"]["bindings"]
    rows = [b for b in rows if not re.fullmatch(r"Q\d+", b["itemLabel"]["value"])]  # no English name: skip
    out, by = [], {}
    for b in rows:
        item, name = b["item"]["value"], b["itemLabel"]["value"]
        file = urllib.parse.unquote(b["logo"]["value"].rsplit("/", 1)[-1])
        if item not in by:
            by[item] = {"key": slug(name), "name": name, "tickers": [], "file": file}
            out.append(by[item])
        t = b["ticker"]["value"].strip().upper()
        if t and t not in by[item]["tickers"]:
            by[item]["tickers"].append(t)
    return out


SUFFIX = re.compile(r"[,\s]+(inc|incorporated|corp|corporation|co|company|plc|ltd|limited|group|holdings?|"
                    r"technologies|technology|n\.?v|s\.?a|ag|se|sa|lp|llc)\.?$", re.I)


def _name_variants(name):
    """'The Walt Disney Company' -> walt-disney-company, walt-disney, the-walt-disney… (how people say it)."""
    out, n = [], name.strip()
    for _ in range(3):
        out.append(slug(n))
        if n.lower().startswith("the "):
            out.append(slug(n[4:]))
        m = SUFFIX.sub("", n)
        if m == n:
            break
        n = m
    out.append(slug(re.sub(r"^the\s+", "", n, flags=re.I)))
    return [x for x in dict.fromkeys(out) if x]


def _index_all(items):
    """Remember every company's tickers, names and logo file, so `find("NVDA")` works before its logo is downloaded."""
    ix = _idx()
    ix.setdefault("files", {})
    for it in items:
        for t in it["tickers"]:
            ix["tickers"].setdefault(t, it["key"])
        for v in _name_variants(it["name"]):
            ix["names"].setdefault(v, it["key"])
        ix["files"].setdefault(it["key"], it["file"])
    DIR.mkdir(parents=True, exist_ok=True)
    INDEX.write_text(json.dumps(ix))


def builtin_index():
    """Load the company list shipped with One Take into the index (no network), once."""
    if _idx().get("files"):
        return
    try:
        items = [dict(x, key=slug(x["name"])) for x in json.loads((config.ROOT / "assets" / "logo_list.json").read_text())]
    except (OSError, ValueError):
        return
    _index_all(items)


def pack(top=None, progress=print, pause=1.0):
    """Download the logo of every listed company (or the `top` best-known) into library/logos, politely (one at a
    time), skipping ones already there. Safe to stop and run again. Writes index.json so tickers work too."""
    import io
    import time
    from PIL import Image
    try:
        items = pack_list()  # the live list (newest logos)
    except Exception as e:  # noqa: BLE001  (the query service is busy/limited): use the list shipped with One Take
        progress(f"  (Wikidata's list is busy right now: {e}. Using the built-in list of companies.)")
        items = [dict(x, key=slug(x["name"])) for x in json.loads((config.ROOT / "assets" / "logo_list.json").read_text())]
    if top:
        items = items[:int(top)]
    DIR.mkdir(parents=True, exist_ok=True)
    _index_all(items)
    ix = _idx()
    got = skipped = failed = 0
    for i, it in enumerate(items, 1):
        out = DIR / (it["key"] + ".png")
        if out.exists():
            skipped += 1
            continue
        url = ("https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(it["file"].replace(" ", "_"))
               + "?width=480")
        try:
            _trim(Image.open(io.BytesIO(_get(url, tries=6)))).save(out, optimize=True)
            got += 1
        except Exception as e:  # noqa: BLE001
            failed += 1
            progress(f"  couldn't get {it['name']}: {e}")
        if i % 25 == 0:
            INDEX.write_text(json.dumps(ix))
            progress(f"  {i}/{len(items)} done ({got} new, {skipped} already here, {failed} missing)")
        time.sleep(pause)
    INDEX.write_text(json.dumps(ix))
    progress(f"Logo pack: {got} new, {skipped} already here, {failed} missing, {len(items)} companies.")
    return got


# ---------- icon marks by ticker (github.com/davidepalazzo/ticker-logos) ----------
ICONS = DIR / "icons"
ICON_REPO = "https://github.com/davidepalazzo/ticker-logos.git"
ICON_RAW = "https://raw.githubusercontent.com/davidepalazzo/ticker-logos/main/ticker_icons/{}.png"


def ticker_of(name):
    """'NVDA' / '$NVDA' -> 'NVDA'; 'Nvidia' -> its ticker from the index (None if unknown)."""
    n = name.strip().lstrip("$")
    if re.fullmatch(r"[A-Z][A-Z.\-]{0,5}", n):
        return n.replace(".", "-")
    builtin_index()
    key = key_for(n)
    for t, k in _idx()["tickers"].items():
        if k == key:
            return t
    return None


def icon(name, online=True):
    """The company's icon mark (library/logos/icons/<TICKER>.png), downloaded on first use; None if there's none."""
    t = ticker_of(name)
    if not t:
        return None
    f = ICONS / f"{t}.png"
    if f.is_file():
        return f
    if not online:
        return None
    try:
        data = _get(ICON_RAW.format(urllib.parse.quote(t)), tries=2)
    except Exception:  # noqa: BLE001  (not in the repo)
        return None
    ICONS.mkdir(parents=True, exist_ok=True)
    f.write_bytes(data)
    return f


def best(name, kind="logo", online=False):
    """What the logo_row look shows: the name logo (wordmark) or the icon mark, falling back to the other one."""
    order = (icon, cached) if kind == "icon" else (cached, icon)
    for fn in order:
        f = fn(name, online=online) if fn is icon else fn(name)
        if f:
            return f
    return None


def import_icons(progress=print):
    """All ~5,100 ticker icons at once (about 105 MB): a sparse git checkout of just the ticker_icons folder."""
    import shutil
    import subprocess
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="ticker-logos-"))
    try:
        run = lambda *a: subprocess.run(["git", *a], cwd=tmp, check=True, capture_output=True, text=True)
        run("init", "-q")
        run("remote", "add", "origin", ICON_REPO)
        run("config", "core.sparseCheckout", "true")
        (tmp / ".git" / "info" / "sparse-checkout").write_text("ticker_icons/\n")
        progress("  downloading the ticker icons (about 105 MB)…")
        run("pull", "-q", "--depth", "1", "origin", "main")
        ICONS.mkdir(parents=True, exist_ok=True)
        n = 0
        for f in (tmp / "ticker_icons").glob("*.png"):
            dest = ICONS / f.name.upper().replace(".PNG", ".png")
            if not dest.exists():
                shutil.copy2(f, dest)
                n += 1
        progress(f"Added {n} ticker icons to {ICONS}.")
        return n
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
