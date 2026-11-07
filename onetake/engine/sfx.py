"""Sound effects: every moment that moves gets a sound, timed to its motion.

- A built-in library of royalty-free effects is generated on this computer (no downloads, no keys)
  into assets/sfx/. Your own effects (downloaded, or from a sound subscription) go in library/sfx/.
- auto(p) gives each overlay, cut-away and punch-in a matching sound: a pop when a card snaps in,
  a whoosh on a slide or punch-in, typing under a typed headline, a riser + hit on a counter, etc.
- Each sound is {"id", "src", "anchor": {"ov": id} | {"broll": id} | {"w": word}, "offset", "volume",
  "muted", "auto", "line"} and is mixed into the render by render._audio().
"""
import json
import subprocess
import wave
from pathlib import Path

import numpy as np

from . import config, project, timeline

SR = 44100
BUILTIN = config.ASSETS / "sfx"


# ---------------------------------------------------------------- the built-in library

def _noise(n, seed=0):
    return np.random.default_rng(seed).standard_normal(n)


def _env(n, attack=0.005, release=None, curve=3.0):
    t = np.linspace(0, 1, n)
    a = np.minimum(1, t / max(1e-4, attack * SR / n))
    r = (1 - t) ** curve if release is None else np.exp(-t * release)
    return a * r


def _lowpass(x, k):
    k = max(1, int(k))
    return np.convolve(x, np.ones(k) / k, mode="same")


def _sweep_noise(dur, f0, f1, seed=0):
    """Band-limited noise whose brightness sweeps from f0 to f1 (a 'whoosh')."""
    n = int(SR * dur)
    x = _noise(n, seed)
    out = np.zeros(n)
    steps = 24
    for s in range(steps):
        a, b = s * n // steps, (s + 1) * n // steps
        f = f0 + (f1 - f0) * (s / (steps - 1))
        k = max(1, int(SR / max(60, f)))
        out[a:b] = _lowpass(x, k)[a:b]
    return out


def _tone(freq, dur, kind="sine"):
    t = np.arange(int(SR * dur)) / SR
    if callable(freq):
        ph = 2 * np.pi * np.cumsum(freq(t)) / SR
    else:
        ph = 2 * np.pi * freq * t
    return np.sin(ph) if kind == "sine" else np.sign(np.sin(ph)) * 0.5


def _norm(x, peak=0.9):
    m = np.abs(x).max() or 1
    return x / m * peak


