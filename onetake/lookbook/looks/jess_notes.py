META = {
    "name": "Class spiral-notebook notes",
    "description": "A white spiral notebook page: a collage title, then lesson notes written line by line as they're said; "
                   "wrap words in ==double equals== to highlight them with a yellow marker. Definitions, key takeaways, "
                   "a lesson summary. Put it on a 'class' screen (red page) or over the top half.",
    "params": {"title": "fund", "lines": ["What is a fund?", "A fund is money pooled together from many people",
                                          "Investment objective: the ==stated goal== of the fund"],
               "at": [], "gap": 1.2, "cps": 32, "width": 0.86, "height": 0.46},
}


def render(ctx):
    p, JS = ctx.p, ctx.JS
    W, H = int(ctx.W * p["width"]), int(ctx.H * p["height"])
    img, pad = ctx.card(W, H, radius=8, fill=JS["paper"])
    d = ctx.ImageDraw.Draw(img)
    for k in range(int(H / 46)):  # the spiral
        y = pad + 30 + k * 46
        d.ellipse([pad - 18, y, pad + 22, y + 22], outline=ctx.rgba("#222222"), width=5)
    pal = ["#E64FA8", "#F6C431", "#2E9E4F", "#6B3FD4", "#E04A3A"]
    x = pad + W / 2 - len(p["title"]) * 32
    for i, ch in enumerate(p["title"]):
        f = ctx.font([ctx.JS_RED, ctx.JS_SERIF_I, ctx.JS_CHALK][i % 3], 84)
        d.text((x, pad + 110), ch, font=f, fill=ctx.rgba(pal[i % len(pal)]), anchor="ls")
        x += f.getlength(ch) + 4
    at = list(p["at"])
    f = ctx.font(ctx.JS_SERIF, 38)
    y = pad + 170
    for i, ln in enumerate(p["lines"]):
        t0 = at[i] if i < len(at) and at[i] is not None else 0.3 + i * p["gap"]
        plain = ln.replace("==", "")
        wrapped = ctx.wrap(plain, f, W - 120)
        if ctx.t >= t0:
            shown = int((ctx.t - t0) * p["cps"])
            hl = []  # highlighted spans in plain-text positions
            pos, on, start = 0, False, 0
            for part in ln.split("=="):
                if on:
                    hl.append((pos, pos + len(part)))
                pos += len(part)
                on = not on
            off = 0
            for wl in wrapped:
                for a, b in hl:  # marker behind highlighted words, swiped in as they're written
                    s0, s1 = max(a, off), min(b, off + len(wl))
                    if s0 < s1 and shown > s0:
                        x0 = pad + 50 + f.getlength(wl[:s0 - off])
                        x1 = pad + 50 + f.getlength(wl[:min(s1, shown) - off])
                        d.rectangle([x0 - 4, y + 8, x1 + 4, y + 44], fill=ctx.rgba(JS["marker"]))
                n = max(0, min(len(wl), shown - off))
                d.text((pad + 50, y + 38), wl[:n], font=f, fill=ctx.rgba(JS["ink"] if i else JS["red"]), anchor="ls")
                off += len(wl) + 1
                y += 50
        else:
            y += 50 * len(wrapped)
        y += 10
    return img
