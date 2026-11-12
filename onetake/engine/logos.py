"""Company logos for the `logo_row` look: say "NVIDIA, AMD and Intel" and each logo pops up on its word.

`find("NVIDIA")` looks the company up on Wikidata (its "logo image" property, P154), downloads the logo from
Wikimedia Commons as a PNG (SVG logos are rendered there at the size asked), trims the empty border and saves it
in library/logos/<slug>.png, so it's only fetched once. The user can drop their own logo files in the same folder
(a file named after the company wins). No key or account needed.
"""
import json
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


def cached(name):
    """The saved logo for this company (library/logos/<slug>.png/.jpg/.webp), or None. Never goes online."""
    for ext in (".png", ".webp", ".jpg", ".jpeg"):
        f = DIR / (slug(name) + ext)
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
    fname = _logo_file(name)
    if not fname:
        return None
    url = "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(fname.replace(" ", "_")) + f"?width={width}"
    data = _get(url)
    import io
    from PIL import Image
    im = _trim(Image.open(io.BytesIO(data)))
    DIR.mkdir(parents=True, exist_ok=True)
    out = DIR / (slug(name) + ".png")
    im.save(out)
    return out
