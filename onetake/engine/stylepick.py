"""Pick the editing style that fits a video, from what's said in it.

  notebook (Look D): a process, a routine, lists, tips, a story told calmly; cards fill in as you talk.
  motion   (Look E): numbers, money, growth or decline, comparisons, results, a hype/energetic delivery;
                     animated charts, slams, transitions.
  mix:               both: notebook cards for the steps + motion charts/numbers for the data moments.

It scores the transcript and returns the pick, the reasons and the moments (word indexes) that suit each kind of
graphic, so Claude can place them on the right words.
"""
import re

MONEY = re.compile(r"^\$?\d[\d,]*(\.\d+)?[kKmM]?%?$|^\$")
NUMWORDS = {"hundred", "thousand", "million", "billion", "percent", "half", "double", "triple", "twice"}
TREND = {"grow", "grew", "growing", "growth", "increase", "increased", "doubled", "compound", "compounding", "climb",
         "drop", "dropped", "decline", "down", "crash", "fell", "rise", "rising", "skyrocket", "zero", "debt-free",
         "paid", "save", "saved", "saving", "invest", "invested", "interest", "rate", "returns"}
COMPARE = {"vs", "versus", "instead", "compared", "than", "better", "worse", "difference"}
PROCESS = {"step", "steps", "first", "second", "third", "next", "then", "finally", "process", "routine", "system",
           "every", "week", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "daily",
           "habit", "habits", "list", "tips", "ways", "rules", "framework", "plan", "method"}
STORY = {"i", "me", "my", "remember", "when", "felt", "feel", "told", "said", "story", "realized", "honestly"}
HYPE = {"crazy", "insane", "huge", "massive", "stop", "never", "secret", "nobody", "everyone", "mistake", "biggest",
        "literally", "wow"}


def _clean(t):
    return t.lower().strip(".,!?;:\"'()")


def analyze(p):
    words = [w for w in p["words"] if not w.get("cut")]
    toks = [(i, _clean(w["t"]), w["t"]) for i, w in enumerate(p["words"]) if not w.get("cut")]
    n = max(1, len(toks))
    moments = {"number": [], "trend": [], "compare": [], "process": [], "hype": []}
    for i, c, raw in toks:
        if MONEY.match(raw.strip(".,!?")) or c in NUMWORDS or (c.isdigit() and len(c) > 1):
            moments["number"].append(i)
        if c in TREND:
            moments["trend"].append(i)
        if c in COMPARE:
            moments["compare"].append(i)
        if c in PROCESS:
            moments["process"].append(i)
        if c in HYPE:
            moments["hype"].append(i)
    story = sum(1 for _, c, _ in toks if c in STORY) / n
    per100 = lambda k: 100 * len(moments[k]) / n
    data = per100("number") * 2.2 + per100("trend") * 1.2 + per100("compare") * 0.6 + per100("hype") * 0.8
    steps = per100("process") * 1.6 + story * 100 * 0.25
    dur = max(1e-6, (words[-1]["e"] - words[0]["s"]) if words else 1)
    wps = len(words) / dur
    if wps > 3.6:
        data += 1.0  # fast, energetic delivery suits punchier motion graphics
    reasons = [f"{len(moments['number'])} numbers/amounts, {len(moments['trend'])} growth/money words, "
               f"{len(moments['compare'])} comparisons, {len(moments['process'])} step/routine words, "
               f"{len(moments['hype'])} hype words; {wps:.1f} words/s"]
    if data >= steps * 1.6 and data > 3:
        pick = "motion"
        reasons.append("it's driven by numbers and results, so animated charts, counters and transitions tell it best")
    elif steps >= data * 1.6 and steps > 3:
        pick = "notebook"
        reasons.append("it walks through steps, a routine or a story, so notebook cards that fill in as you talk fit best")
    else:
        pick = "mix"
        reasons.append("it has both steps and numbers: notebook cards for the steps, motion charts/numbers for the data")
    return {"pick": pick, "scores": {"motion": round(data, 1), "notebook": round(steps, 1)}, "reasons": reasons,
            "moments": {k: v[:40] for k, v in moments.items()}}


STYLE_CAPTIONS = {"notebook": "notebook-word", "motion": "motion-pill", "mix": "notebook-word"}
