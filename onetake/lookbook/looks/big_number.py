META = {
    "name": "Big number counter",
    "description": "A big white number that counts up with ease-out (~1.25 s, fast start, slow settle), with a handwritten label. No card.",
    "params": {"to": 50000, "from": 0, "prefix": "$", "suffix": "", "label": "paid off in 1 year", "size": 190,
               "count_time": 1.25, "color": "#FFFFFF", "commas": True, "font": "Montserrat_900Black"},
}


def render(ctx):
    p = ctx.p
    k = ctx.ease(min(1.0, ctx.t / max(0.1, p["count_time"])))
    n = p["from"] + (p["to"] - p["from"]) * k
    n = int(round(n))
    fmt = (lambda v: f"{v:,}") if p["commas"] else str
    full = f'{p["prefix"]}{fmt(p["to"])}{p["suffix"]}'
    now = f'{p["prefix"]}{fmt(n)}{p["suffix"]}'
    f = ctx.font(p["font"], p["size"])
    w = int(f.getlength(full) + 40)
    num = ctx.Image.new("RGBA", (w, int(p["size"] * 1.2)), (0, 0, 0, 0))
    ctx.ImageDraw.Draw(num).text((w / 2, p["size"] * 0.6), now, font=f, fill=ctx.rgba(p["color"]), anchor="mm")
    label = ctx.write(p["label"], ctx.HAND, 70, ctx.W * 0.8, fill=p["color"]) if p["label"] else None
    return ctx.shadowed(ctx.stack([num, label], gap=0), blur=8)
