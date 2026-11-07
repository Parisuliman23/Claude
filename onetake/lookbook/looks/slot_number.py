META = {
    "name": "Slot-machine number",
    "description": "Big digits roll like a slot machine and land on the number, one column after another "
                   "(e.g. $0 → $50,000). White with a soft shadow, no card.",
    "params": {"to": "$50,000", "label": "paid off", "roll_at": 0.1, "roll_time": 0.6, "stagger": 0.07,
               "size": 190, "color": "#FFFFFF", "accent": "#F5C542"},
}


def render(ctx):
    p = ctx.p
    if ctx.t < p["roll_at"]:  # appears as the number is said
        return None
    text = str(p["to"])
    f = ctx.font(ctx.MO_BLACK, int(p["size"]))
    lh = int(p["size"] * 1.05)
    widths = [f.getlength(c) for c in text]
    W = int(sum(widths) + 40)
    lf = ctx.font(ctx.MO_SEMI, int(p["size"] * 0.24))
    H = lh + (int(p["size"] * 0.4) if p["label"] else 0) + 20
    img = ctx.Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x = 20
    di = 0
    for c, cw in zip(text, widths):
        col = ctx.Image.new("RGBA", (int(cw) + 2, lh), (0, 0, 0, 0))
        cd = ctx.ImageDraw.Draw(col)
        if c.isdigit():
            start = p["roll_at"] + di * p["stagger"]
            k = ctx.inout(ctx.prog(start, p["roll_time"]))
            target = int(c) + 10  # roll through a full lap of digits, landing on the right one
            pos = target * k
            for j in (int(pos), int(pos) + 1):
                off = (j - pos) * lh
                cd.text((0, off + lh * 0.82), str(j % 10), font=f, fill=ctx.rgba(p["color"]), anchor="ls")
            di += 1
        else:
            cd.text((0, lh * 0.82), c, font=f, fill=ctx.rgba(p["color"]), anchor="ls")
        img.alpha_composite(col, (int(x), 0))
        x += cw
    if p["label"]:
        done = ctx.t >= p["roll_at"] + max(0, di - 1) * p["stagger"] + p["roll_time"]
        ctx.ImageDraw.Draw(img).text((W / 2, H - 14), p["label"], font=lf,
                                     fill=ctx.rgba(p["accent"] if done else p["color"]), anchor="ms")
    return ctx.shadowed(img, blur=8, offset=4, alpha=170)
