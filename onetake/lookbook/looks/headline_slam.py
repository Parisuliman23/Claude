META = {
    "name": "Headline slam",
    "description": "A heavyweight headline scales down into frame, lands with a three-frame shake, drifts slightly, and "
                   "whips up and out at the end. Big claims, plot twists, 'STOP DOING THIS'.",
    "params": {"text": "STOP PAYING MINIMUMS", "color": "#FFFFFF", "accent": "#F5C542", "accent_words": ["MINIMUMS"],
               "size": 120, "width": 0.86, "land_at": 0.0, "exit": True},
}


def render(ctx):
    import math
    p = ctx.p
    f = ctx.font(ctx.MO_BLACK, int(p["size"]))
    words = str(p["text"]).upper().split()
    lines = ctx.wrap(" ".join(words), f, ctx.W * p["width"])
    lh = int(p["size"] * 1.02)
    W = int(max(f.getlength(l) for l in lines) + 60)
    H = lh * len(lines) + 60
    img = ctx.Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ctx.ImageDraw.Draw(img)
    acc = {w.upper() for w in p["accent_words"]}
    for i, ln in enumerate(lines):
        x = (W - f.getlength(ln)) / 2
        for w in ln.split():
            d.text((x, 30 + i * lh + lh * 0.85), w, font=f, fill=ctx.rgba(p["accent"] if w.strip(".,!?") in acc else p["color"]), anchor="ls")
            x += f.getlength(w + " ")
    img = ctx.shadowed(img, blur=10, offset=5, alpha=170)
    t = ctx.t - p["land_at"]
    if t < 0:
        return None
    LAND = 0.28
    sc = 1.0 + 1.6 * (1 - ctx.expo(t / LAND)) if t < LAND else 1.0
    a = min(1.0, t / 0.08)
    dx = dy = 0.0
    fr = (t - LAND) * 30
    if 0 <= fr < 3:  # the three-frame shake on landing
        dx, dy = [(9, -5), (-6, 4), (0, 0)][int(fr)]
    elif t >= LAND:
        dy = -min(6.0, (t - LAND) * 3)  # gentle drift while it holds
    if p["exit"] and ctx.dur - ctx.t < 0.22:  # whip up and out
        e = 1 - (ctx.dur - ctx.t) / 0.22
        dy -= 260 * e * e
        a *= 1 - e
    if sc != 1.0:
        img = img.resize((max(1, int(img.width * sc)), max(1, int(img.height * sc))))
    if a < 1:
        img = ctx.faded(img, a)
    if dx or dy:
        canvas = ctx.Image.new("RGBA", (img.width + 40, img.height + 600), (0, 0, 0, 0))
        canvas.alpha_composite(img, (int(20 + dx), int(300 + dy)))
        return canvas
    return img
