"""The automatic rough cut: drop filler words, false starts and repeated takes
(keeping the last take of a line, which is usually the best one). Long pauses
are removed by the timeline itself. Claude reviews this afterwards."""
import re
from difflib import SequenceMatcher

from . import project

FILLERS = {"um", "uh", "uhm", "umm", "erm", "er", "ah", "hmm", "mm", "mhm"}


def norm(t):
    return re.sub(r"[^a-z0-9$']", "", t.lower())


def similar(a, b):
    """How much line a looks like a retake of line b (0..1)."""
    if not a or not b:
        return 0.0
    ratio = SequenceMatcher(None, a, b).ratio()
    # false start: a is the beginning of b ("so before there was" -> "so before there was ever a product")
    k = 0
    while k < min(len(a), len(b)) and a[k] == b[k]:
        k += 1
    prefix = k / len(a) if len(a) >= 2 else 0.0
    return max(ratio, prefix if k >= 2 else 0.0)


def run(p, lookahead=3, threshold=0.6):
    words = p["words"]
    for w in words:
        if norm(w["t"]) in FILLERS:
            w["cut"] = True
            w["why"] = "filler"
    ls = project.lines(p)
    toks = [[norm(words[i]["t"]) for i in range(l["w0"], l["w1"] + 1) if norm(words[i]["t"]) not in FILLERS] for l in ls]
    cuts = []
    for a in range(len(ls)):
        best = None
        for b in range(a + 1, min(len(ls), a + 1 + lookahead)):
            sc = similar(toks[a], toks[b])
            if sc >= threshold and (best is None or sc > best[1]):
                best = (b, sc)
        if best:
            la, lb = ls[a], ls[best[0]]
            for i in range(la["w0"], la["w1"] + 1):
                words[i]["cut"] = True
                words[i]["why"] = "retake"
            short = len(toks[a]) < len(toks[best[0]]) * 0.7
            cuts.append({"line": la["id"], "kept": lb["id"], "reason": "false start" if short else "earlier take",
                         "text": la["text"]})
    p["engine_cuts"] = cuts
    return cuts
