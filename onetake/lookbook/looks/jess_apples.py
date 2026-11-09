META = {
    "name": "Apples for the teacher",
    "description": "Red apples pop in one after another and fill the frame ('leave me an apple for extra credit'). "
                   "Her outro gag; works for any 'thank you' moment.",
    "params": {"count": 24, "at": 0.0, "rate": 18},
}


def render(ctx):
    import math
    p = ctx.p
    t = ctx.t - p["at"]
    if t <= 0:
        return None
    W, H = ctx.W, int(ctx.H * 0.62)
    img = ctx.Image.new("RGBA", (W, H), (0, 0, 0, 0))
    n = min(int(p["count"]), int(t * p["rate"]) + 1)
    for i in range(n):
        x = (math.sin(i * 12.9898) * 43758.5453) % 1 * (W - 160) + 80
        y = (math.sin(i * 78.233) * 12345.678) % 1 * (H - 160) + 80
        r = 46 + (i * 29) % 50
        k = ctx.ease_back(min(1.0, (t - i / p["rate"]) / 0.18))
        rr = max(1, r * k)
        a = ctx.Image.new("RGBA", (int(rr * 2.6), int(rr * 2.8)), (0, 0, 0, 0))
        d = ctx.ImageDraw.Draw(a)
        c = rr * 1.3
        d.ellipse([c - rr - 6, c - rr * 0.9 - 6, c + rr + 6, c + rr * 1.05 + 6], fill=(255, 255, 255, 255))  # sticker edge
        d.ellipse([c - rr, c - rr * 0.9, c + rr, c + rr * 1.05], fill=ctx.rgba("#6E1424"))
        d.ellipse([c - rr * 0.55, c - rr * 0.6, c - rr * 0.1, c - rr * 0.1], fill=(255, 255, 255, 60))
        d.line([(c, c - rr * 0.8), (c + rr * 0.1, c - rr * 1.25)], fill=ctx.rgba("#3B2414"), width=max(2, int(rr / 9)))
        d.ellipse([c + rr * 0.1, c - rr * 1.3, c + rr * 0.55, c - rr * 1.0], fill=ctx.rgba("#4E8A3A"))
        a = a.rotate(((i * 47) % 40) - 20, resample=ctx.Image.BICUBIC)
        img.alpha_composite(a, (int(x - a.width / 2), int(y - a.height / 2)))
    return ctx.shadowed(img, blur=6, offset=4, alpha=100)
