META = {
    "name": "Growth curve card",
    "description": "Cream grid-paper card: a label, two axes, and an S-curve that draws itself, ending in a yellow dot "
                   "with a handwritten 'you'. Great for 'the more you do it…' or money growing over time.",
    "params": {"label": "confident + energetic", "x_label": "the more you do it", "dot_label": "you",
               "draw_at": 0.3, "draw_dur": 1.2, "width": 0.64, "height": 300},
}


def render(ctx):
    import math
    p, NB = ctx.p, ctx.NB
    W, H = int(ctx.W * p["width"]), int(p["height"])
    img, pad = ctx.paper(W, H, grid=26, radius=6)
    d = ctx.ImageDraw.Draw(img)
    ink = ctx.rgba(NB["ink"])
    d.text((pad + 26, pad + 40), p["label"], font=ctx.font(ctx.NB_BOLD, 26), fill=ink, anchor="ls")
    ox, oy = pad + 36, pad + H - 48
    top, right = pad + 62, pad + W - 34
    d.line([(ox, oy), (ox, top)], fill=ink, width=3)
    d.line([(ox, top), (ox - 9, top + 14)], fill=ink, width=3)
    d.line([(ox, top), (ox + 9, top + 14)], fill=ink, width=3)
    d.line([(ox, oy), (right, oy)], fill=ink, width=3)
    d.line([(right, oy), (right - 14, oy - 9)], fill=ink, width=3)
    d.line([(right, oy), (right - 14, oy + 9)], fill=ink, width=3)
    d.text((right - 10, oy + 32), p["x_label"], font=ctx.font(ctx.NB_LABEL, 21), fill=ctx.rgba(NB["gray"]), anchor="rs")
    k = max(0.0, min(1.0, (ctx.t - p["draw_at"]) / p["draw_dur"]))
    if k > 0:
        k = ctx.ease(k)
        pts = []
        for i in range(int(80 * k) + 1):
            u = i / 80
            v = (1 / (1 + math.exp(-7 * (u - 0.55))) - 0.0205) / 0.9535  # a gentle S that keeps climbing
            pts.append((ox + 12 + u * (right - ox - 70), oy - 12 - v * (oy - top - 22)))
        if len(pts) > 1:
            d.line(pts, fill=ink, width=5, joint="curve")
        if k >= 1:
            ex, ey = pts[-1]
            d.ellipse([ex - 13, ey - 13, ex + 13, ey + 13], fill=ctx.rgba(NB["yellow"]), outline=ink, width=3)
            if p["dot_label"]:
                ctx.hand(d, (ex - 4, ey + 46), p["dot_label"], 30, anchor="ms")
    return img
