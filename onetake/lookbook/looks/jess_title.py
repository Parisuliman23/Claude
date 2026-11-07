META = {
    "name": "Class title (serif + red caps)",
    "description": "Jess-style two-tone title: white serif italic words and big red rounded caps, each part typed on with an "
                   "underscore cursor the moment it's said. Hooks, keywords ('MUTUAL shared FUND'), 'Hi! I'm …', "
                   "'class is in SESSION', 'on the next LESSON…'. Optional school bell.",
    "params": {"parts": [{"t": "your first", "s": "serif"}, {"t": "INVESTMENT", "s": "red"}],
               "at": [], "gap": 0.25, "cps": 26, "size": 100, "align": "center", "width": 0.9, "bell": False,
               "cursor": True},
}
# parts: [{"t": text, "s": "serif" | "serif_up" | "red" | "white" | "small", "inline": true (same line as the previous)}]
# at: one time (or word cue {"w": i}) per part: each part types on as it's said.


def render(ctx):
    p, JS = ctx.p, ctx.JS
    parts = list(p["parts"])
    at = list(p["at"])
    sz = int(p["size"])
    FONTS = {"serif": (ctx.JS_SERIF_I, 0.72, "#FFFFFF"), "serif_up": (ctx.JS_SERIF, 0.6, "#FFFFFF"),
             "red": (ctx.JS_RED, 1.0, JS["red"]), "white": (ctx.JS_RED, 1.0, "#FFFFFF"),
             "small": (ctx.JS_SERIF, 0.36, "#FFFFFF")}
    lines, cur = [], []
    for i, part in enumerate(parts):
        fn, k, col = FONTS.get(part.get("s", "serif"), FONTS["serif"])
        f = ctx.font(fn, int(sz * k))
        t0 = at[i] if i < len(at) and at[i] is not None else i * p["gap"]
        item = (part["t"], f, col, t0)
        if part.get("inline") and cur:
            cur.append(item)
        else:
            if cur:
                lines.append(cur)
            cur = [item]
    if cur:
        lines.append(cur)
    maxw = ctx.W * p["width"]
    widths = [sum(f.getlength(t) for t, f, _, _ in ln) + 14 * (len(ln) - 1) for ln in lines]
    heights = [max(int(f.size * 0.92) for _, f, _, _ in ln) for ln in lines]
    W = int(min(maxw * 1.2, max(widths)) + 60)
    bell_h = int(sz * 1.1) if p["bell"] else 0
    H = sum(heights) + 50 + bell_h
    img = ctx.Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ctx.ImageDraw.Draw(img)
    y = 25 + bell_h
    if p["bell"]:
        import math
        sw = math.sin(ctx.t * 9) * 12 * max(0.0, 1 - ctx.t / 1.4)  # rings, then settles
        bx, by, r = W / 2, 10 + bell_h * 0.48, bell_h * 0.36
        bell = ctx.Image.new("RGBA", (int(r * 3), int(r * 3)), (0, 0, 0, 0))
        bd = ctx.ImageDraw.Draw(bell)
        c = r * 1.5
        bd.pieslice([c - r, c - r * 1.1, c + r, c + r * 0.9], 180, 360, fill=ctx.rgba("#F6C431"))
        bd.rectangle([c - r, c - r * 0.1, c + r, c + r * 0.45], fill=ctx.rgba("#F6C431"))
        bd.rounded_rectangle([c - r * 1.2, c + r * 0.35, c + r * 1.2, c + r * 0.6], radius=8, fill=ctx.rgba("#F9E9C8"))
        bd.ellipse([c - r * 0.18, c + r * 0.55, c + r * 0.18, c + r * 0.9], fill=ctx.rgba("#E04A3A"))
        bell = bell.rotate(sw, resample=ctx.Image.BICUBIC)
        img.alpha_composite(bell, (int(bx - bell.width / 2), int(by - bell.height / 2)))
    for ln, lw, lh in zip(lines, widths, heights):
        x = (W - lw) / 2 if p["align"] == "center" else 30
        for text, f, col, t0 in ln:
            shown = ctx.typed_text(text, t0, p["cps"], p["cursor"])
            d.text((x, y + lh * 0.86), shown, font=f, fill=ctx.rgba(col), anchor="ls")
            x += f.getlength(text) + 14
        y += lh
    return ctx.shadowed(img, blur=6, offset=3, alpha=110)
