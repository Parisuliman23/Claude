META = {
    "name": "Crossed-out card",
    "description": "A small white card ('untitled', 'blank page') with faint ghost text that gets crossed out with a "
                   "big drawn X, plus an optional serif-italic word and handwritten line typed beside it.",
    "params": {"label": "untitled", "ghost": "new idea...", "x_at": 0.4, "note": "never", "sub": "sit down and come up with an idea on the spot",
               "note_at": 0.3, "size": 250},
}


def render(ctx):
    p, NB = ctx.p, ctx.NB
    s = int(p["size"])
    side_w = 430 if (p["note"] or p["sub"]) else 0
    n_sub = len(ctx.wrap(p["sub"], ctx.font(ctx.NB_HAND, 34), side_w * 0.92)) if side_w and p["sub"] else 0
    img = ctx.Image.new("RGBA", (s + 48 + side_w + 40, max(s + 48, 140 + 54 * n_sub + 48)), (0, 0, 0, 0))
    card, pad = ctx.paper(s, s, fill=NB["white"], radius=6)
    d = ctx.ImageDraw.Draw(card)
    d.text((pad + 16, pad + 30), p["label"], font=ctx.font(ctx.NB_SEMI, 22), fill=ctx.rgba(NB["gray"]), anchor="ls")
    if p["ghost"]:
        ctx.hand(d, (pad + 22, pad + 104), p["ghost"], 30, fill=NB["faint"])
    ink = ctx.rgba(NB["ink"])
    k = max(0.0, min(1.0, (ctx.t - p["x_at"]) / 0.25))  # two strokes, drawn fast
    m = s * 0.16
    a, b = min(1.0, k * 2), max(0.0, k * 2 - 1)
    if a > 0:
        d.line([(pad + m, pad + m + 20), (pad + m + (s - 2 * m) * a, pad + m + 20 + (s - 2 * m - 20) * a)], fill=ink, width=7)
    if b > 0:
        d.line([(pad + s - m, pad + m + 20), (pad + s - m - (s - 2 * m) * b, pad + m + 20 + (s - 2 * m - 20) * b)], fill=ink, width=7)
    img.alpha_composite(card, (0, 0))
    if side_w:  # the note sits on its own cream paper, so it reads on any background
        n_lines = len(ctx.wrap(p["sub"], ctx.font(ctx.NB_HAND, 34), side_w * 0.92)) if p["sub"] else 0
        note_card, npad = ctx.paper(side_w + 10, 140 + 54 * n_lines, radius=6)
        img.alpha_composite(note_card, (s + 48 - npad + 4, 0))
        d2 = ctx.ImageDraw.Draw(img)
        x = s + 48 + 20
        n = int(max(0.0, ctx.t - p["note_at"]) * 22)
        if p["note"]:
            f = ctx.font(ctx.NB_SERIF, 76)
            d2.text((x, 110), p["note"][:n], font=f, fill=ctx.rgba(NB["ink"]), anchor="ls")
        if p["sub"]:
            start = p["note_at"] + len(p["note"]) / 22 + 0.15
            f = ctx.font(ctx.NB_HAND, 34)
            y = 172
            used = 0
            for ln in ctx.wrap(p["sub"], f, side_w * 0.92):
                ctx.hand(d2, (x, y), ln, 34, chars=(ctx.t - start) * 30 - used)
                used += len(ln) + 1
                y += 54
    return img
