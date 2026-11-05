"""Turn the word list (with cut flags) into an edit: which pieces of the source
play, in what order, and where every word lands on the output timeline.

app/timeline.js mirrors this file so the browser preview matches the render
exactly. Change both together.
"""
import re

PUNCT_END = re.compile(r"[.,!?;:…]$")


def kept(words):
    return [i for i, w in enumerate(words) if not w.get("cut")]


def build_segments(words, duration, max_gap=0.35, pad_before=0.06, pad_after=0.12, order=None):
    """order: optional list of (w0, w1) word ranges to play in that order
    (used by trial reels to move a line to the front). Default: everything in order."""
    n = len(words)
    blocks = order or [(0, n - 1)]
    segs = []
    for b0, b1 in blocks:
        cur = None
        for i in range(b0, b1 + 1):
            w = words[i]
            if w.get("cut"):
                cur = None
                continue
            if cur and cur["w1"] == i - 1 and w["s"] - words[i - 1]["e"] <= max_gap:
                cur["w1"] = i
            else:
                cur = {"w0": i, "w1": i}
                segs.append(cur)
    out = []
    t = 0.0
    for sg in segs:
        w0, w1 = sg["w0"], sg["w1"]
        s = max(0.0, words[w0]["s"] - pad_before)
        e = min(duration, words[w1]["e"] + pad_after)
        if w0 > 0 and words[w0 - 1].get("cut"):
            s = min(max(s, words[w0 - 1]["e"]), words[w0]["s"])
        if w1 + 1 < n and words[w1 + 1].get("cut"):
            e = min(e, max(words[w1]["e"], words[w1 + 1]["s"]))
        if e - s < 0.05:
            e = s + 0.05
        out.append({"w0": w0, "w1": w1, "s": round(s, 3), "e": round(e, 3), "o": round(t, 3)})
        t += e - s
    return out


def total(segs):
    return round(sum(sg["e"] - sg["s"] for sg in segs), 3)


def seg_of_word(segs, i):
    for sg in segs:
        if sg["w0"] <= i <= sg["w1"]:
            return sg
    return None


def word_out(words, segs, i):
    """(start, end) of word i on the output timeline, or None if it was cut."""
    sg = seg_of_word(segs, i)
    if not sg:
        return None
    w = words[i]
    return (max(sg["o"], sg["o"] + w["s"] - sg["s"]), sg["o"] + min(w["e"], sg["e"]) - sg["s"])


def range_out(words, segs, w0, w1):
    """Output-time span covered by the kept words in [w0, w1]."""
    spans = [word_out(words, segs, i) for i in range(w0, w1 + 1)]
    spans = [s for s in spans if s]
    if not spans:
        return None
    return (min(s[0] for s in spans), max(s[1] for s in spans))


def out_to_src(segs, t):
    for sg in segs:
        if sg["o"] <= t < sg["o"] + (sg["e"] - sg["s"]):
            return sg, sg["s"] + (t - sg["o"])
    if segs:
        sg = segs[-1]
        return sg, sg["e"]
    return None, 0.0


def _new_sentence(prev, w):
    """A capitalised word after a short pause starts a new sentence, even when the transcript
    missed the full stop ("…pay it on" / "We need…"). Mirrored in app/timeline.js."""
    t = w["t"].strip().lstrip("\"'“(")
    if not t or not t[0].isupper() or t in ("I", "I'm", "I've", "I'll", "I'd") or t.isupper():
        return False
    return w["s"] - prev["e"] > 0.15


def caption_groups(words, segs, style):
    """Split the kept words into the chunks that appear on screen together."""
    max_words = 1 if style.get("mode") == "single" else int(style.get("max_words", 3))
    max_chars = int(style.get("max_chars", 18))
    groups = []
    cur = None
    prev = None
    for sg in segs:
        for i in range(sg["w0"], sg["w1"] + 1):
            w = words[i]
            st, en = word_out(words, segs, i)
            brk = (
                cur is None
                or len(cur["w"]) >= max_words
                or len(" ".join(words[j]["t"] for j in cur["w"]) + " " + w["t"]) > max_chars
                or (prev is not None and words[prev].get("l") != w.get("l"))
                or bool(w.get("cbreak"))
                or (prev is not None and _new_sentence(words[prev], w))
                or (prev is not None and PUNCT_END.search(words[prev]["t"].strip()))
                or (prev is not None and st - cur["end"] > 0.6)
            )
            if brk:
                cur = {"w": [], "start": st, "end": en}
                groups.append(cur)
            cur["w"].append(i)
            cur["end"] = en
            prev = i
    for a, b in zip(groups, groups[1:]):
        a["end"] = b["start"] if b["start"] - a["end"] < 0.5 else a["end"] + 0.25
    if groups:
        groups[-1]["end"] += 0.3
    return groups


def hook_span(project, segs):
    d = project.get("hook_duration", 3.0)
    return (0.0, min(d, total(segs)))


def overlay_span(project, words, segs, ov):
    if ov.get("role") == "hook":
        return hook_span(project, segs)
    sp = range_out(words, segs, ov["w0"], ov.get("w1", ov["w0"]))
    if not sp:
        return None
    s, e = sp
    if ov.get("min_dur") and e - s < ov["min_dur"]:
        e = s + ov["min_dur"]
    return (s, e)


CAM_ANCHOR = (0.5, 0.38)  # zoom toward the eyes (upper third) unless the project knows where the face is


def focus(p):
    return tuple(p.get("focus") or CAM_ANCHOR)


def camera_zoom(p, words, segs, t):
    """Digital zoom of the speaker at output time t. Mirrored in app/timeline.js.
    camera = {"push_in": seconds of slow push at the start (0 = off), "push_amount": 0.08,
              "punches": [word indexes where a thought changes], "punch_scale": 1.12}"""
    cam = p.get("camera") or {}
    starts = sorted(s for s in (word_out(words, segs, i) for i in cam.get("punches", [])) if s)
    starts = [s[0] for s in starts]
    passed = sum(1 for s in starts if s <= t)
    z = cam.get("punch_scale", 1.12) if passed % 2 else 1.0
    push = float(cam.get("push_in", 0) or 0)
    if push > 0 and (not starts or t < starts[0]):
        k = min(1.0, t / push)
        z *= 1.0 + cam.get("push_amount", 0.08) * (1 - (1 - k) ** 2)
    return z
