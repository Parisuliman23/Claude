META = {
    "name": "Success check",
    "description": "A circle draws itself, fills green and a white check pops in with a small bounce, plus an "
                   "optional word underneath (DONE, PAID OFF). For a finished step or a win.",
    "params": {"label": "PAID OFF", "color": "#16A34A", "at": 0.0, "size": 220},
}


def render(ctx):
    p = ctx.p
    S = int(p["size"])
    lf = ctx.font(ctx.MO_BLACK, int(S * 0.3))
    W = int(max(S + 60, lf.getlength(p["label"]) + 40))
    H = S + 60 + (int(S * 0.45) if p["label"] else 0)
    img = ctx.Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ctx.ImageDraw.Draw(img)
    cx, cy, r = W / 2, 30 + S / 2, S / 2
    col = ctx.rgba(p["color"])
    k = ctx.inout(ctx.prog(p["at"], 0.35))
    if k <= 0:
        return None
    if k < 1:
        d.arc([cx - r, cy - r, cx + r, cy + r], -90, -90 + 360 * k, fill=col, width=max(6, S // 18))
    else:
        pop = ctx.ease_back(ctx.prog(p["at"] + 0.35, 0.25))
        rr = r * (0.92 + 0.08 * pop)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col)
        ctx.check(d, cx, cy + 4, S * 0.55, fill="#FFFFFF", width=max(8, S // 14), progress=ctx.prog(p["at"] + 0.4, 0.25))
        if p["label"]:
            a = ctx.prog(p["at"] + 0.55, 0.2)
            d.text((cx, H - 10), p["label"], font=lf, fill=ctx.rgba("#FFFFFF")[:3] + (int(255 * a),), anchor="ms")
    return ctx.shadowed(img, blur=8, offset=4, alpha=150)
