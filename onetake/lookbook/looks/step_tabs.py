META = {
    "name": "Step tabs (top bar)",
    "description": "A row of numbered tabs across the top (1 catch, 2 pick...). The current step is yellow and raised; "
                   "the others are cream. Use one per section with a new 'active' to move through the steps.",
    "params": {"steps": ["catch", "pick", "jobs", "format", "film", "board"], "active": 0, "width": 0.82},
}


def render(ctx):
    p, NB = ctx.p, ctx.NB
    steps = list(p["steps"])
    W = int(ctx.W * p["width"])
    gap, h = 12, 52
    tw = (W - gap * (len(steps) - 1)) / len(steps)
    pad = 20
    img = ctx.Image.new("RGBA", (W + pad * 2, h + 12 + pad * 2), (0, 0, 0, 0))
    sh = ctx.Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ctx.ImageDraw.Draw(sh)
    for i in range(len(steps)):
        x = pad + i * (tw + gap)
        lift = 4 if i == int(p["active"]) else 0
        sd.rounded_rectangle([x, pad + 8 - lift, x + tw, pad + 8 - lift + h], radius=10, fill=(0, 0, 0, 70))
    img.alpha_composite(sh.filter(ctx.ImageFilter.GaussianBlur(6)))
    d = ctx.ImageDraw.Draw(img)
    for i, step in enumerate(steps):
        on = i == int(p["active"])
        x = pad + i * (tw + gap)
        y = pad + 6 - (4 if on else 0)
        d.rounded_rectangle([x, y, x + tw, y + h + (4 if on else 0)], radius=10, fill=ctx.rgba(NB["yellow"] if on else "#EFEBE3"))
        col = ctx.rgba(NB["ink"] if on else NB["gray"])
        num, word = ctx.font(ctx.NB_SERIF, 34), ctx.font(ctx.NB_BOLD if on else ctx.NB_SEMI, 24)
        label = f"{i + 1}"
        wn, ww = num.getlength(label), word.getlength(step)
        sx = x + (tw - wn - 8 - ww) / 2
        cy = y + (h + (4 if on else 0)) / 2
        d.text((sx, cy + 11), label, font=num, fill=col, anchor="ls")
        d.text((sx + wn + 8, cy + 9), step, font=word, fill=col, anchor="ls")
    return img
