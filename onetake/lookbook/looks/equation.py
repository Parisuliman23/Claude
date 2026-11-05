META = {
    "name": "Rule / equation",
    "description": "Process or formula built term by term: [IF VIX > 30] → [BUY +$800]. Left box pops first; arrow and result appear at right_at seconds.",
    "params": {"left": "IF VIX > 30", "right": "BUY +$800", "note": "", "right_at": 1.0, "panel": True,
               "accent": "#0444A4", "size": 44},
}


def render(ctx):
    p = ctx.p
    f = ctx.font(ctx.SANS, p["size"])
    lw, rw = f.getlength(p["left"]) + 60, f.getlength(p["right"]) + 60
    bh = int(p["size"] * 2)
    aw = 150
    W = int(lw + aw + rw + 80)
    H = bh + 120
    img = ctx.Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ctx.ImageDraw.Draw(img)
    if p["panel"]:
        d.rounded_rectangle([0, 0, W - 1, H - 1], radius=18, fill=(255, 255, 255, 255))
    x, y = 40, 50
    d.rectangle([x, y, x + lw, y + bh], outline=(30, 30, 30, 255), width=4)
    d.text((x + lw / 2, y + bh / 2), p["left"], font=f, fill=(20, 20, 24, 255), anchor="mm")
    if ctx.t >= p["right_at"]:
        k = ctx.ease(min(1, (ctx.t - p["right_at"]) / 0.3))
        ax0, ax1 = x + lw + 20, x + lw + 20 + (aw - 40) * k
        col = ctx.rgba(p["accent"])
        d.line([(ax0, y + bh / 2), (ax1, y + bh / 2)], fill=col, width=10)
        if k > 0.9:
            d.polygon([(ax1 + 6, y + bh / 2), (ax1 - 22, y + bh / 2 - 18), (ax1 - 22, y + bh / 2 + 18)], fill=col)
            rx = x + lw + aw
            d.rectangle([rx, y, rx + rw, y + bh], fill=col)
            d.text((rx + rw / 2, y + bh / 2), p["right"], font=f, fill=(255, 255, 255, 255), anchor="mm")
            if p["note"]:
                d.text((rx + rw / 2, y + bh + 30), p["note"], font=ctx.font(ctx.SANS, int(p["size"] * 0.5)),
                       fill=(90, 90, 100, 255), anchor="mm")
    return img
