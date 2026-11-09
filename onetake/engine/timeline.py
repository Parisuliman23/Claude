"""Turn the word list (with cut flags) into an edit: which pieces of the source
play, in what order, and where every word lands on the output timeline.

app/timeline.js mirrors this file so the browser preview matches the render
exactly. Change both together.
"""
import re

PUNCT_END = re.compile(r"[.,!?;:…]$")


def kept(words):
    return [i for i, w in enumerate(words) if not w.get("cut")]


def _reassign(piece, words, w0, w1):
    """The words of a clip after it was trimmed: those whose middle is still inside it."""
    ins = [i for i in range(w0, w1 + 1) if piece[0] <= (words[i]["s"] + words[i]["e"]) / 2 < piece[1]]
    return (ins[0], ins[-1]) if ins else None


def _apply_keeps(segs, keeps):
    """Footage you dragged a clip's edge out over (e.g. a pause One Take had trimmed): the clip grows to cover it."""
    segs = [dict(s) for s in segs]
    for a, b in sorted((float(a), float(b)) for a, b in keeps if float(b) > float(a)):
        a = max(0.0, a)
        hit = [s for s in segs if s["s"] <= b + 0.05 and s["e"] >= a - 0.05]
        if not hit:
            continue
        m = {"w0": min(s["w0"] for s in hit), "w1": max(s["w1"] for s in hit),
             "s": round(min([a] + [s["s"] for s in hit]), 3), "e": round(max([b] + [s["e"] for s in hit]), 3)}
        segs = sorted([s for s in segs if s not in hit] + [m], key=lambda s: s["s"])
    return segs


def apply_time_edits(segs, words, cuts=None, splits=None, keeps=None):
    """CapCut-style edits on top of the word cut: `cuts` = [[a, b], …] source seconds removed (camera fiddling,
    a stumble the transcript missed…), `splits` = source seconds where a clip is divided in two without removing
    anything. Pieces with no words left are dropped (they're only silence)."""
    if not cuts and not splits and not keeps:
        return segs
    if keeps:
        segs = _apply_keeps(segs, keeps)
    cuts = sorted((float(a), float(b)) for a, b in (cuts or []) if float(b) > float(a))
    out = []
    for sg in segs:
        pieces = [(sg["s"], sg["e"])]
        for a, b in cuts:
            nxt = []
            for s, e in pieces:
                if b <= s or a >= e:
                    nxt.append((s, e))
                    continue
                if a > s:
                    nxt.append((s, a))
                if b < e:
                    nxt.append((b, e))
            pieces = nxt
        for x in sorted(float(t) for t in (splits or [])):
            nxt = []
            for s, e in pieces:
                if s + 0.05 < x < e - 0.05:
                    nxt += [(s, x), (x, e)]
                else:
                    nxt.append((s, e))
            pieces = nxt
        for s, e in pieces:
            if e - s < 0.04:
                continue
            ww = _reassign((s, e), words, sg["w0"], sg["w1"])
            if ww:
                out.append({"w0": ww[0], "w1": ww[1], "s": round(s, 3), "e": round(e, 3)})
    t = 0.0
    for sg in out:
        sg["o"] = round(t, 3)
        t += sg["e"] - sg["s"]
    return out


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


def is_cue(v):
    return isinstance(v, dict) and isinstance(v.get("w"), int) and set(v) <= {"w", "dt"}


def resolve_cues(obj, words, segs, t0):
    """Inside a look, anything can be timed to a spoken word: {"w": 57} (optionally {"w": 57, "dt": 0.1}) becomes
    the seconds from the look's start to the moment word 57 is said. So a check lands on "Monday", a list item
    appears on its word, a counter starts on the number. A cut word falls back to the next kept word."""
    if is_cue(obj):
        i = obj["w"]
        wo = None
        for j in range(i, min(len(words), i + 40)):
            wo = word_out(words, segs, j)
            if wo:
                break
        return round(max(0.0, (wo[0] if wo else t0) - t0) + float(obj.get("dt", 0) or 0), 3)
    if isinstance(obj, dict):
        return {k: resolve_cues(v, words, segs, t0) for k, v in obj.items()}
    if isinstance(obj, list):
        return [resolve_cues(v, words, segs, t0) for v in obj]
    return obj


def with_cues(ov, words, segs, t0):
    """A copy of the overlay with its word cues turned into seconds (for drawing)."""
    if ov.get("kind") != "look" or "w" not in json_str(ov.get("params")):
        return ov
    return dict(ov, params=resolve_cues(ov.get("params") or {}, words, segs, t0))


def json_str(x):
    import json
    return json.dumps(x or {})


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
