META = {
    "name": "Emoji row",
    "description": "FEEL: a row of emoji above the head that pop in one after another (e.g. 🤯😳😳).",
    "params": {"emojis": ["1f92f", "1f633", "1f633"], "size": 120, "stagger": 0.12},
}


def render(ctx):
    p = ctx.p
    S, n = p["size"], len(p["emojis"])
    img = ctx.Image.new("RGBA", (int(S * n + 10 * (n - 1)), S), (0, 0, 0, 0))
    for i, code in enumerate(p["emojis"]):
        t0 = i * p["stagger"]
        if ctx.t < t0:
            continue
        try:
            e = ctx.emoji(code)
        except Exception:
            continue
        k = 0.4 + 0.6 * ctx.ease(min(1, (ctx.t - t0) / 0.1))
        s = max(1, int(S * k))
        e = e.resize((s, s))
        img.alpha_composite(e, (int(i * (S + 10) + (S - s) / 2), int((S - s) / 2)))
    return img
