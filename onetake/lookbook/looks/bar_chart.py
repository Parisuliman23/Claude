META = {
    "name": "Bar chart (grows)",
    "description": "White data card: a title, a big result (e.g. +42% or $0 debt) and bars that grow one after another, "
                   "each on its word. Highlight one bar in the accent colour. Great for comparisons and growth.",
    "params": {"title": "debt paid off", "stat": "+$50,000", "stat_color": "up",
               "values": [12000, 21000, 33000, 50000], "labels": ["Q1", "Q2", "Q3", "Q4"], "prefix": "$", "suffix": "",
               "show_values": True, "highlight": -1, "grow_at": 0.25, "bars_at": [], "stagger": 0.12,
               "grow_time": 0.9, "width": 0.76, "accent": "accent"},
}
# bars_at: one time (or word cue {"w": i}) per bar. stat_color / accent: up | down | accent | a #hex colour.


def render(ctx):
    p, MO = ctx.p, ctx.MO
    col = lambda c: ctx.rgba(MO.get(c, c))
    vals = [float(v) for v in p["values"]] or [1]
    n = len(vals)
    W = int(ctx.W * p["width"])
    H = 460
    img, pad = ctx.card(W, H, radius=28, fill=MO["card"])
    d = ctx.ImageDraw.Draw(img)
    ink, muted = col("ink"), col("muted")
    intro = ctx.p3(ctx.prog(0, 0.35))
    d.text((pad + 40, pad + 70), p["title"], font=ctx.font(ctx.MO_BOLD, 40), fill=ink, anchor="ls")
    if p["stat"]:
        sf = ctx.font(ctx.MO_BOLD, 64)
        d.text((pad + W - 40, pad + 84), p["stat"], font=sf, fill=col(p["stat_color"]) if intro > 0.5 else (0, 0, 0, 0), anchor="rs")
    x0, x1, base, top = pad + 40, pad + W - 40, pad + H - 70, pad + 150
    d.line([(x0, base), (x1, base)], fill=col("line"), width=3)
    gap = 26
    bw = (x1 - x0 - gap * (n - 1)) / n
    mx = max(vals) or 1
    at = list(p["bars_at"])
    vf = ctx.font(ctx.MO_BOLD, 30)
    lf = ctx.font(ctx.MO_SEMI, 26)
    for i, v in enumerate(vals):
        start = at[i] if i < len(at) and at[i] is not None else p["grow_at"] + i * p["stagger"]
        k = ctx.p3(ctx.prog(start, p["grow_time"]))
        x = x0 + i * (bw + gap)
        h = (base - top) * (v / mx) * k
        c = col(p["accent"]) if (p["highlight"] < 0 or i == p["highlight"]) else col("line")
        if p["highlight"] >= 0 and i != p["highlight"]:
            c = ctx.rgba("#CBD5E1")
        if h > 1:
            d.rounded_rectangle([x, base - h, x + bw, base], radius=min(14, bw / 4), fill=c)
            d.rectangle([x, base - min(h, 14), x + bw, base], fill=c)
        if p["show_values"] and k > 0.05:
            d.text((x + bw / 2, base - h - 14), f"{p['prefix']}{ctx.fmt_num(v * k)}{p['suffix']}", font=vf, fill=ink, anchor="ms")
        if i < len(p["labels"]):
            d.text((x + bw / 2, base + 40), str(p["labels"][i]), font=lf, fill=muted, anchor="ms")
    return img
