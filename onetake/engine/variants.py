"""Several versions of one edit, each its own project with the same cut, in a different style.

The user always wants one version in the class style (Look F, from Jess Inskip's reels); the others follow
style-pick (notebook / motion / mix). Each version is a normal project ("<name>-class", "<name>-motion"…) that
shares the original's footage, so the studio, render, phone page and CapCut export all just work.
"""
import copy
import json
import os
import shutil

from . import config, project, stylepick

STYLES = {  # style: (caption style, hook look, label)
    "class": ("class-serif", "jess_title", "Class style"),
    "notebook": ("notebook-word", "serif_hook", "Notebook style"),
    "motion": ("motion-pill", "headline_slam", "Motion style"),
    "mix": ("notebook-word", "serif_hook", "Mix style"),
}


def _hook(style, first_line, w0, w1):
    words = first_line.split()
    if style == "class":
        cut = max(1, len(words) // 2)
        return {"look": "jess_title", "y": 0.2, "params": {"parts": [
            {"t": " ".join(words[:cut]).lower().strip(",.!?"), "s": "serif"},
            {"t": " ".join(words[cut:cut + 3]).upper().strip(",.!?"), "s": "red"}]}}
    if style == "motion":
        return {"look": "headline_slam", "y": 0.2, "params": {"text": " ".join(words[:5]).upper().strip(",.!?")}}
    return {"look": "serif_hook", "y": 0.185, "params": {"top": "", "mid": " ".join(words[:5]).strip(",.!?").lower(), "bottom": ""}}


def default_styles(p):
    """The original is already in its picked style, so by default it gets the class version (or notebook, if the
    original is the class one)."""
    return ["notebook"] if p.get("style_variant") == "class" else ["class"]


def make(name, styles=None):
    p = project.load(name)
    base = p.get("variant_of") or name
    own = p.get("style_variant") or (p.get("style_pick") or {}).get("pick") or stylepick.analyze(p)["pick"]
    if not p.get("style_variant"):  # the original is the version in its picked style
        project.update(name, lambda x: x.update({"style_variant": own}))
        p["style_variant"] = own
    styles = styles or default_styles(p)
    made = []
    for st in styles:
        if st not in STYLES:
            raise SystemExit(f"style must be one of: {', '.join(STYLES)}")
        if st == p.get("style_variant"):
            continue
        vname = f"{base}-{st}"
        if project.exists(vname):
            made.append({"name": vname, "style": st, "existing": True})
            continue
        d = project.pdir(vname)
        (d / "exports").mkdir(parents=True)
        (d / "frames").mkdir()
        src = config.absolute(p["source"])
        try:  # share the footage without taking up the space twice
            os.link(src, d / "source.mp4")
        except OSError:
            shutil.copy2(src, d / "source.mp4")
        q = copy.deepcopy(p)
        cap, hook, label = STYLES[st]
        q.update({"source": config.rel(d / "source.mp4"), "variant_of": base, "style_variant": st,
                  "title": f"{(p.get('title') or base).split(' · ')[0]} · {label}", "caption_style": cap,
                  "overlays": [], "fx": [], "sfx": [], "broll": [], "render": {"status": "none"}, "exports": {},
                  "requests": [], "rev": 0, "edit_rev": 0})
        for w in q["words"]:
            w.pop("hl", None)  # keywords are picked per style
        if st == "class":
            eye = float((q.get("focus") or [0.5, 0.38])[1])
            q["caption_y"] = round(max(0.14, eye - 0.17), 3)  # her captions sit just above the head
            q["camera"] = {"push_in": 0, "punches": []}
            q["sound"] = dict(q.get("sound") or {}, volume=0.2)  # her music bed sits right under the voice
        ls = [l for l in project.lines(q) if not l["cut"]]
        if ls:
            h = _hook(st, ls[0]["text"], ls[0]["w0"], ls[0]["w1"])
            q["overlays"].append({"id": project.new_id(), "kind": "look", "look": h["look"], "role": "hook",
                                  "w0": ls[0]["w0"], "w1": ls[0]["w1"], "x": 0.5, "y": h["y"], "scale": 1.0,
                                  "anim_in": "none", "anim_out": "none", "params": h["params"]})
        project.save(vname, q)
        made.append({"name": vname, "style": st})
    if made and p.get("variant_of") is None:  # the original lists its versions (the phone page and renders use it)
        project.update(name, lambda x: x.update({"variants": sorted({*x.get("variants", []), *(m["name"] for m in made)})}))
    return made


def family(name):
    """The original edit and all its versions."""
    p = project.load(name)
    base = p.get("variant_of") or name
    names = [base] + [n for n in project.load(base).get("variants", [])] if project.exists(base) else [name]
    return [n for n in dict.fromkeys(names) if project.exists(n)]
