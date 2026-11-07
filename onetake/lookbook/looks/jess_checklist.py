META = {
    "name": "Class checklist card",
    "description": "White rounded card: a serif-italic + red title ('Benefits of ETFs'), then items typed on one by one, "
                   "each box getting a green tick as it lands. Lists of benefits, steps, rules.",
    "params": {"title": [{"t": "Benefits of", "s": "serif"}, {"t": "ETFs", "s": "red"}],
               "items": ["Generally easy to buy and sell", "Access more investments", "Easy to automate", "Can reduce risk"],
               "at": [], "gap": 0.9, "cps": 30, "width": 0.56},
}


def render(ctx):
    p, JS = ctx.p, ctx.JS
    W = int(ctx.W * p["width"])
    items = list(p["items"])
    k = W / (0.56 * ctx.W)  # everything scales with the card's width
    row = int(66 * k)
    H = int(110 * k) + row * len(items) + 20
    img, pad = ctx.card(W, H, radius=26, fill="#FFFFFF")
    d = ctx.ImageDraw.Draw(img)
    x = pad + 34
    tf = lambda red, kk: ctx.font(ctx.JS_RED if red else ctx.JS_SERIF_I, int((56 if red else 58) * kk))
    kt = k
    while kt > 0.4 and sum(tf(pt.get("s") == "red", kt).getlength(pt["t"]) + 14 for pt in p["title"]) > W - 68:
        kt -= 0.05  # a long title shrinks to fit the card
    for part in p["title"]:
        red = part.get("s") == "red"
        f = tf(red, kt)
        d.text((x, pad + 78 * k), part["t"], font=f, fill=ctx.rgba(JS["red"] if red else JS["ink"]), anchor="ls")
        x += f.getlength(part["t"]) + 14
    at = list(p["at"])
    f = ctx.font(ctx.JS_SERIF, int(36 * k))
    b = int(38 * k)
    for i, it in enumerate(items):
        t0 = at[i] if i < len(at) and at[i] is not None else 0.3 + i * p["gap"]
        y = pad + int(110 * k) + i * row
        bx = pad + 34
        d.rounded_rectangle([bx, y, bx + b, y + b], radius=6, outline=ctx.rgba("#555555"), width=3)
        if ctx.t >= t0:
            d.text((bx + b + 22, y + b * 0.85), ctx.typed_text(it, t0, p["cps"]), font=f, fill=ctx.rgba(JS["ink"]), anchor="ls")
            done = t0 + len(it) / p["cps"]
            if ctx.t >= done:  # the tick lands when the line is written
                d.rounded_rectangle([bx, y, bx + b, y + b], radius=6, fill=ctx.rgba(JS["check"]))
                ctx.check(d, bx + b / 2, y + b / 2 + 1, b * 0.8, fill="#FFFFFF", width=max(4, b // 8), progress=ctx.prog(done, 0.12))
    return img
