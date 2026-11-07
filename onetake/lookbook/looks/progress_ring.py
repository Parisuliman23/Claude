META = {
    "name": "Progress ring",
    "description": "A ring fills to a percentage while the number counts up, with a label underneath. "
                   "Savings rate, % paid off, goal reached.",
    "params": {"percent": 72, "label": "of my debt paid off", "fill_at": 0.25, "fill_time": 1.3, "color": "up",
               "card": True, "size": 360},
}


def render(ctx):
    p, MO = ctx.p, ctx.MO
    S = int(p["size"])
    color = ctx.rgba(MO.get(p["color"], p["color"]))
    lf = ctx.font(ctx.MO_SEMI, 34)
    lines = ctx.wrap(p["label"], lf, S + 120) if p["label"] else []
    W, H = S + 160, S + 120 + 46 * len(lines)
    if p["card"]:
        img, pad = ctx.card(W, H, radius=32, fill=MO["card"])
    else:
        img, pad = ctx.Image.new("RGBA", (W, H), (0, 0, 0, 0)), 0
    d = ctx.ImageDraw.Draw(img)
    cx, cy, r, w = pad + W / 2, pad + 60 + S / 2, S / 2, 34
    k = ctx.p3(ctx.prog(p["fill_at"], p["fill_time"]))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ctx.rgba(MO["line"]), width=w)
    if k > 0:
        d.arc([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * p["percent"] / 100 * k, fill=color, width=w)
    ink = ctx.rgba(MO["ink"] if p["card"] else "#FFFFFF")
    d.text((cx, cy), f"{int(round(p['percent'] * k))}%", font=ctx.font(ctx.MO_BOLD, int(S * 0.3)), fill=ink, anchor="mm")
    for i, ln in enumerate(lines):
        d.text((cx, pad + 60 + S + 60 + i * 46), ln, font=lf, fill=ctx.rgba(MO["muted"] if p["card"] else "#FFFFFF"), anchor="ms")
    return img if p["card"] else ctx.shadowed(img)
