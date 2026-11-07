import math

META = {
    "name": "Hand-drawn circle call-out",
    "description": "A wobbly hand-drawn ellipse draws itself around something in the frame (place the look on it), with "
                   "an optional curved arrow to a handwritten label that pops in. Point at a number, an app, your hand.",
    "params": {"label": "this one!", "w": 360, "h": 220, "color": "#F5C542", "draw_at": 0.0, "draw_time": 0.5,
               "label_side": "right", "stroke": 9},
}


def render(ctx):
    p = ctx.p
    w, h = float(p["w"]), float(p["h"])
    lab = bool(p["label"])
    extra = 420 if lab else 0
    W, H = int(w + 80 + extra * 2), int(h + 260)
    img = ctx.Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ctx.ImageDraw.Draw(img)
    col = ctx.rgba(p["color"])
    cx, cy = W / 2, H / 2
    k = ctx.inout(ctx.prog(p["draw_at"], p["draw_time"]))
    n = 90
    pts = []
    for i in range(int(n * 1.08 * k) + 1):  # a bit more than a full loop, like a real pen
        a = -2.4 + 2 * math.pi * i / n
        wob = 1 + 0.04 * math.sin(a * 3 + 1) + 0.025 * math.sin(a * 7)
        pts.append((cx + w / 2 * wob * math.cos(a), cy + h / 2 * wob * math.sin(a) + i * 0.15))
    if len(pts) > 1:
        d.line(pts, fill=col, width=int(p["stroke"]), joint="curve")
    if lab and k >= 1:
        right = p["label_side"] != "left"
        sx = cx + (w / 2 + 6) * (1 if right else -1)
        a = ctx.inout(ctx.prog(p["draw_at"] + p["draw_time"], 0.35))
        ex = sx + (150 if right else -150)
        ctx.curve(d, (sx, cy - 10), (sx + (60 if right else -60), cy - 110), (ex, cy - 120), a, width=6, fill=p["color"])
        if a >= 1:
            pop = ctx.ease_back(ctx.prog(p["draw_at"] + p["draw_time"] + 0.35, 0.25))
            lf = ctx.font(ctx.HAND, int(64 * max(0.01, pop)))
            d.text((ex + (16 if right else -16), cy - 130), p["label"], font=lf, fill=col, anchor="ls" if right else "rs")
    return ctx.shadowed(img, blur=5, offset=2, alpha=120)
