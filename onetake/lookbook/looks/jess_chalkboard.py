META = {
    "name": "Class chalkboard",
    "description": "A green chalkboard across the top half (wood ledge underneath): a chalk title, then lines written in "
                   "chalk colours as they're said, with optional arrows. Definitions ('BETA = …'), formulas, the "
                   "series title card ('I WANT TO START INVESTING').",
    "params": {"title": "MARKET CAPITAL", "title_at": 0.0,
               "lines": [{"t": "market assigned value", "c": "white"},
                         {"t": "Stock Price x # of Shares Outstanding", "c": "yellow"},
                         {"t": "Ex. $100 x 1,000,000 shares = $100 Million", "c": "pink"}],
               "at": [], "gap": 1.0, "cps": 30, "height": 0.47, "hand": True},
}
# lines: {"t": text, "c": white | yellow | pink | blue, "size": 1.0, "font": "hand" | "chalk"}


def render(ctx):
    import math
    p, JS = ctx.p, ctx.JS
    W, H = ctx.W, int(ctx.H * p["height"])
    img = ctx.Image.new("RGBA", (W, H + 40), (0, 0, 0, 0))
    d = ctx.ImageDraw.Draw(img)
    d.rectangle([0, 0, W, H], fill=ctx.rgba(JS["board"]))
    dust = ctx.Image.new("RGBA", img.size, (0, 0, 0, 0))  # chalk dust smudges, the same every frame
    dd = ctx.ImageDraw.Draw(dust)
    for k in range(60):
        x = (math.sin(k * 12.9898) * 43758.5453) % 1 * W
        y = (math.sin(k * 78.233) * 12345.678) % 1 * H
        r = 30 + (k * 37) % 90
        dd.ellipse([x - r, y - r * 0.4, x + r, y + r * 0.4], fill=(255, 255, 255, 10))
    img.alpha_composite(dust.filter(ctx.ImageFilter.GaussianBlur(18)))
    d = ctx.ImageDraw.Draw(img)
    d.rectangle([0, H - 26, W, H + 6], fill=ctx.rgba(JS["frame"]))
    d.rectangle([0, H + 6, W, H + 18], fill=(0, 0, 0, 90))
    cols = {"white": JS["chalk"], "yellow": JS["chalk_y"], "pink": JS["chalk_p"], "blue": JS["chalk_b"]}
    tf = ctx.font(ctx.JS_CHALK, 118)
    d.text((W / 2, 170), ctx.typed_text(p["title"], p["title_at"], 22, False), font=tf, fill=ctx.rgba(JS["chalk_y"]), anchor="ms")
    at = list(p["at"])
    y = 230
    for i, ln in enumerate(p["lines"]):
        t0 = at[i] if i < len(at) and at[i] is not None else p["title_at"] + 0.6 + i * p["gap"]
        sc = float(ln.get("size", 1.0))
        f = ctx.font(ctx.JS_CHALK if ln.get("font") == "chalk" else ctx.NB_HAND, int(66 * sc))
        lh = int(84 * sc)
        if ctx.t >= t0:
            text = ln["t"]
            for wl in ctx.wrap(text, f, W * 0.86) or [""]:
                ctx.hand(d, (W / 2, y + lh * 0.8), wl, int(66 * sc), chars=(ctx.t - t0) * p["cps"],
                         fill=cols.get(ln.get("c", "white"), ln.get("c", "#FFFFFF")), anchor="ms", track=0.03)
                y += lh
        else:
            y += lh * max(1, len(ctx.wrap(ln["t"], f, W * 0.86)))
    return img