def _make_all():
    n = lambda d: int(SR * d)
    lib = {}
    # whooshes
    for name, d, f0, f1, seed in (("whoosh-soft", 0.45, 300, 2500, 1), ("whoosh-fast", 0.28, 500, 4000, 2),
                                  ("whoosh-low", 0.6, 120, 900, 3)):
        x = _sweep_noise(d, f0, f1, seed)
        t = np.linspace(0, 1, len(x))
        lib[name] = _norm(x * np.sin(np.pi * t) ** 1.5, 0.7)
    # pops and clicks
    t = np.arange(n(0.09)) / SR
    lib["pop"] = _norm(np.sin(2 * np.pi * (900 - 5000 * t) * t) * np.exp(-t * 55), 0.8)
    t = np.arange(n(0.12)) / SR
    lib["pop-bubble"] = _norm(np.sin(2 * np.pi * (300 + 2500 * t) * t) * np.exp(-t * 35), 0.8)
    t = np.arange(n(0.03)) / SR
    lib["click"] = _norm(_noise(len(t), 4) * np.exp(-t * 300) + np.sin(2 * np.pi * 2200 * t) * np.exp(-t * 200), 0.6)
    # typing: a run of soft key clicks
    x = np.zeros(n(1.6))
    rng = np.random.default_rng(5)
    pos = 0.0
    while pos < 1.5:
        i = int(pos * SR)
        k = _noise(n(0.02), int(pos * 1000)) * np.exp(-np.arange(n(0.02)) / SR * 350) * rng.uniform(0.5, 1)
        x[i:i + len(k)] += k
        pos += rng.uniform(0.045, 0.09)
    lib["typing"] = _norm(_lowpass(x, 3), 0.5)
    # riser into a hit
    d = 1.2
    x = _sweep_noise(d, 200, 6000, 6) * np.linspace(0, 1, n(d)) ** 2
    x += 0.3 * _tone(lambda t: 200 + 500 * (t / d) ** 2, d) * np.linspace(0, 1, n(d)) ** 2
    lib["riser"] = _norm(x, 0.6)
    # hits / booms
    t = np.arange(n(0.7)) / SR
    boom = np.sin(2 * np.pi * (110 * np.exp(-t * 4) + 40) * t) * np.exp(-t * 6)
    lib["boom"] = _norm(boom + 0.2 * _lowpass(_noise(len(t), 7), 8) * np.exp(-t * 20), 0.9)
    t = np.arange(n(0.35)) / SR
    lib["hit"] = _norm(np.sin(2 * np.pi * (180 * np.exp(-t * 10) + 60) * t) * np.exp(-t * 12) +
                       0.5 * _noise(len(t), 8) * np.exp(-t * 40), 0.9)
    # money / success
    t = np.arange(n(0.6)) / SR
    bell = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * dcy) / (k + 1)
               for k, (f, dcy) in enumerate(((2093, 6), (2637, 7), (3136, 8))))
    lib["ding"] = _norm(bell, 0.6)
    x = np.zeros(n(0.75))
    c = _norm(_noise(n(0.05), 9) * np.exp(-np.arange(n(0.05)) / SR * 120), 0.5)
    x[:len(c)] += c
    x[n(0.08):n(0.08) + len(bell)] += bell[:len(x) - n(0.08)]
    lib["ka-ching"] = _norm(x, 0.7)
    # swipe (short bright whoosh) and pen scribble (for drawn arrows / ✗)
    x = _sweep_noise(0.18, 1500, 6000, 10)
    lib["swipe"] = _norm(x * np.sin(np.pi * np.linspace(0, 1, len(x))), 0.5)
    x = _lowpass(_noise(n(0.5), 11), 2) * (0.6 + 0.4 * np.sin(np.linspace(0, 40, n(0.5))))
    lib["scribble"] = _norm(x * np.sin(np.pi * np.linspace(0, 1, n(0.5))), 0.35)
    # notebook style (look D), measured from the reference reel: a ~30 ms bright paper tap when a card lands,
    # and a ~90 ms airy swish when the step tabs change
    t = np.arange(n(0.035)) / SR
    tap = _noise(len(t), 12) - _lowpass(_noise(len(t), 12), 6)  # keep the bright part, like a fingertip on paper
    lib["tap"] = _norm(tap * np.exp(-t * 140) + 0.25 * np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 220), 0.45)
    x = _sweep_noise(0.09, 3000, 8000, 13)
    lib["paper-swish"] = _norm(x * np.sin(np.pi * np.linspace(0, 1, len(x))) ** 0.7, 0.35)
    # error buzz (for "wrong") and a soft camera shutter (for frames)
    t = np.arange(n(0.3)) / SR
    lib["buzz"] = _norm(_tone(140, 0.3, "square") * np.exp(-t * 6), 0.5)
    return lib


