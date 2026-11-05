META = {
    "name": "Red X (wrong)",
    "description": "Contrarian \"Wrong.\": a red ✗ drawn in two strokes (~0.25 s each), optional handwritten label.",
    "params": {"size": 300, "color": "#FC1404", "label": "", "width": 26},
}


def render(ctx):
    p = ctx.p
    S = p["size"]
    img = ctx.Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ctx.ImageDraw.Draw(img)
    m = p["width"]
    k1 = ctx.ease(min(1, ctx.t / 0.25))
    k2 = ctx.ease(min(1, max(0, ctx.t - 0.25) / 0.25))
    col = ctx.rgba(p["color"])
    if k1 > 0:
        d.line([(m, m), (m + (S - 2 * m) * k1, m + (S - 2 * m) * k1)], fill=col, width=p["width"])
    if k2 > 0:
        d.line([(S - m, m), (S - m - (S - 2 * m) * k2, m + (S - 2 * m) * k2)], fill=col, width=p["width"])
    label = ctx.write(p["label"], ctx.HAND, 64, ctx.W * 0.7, fill="#FFFFFF") if p["label"] else None
    return ctx.shadowed(ctx.stack([img, label], gap=0))
