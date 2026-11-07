META = {
    "name": "Hook title (sans + serif italic)",
    "description": "The opening title stacked in three lines: small bold white, a big yellow serif-italic phrase, small "
                   "bold white again. On screen from the first frame.",
    "params": {"top": "if you make your content", "mid": "the same day", "bottom": "you post, we need to talk.",
               "color": "#FFFFFF", "accent": "#EED98A", "size": 48, "mid_scale": 2.3},
}


def render(ctx):
    p = ctx.p
    sz = int(p["size"])
    fs, fm = ctx.font("Poppins_700Bold", sz), ctx.font(ctx.NB_SERIF, int(sz * p["mid_scale"]))
    rows = [(p["top"], fs, p["color"]), (p["mid"], fm, p["accent"]), (p["bottom"], fs, p["color"])]
    rows = [r for r in rows if r[0]]
    W = int(max(f.getlength(t) for t, f, _ in rows) + 40)
    hs = [int(f.size * (1.0 if f is fm else 1.25)) for _, f, _ in rows]
    img = ctx.Image.new("RGBA", (W, sum(hs) + 20), (0, 0, 0, 0))
    d = ctx.ImageDraw.Draw(img)
    y = 10
    for (t, f, col), h in zip(rows, hs):
        d.text((W / 2, y + h * 0.82), t, font=f, fill=ctx.rgba(col), anchor="ms")
        y += h
    return ctx.shadowed(img, blur=5, offset=2, alpha=120)