META = {  # name: (label, tags)
    "whoosh-soft": ("Whoosh, soft", "transition whoosh slide"),
    "whoosh-fast": ("Whoosh, fast", "transition whoosh slide quick"),
    "whoosh-low": ("Whoosh, low", "transition whoosh punch zoom cinematic"),
    "pop": ("Pop", "pop ui sticker card"),
    "pop-bubble": ("Pop, bubble", "pop cute emoji"),
    "click": ("Click", "ui click button"),
    "typing": ("Typing", "typewriter keyboard text"),
    "riser": ("Riser", "build tension riser"),
    "boom": ("Boom", "impact hit boom drop"),
    "hit": ("Hit", "impact hit punch"),
    "ding": ("Ding", "success bell notification"),
    "ka-ching": ("Ka-ching", "money cash register"),
    "swipe": ("Swipe", "swipe ui fast"),
    "scribble": ("Pen scribble", "pen draw arrow handwriting"),
    "buzz": ("Wrong buzz", "error wrong buzzer"),
    "tap": ("Paper tap", "notebook card tap soft click"),
    "paper-swish": ("Paper swish", "notebook tab swish soft transition"),
}


def ensure_builtin():
    BUILTIN.mkdir(parents=True, exist_ok=True)
    missing = [k for k in META if not (BUILTIN / f"{k}.wav").exists()]
    if not missing:
        return []
    lib = _make_all()
    for k in missing:
        x = (np.clip(lib[k], -1, 1) * 32767).astype(np.int16)
        with wave.open(str(BUILTIN / f"{k}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(x.tobytes())
    return missing


_dur_cache = {}


def duration(path):
    path = Path(path)
    key = (str(path), path.stat().st_mtime)
    if key not in _dur_cache:
        try:
            if path.suffix.lower() == ".wav":
                with wave.open(str(path)) as w:
                    _dur_cache[key] = w.getnframes() / w.getframerate()
            else:
                out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                      str(path)], capture_output=True, text=True).stdout.strip()
                _dur_cache[key] = float(out or 0)
        except Exception:
            _dur_cache[key] = 0.0
    return round(_dur_cache[key], 2)


def library():
    """Every effect you can pick: your own (library/sfx) first, then the built-in ones."""
    ensure_builtin()
    out = []
    mine = config.LIBRARY / "sfx"
    if mine.exists():
        for f in sorted(mine.iterdir()):
            if f.suffix.lower() in config.AUDIO_EXT:
                out.append({"path": config.rel(f), "name": f.stem.replace("-", " ").replace("_", " "),
                            "tags": f.stem.lower(), "dur": duration(f), "source": "Yours"})
    for k, (label, tags) in META.items():
        f = BUILTIN / f"{k}.wav"
        out.append({"path": config.rel(f), "name": label, "tags": tags, "dur": duration(f), "source": "Built-in"})
    return out


# ---------------------------------------------------------------- matching sounds to motion

def b(name):
    return f"assets/sfx/{name}.wav"


NOTEBOOK_CARDS = ("notebook_note", "week_check", "sticky_row", "x_card", "option_tiles", "growth_chart", "comment_cta",
                  "notebook_counter")


def for_overlay(ov):
    """[(sound, offset_s, volume)] for one overlay, chosen from its look and how it moves."""
    look, kind, ai = ov.get("look"), ov.get("kind"), ov.get("anim_in", "pop")
    if look in NOTEBOOK_CARDS:  # notebook style: sparse and soft, one tap as the card lands (no typing sounds)
        return [(b("tap"), 0.0, 0.4)]
    if look == "step_tabs":
        return [(b("paper-swish"), -0.03, 0.35)]
    if look == "follow_card":
        ca = (ov.get("params") or {}).get("click_at", 0.8)
        return [] if isinstance(ca, dict) else [(b("click"), float(ca), 0.45)]  # a word cue: see auto()
    if look == "serif_hook":
        return []
    if look in ("count_up", "big_number"):
        return [(b("riser"), -0.6, 0.35), (b("ka-ching" if (ov.get("params") or {}).get("prefix") == "$" else "boom"), 1.2, 0.55)]
    if look in ("typed_title", "hand_note", "keyword_def", "chapter_header"):
        return [(b("typing"), 0.0, 0.25)]
    if look == "checklist":
        return [(b("scribble"), 0.0, 0.3)]
    if look in ("red_x",):
        return [(b("scribble"), 0.0, 0.35), (b("buzz"), 0.2, 0.3)]
    if look == "cta_keyword":
        return [(b("ding"), 0.0, 0.5)]
    if look == "arrow":
        return [(b("scribble"), 0.0, 0.3)]
    if look in ("equation", "highlight_card", "name_badge", "lower_third"):
        return [(b("swipe" if ai.startswith("slide") else "pop"), 0.0, 0.45)]
    if look == "emoji_burst" or kind == "emoji" or look == "emoji_row":
        return [(b("pop-bubble"), 0.0, 0.45)]
    if ai and ai.startswith("slide"):
        return [(b("whoosh-fast"), -0.1, 0.4)]
    if ai == "spin":
        return [(b("whoosh-soft"), 0.0, 0.4)]
    return [(b("pop"), 0.0, 0.45)]


