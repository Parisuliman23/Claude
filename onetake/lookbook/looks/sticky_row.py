META = {
    "name": "Sticky notes row",
    "description": "A row of yellow sticky notes that fade in one after another (left to right), each numbered in serif "
                   "italic; a bold title and handwritten note fill in on cue. 'focus' dims the others.",
    "params": {"notes": [{"icon": "bookmark", "title": "save", "body": "useful: worth keeping"}, {"icon": "follow", "title": "follow", "body": "a story: what happens next?"},
                         {"title": "", "body": ""}, {"title": "", "body": ""}],
               "appear_gap": 0.067, "appear_at": [], "text_at": [], "text_gap": 1.2, "focus": -1, "width": 0.74, "height": 250},
}


def render(ctx):
    p, NB = ctx.p, ctx.NB
    notes = list(p["notes"])
    W = int(ctx.W * p["width"])
    gap = 22
    n = len(notes)
    nw, nh = (W - gap * (n - 1)) / n, int(p["height"])
    pad = 24
    img = ctx.Image.new("RGBA", (W + pad * 2, nh + pad * 2), (0, 0, 0, 0))
    text_at = list(p["text_at"]) + [None] * n
    ink = ctx.rgba(NB["ink"])
    for i, note in enumerate(notes):
        ap = list(p["appear_at"])
        a = ctx.appear(ap[i] if i < len(ap) and ap[i] is not None else i * p["appear_gap"], 0.12)
        if a <= 0:
            continue
        if p["focus"] >= 0 and i != p["focus"]:
            a *= 0.45
        x = pad + i * (nw + gap)
        layer = ctx.Image.new("RGBA", img.size, (0, 0, 0, 0))
        layer.alpha_composite(ctx.shadows(img.size, [(x + 2, pad, x + nw + 2, pad + nh)], radius=0, blur=7, alpha=70, dy=6))
        d = ctx.ImageDraw.Draw(layer)
        d.rectangle([x, pad, x + nw, pad + nh], fill=ctx.rgba(NB["sticky"]))
        d.text((x + nw - 22, pad + 50), str(i + 1), font=ctx.font(ctx.NB_SERIF, 46), fill=ctx.rgba("#8C7A3A"), anchor="rs")
        ta = text_at[i] if text_at[i] is not None else 0.4 + i * p["text_gap"]
        if (note.get("title") or note.get("body")) and ctx.t >= ta:
            if note.get("icon") in ctx.ICONS:
                ctx.icon(d, note["icon"], x + 32, pad + 34, 30)
            if note.get("title"):
                d.text((x + 16, pad + 92), note["title"], font=ctx.font(ctx.NB_BOLD, 34), fill=ink, anchor="ls")
            if note.get("body"):  # a line break after a colon, like the reference ("useful:" / "worth keeping")
                f = ctx.font(ctx.NB_HAND, 29)
                y = pad + 136
                used = 0
                body = note["body"].replace(": ", ":\n")
                for para in body.split("\n"):
                    for ln in ctx.wrap(para, f, nw - 30):
                        ctx.hand(d, (x + 16, y), ln, 29, chars=(ctx.t - ta - 0.15) * 30 - used, track=0.03)
                        used += len(ln) + 1
                        y += 35
        img.alpha_composite(ctx.faded(layer, a))
    return img