def auto(p, replace=True):
    """Give every moving thing a sound. Keeps sounds you added or edited yourself."""
    ensure_builtin()
    keep = [s for s in p.get("sfx", []) if not s.get("auto") or not replace]
    taken = {json.dumps(s.get("anchor"), sort_keys=True) for s in keep}
    out = list(keep)

    def add(anchor, src, off, vol):
        if json.dumps(anchor, sort_keys=True) in taken:
            return
        out.append({"id": project.new_id("s") + str(len(out)), "src": src, "anchor": anchor, "offset": off,
                    "volume": vol, "muted": False, "auto": True})

    for ov in p.get("overlays", []):
        if ov.get("role") == "hook" and ov.get("look") == "typed_title":
            add({"ov": ov["id"]}, b("typing"), 0.0, 0.22)
            continue
        for k, (src, off, vol) in enumerate(for_overlay(ov)):
            add({"ov": ov["id"], "k": k} if k else {"ov": ov["id"]}, src, off, vol)
        ca = (ov.get("params") or {}).get("click_at") if ov.get("look") == "follow_card" else None
        if isinstance(ca, dict) and isinstance(ca.get("w"), int):  # the click lands on its word
            add({"w": ca["w"]}, b("click"), float(ca.get("dt", 0) or 0), 0.45)
    for br in p.get("broll", []):
        add({"broll": br["id"]}, b("whoosh-soft"), -0.15, 0.35)
    for w in (p.get("camera") or {}).get("punches", []):
        add({"w": w}, b("whoosh-low"), -0.1, 0.25)
    p["sfx"] = out
    p.setdefault("sfx_on", True)
    return out


def times(p, segs):
    """Output time of every sound: [(sfx, t)]. Sounds whose thing was removed are skipped."""
    words = p["words"]
    ovs = {o["id"]: o for o in p.get("overlays", [])}
    brs = {x["id"]: x for x in p.get("broll", [])}
    out = []
    for s in p.get("sfx", []):
        a = s.get("anchor") or {}
        t = None
        if "ov" in a and a["ov"] in ovs:
            sp = timeline.overlay_span(p, words, segs, ovs[a["ov"]])
            t = sp[0] if sp else None
        elif "broll" in a and a["broll"] in brs:
            sp = timeline.range_out(words, segs, brs[a["broll"]]["w0"], brs[a["broll"]]["w1"])
            t = sp[0] if sp else None
        elif "w" in a and 0 <= a["w"] < len(words):
            wo = timeline.word_out(words, segs, a["w"])
            t = wo[0] if wo else None
        if t is not None:
            out.append((s, max(0.0, t + float(s.get("offset", 0)))))
    return out


def line_of(p, s):
    """Which word a sound belongs to (for listing it under its line)."""
    a = s.get("anchor") or {}
    if "ov" in a:
        o = next((o for o in p.get("overlays", []) if o["id"] == a["ov"]), None)
        return 0 if o and o.get("role") == "hook" else (o["w0"] if o else None)
    if "broll" in a:
        x = next((x for x in p.get("broll", []) if x["id"] == a["broll"]), None)
        return x["w0"] if x else None
    return a.get("w")
