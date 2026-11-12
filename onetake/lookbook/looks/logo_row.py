META = {
    "name": "Company logos (pop in on each name)",
    "description": "A row of white rounded tiles with company logos; each one pops in on the word it's said, with an "
                   "optional two-tone title above (e.g. 'BUY THE DIP' + 'OR DEAD MONEY?'). Logos come from "
                   "library/logos (python3 -m engine logo-find NVIDIA AMD Intel).",
    "params": {"companies": ["NVIDIA", "AMD", "Intel"], "logos": [], "at": [], "gap_at": 0.35,
               "title": "", "title_accent": "", "sub": "", "accent": "#F26A1B",
               "tile": 190, "tile_h": 0, "dark": [], "max_per_row": 5, "width": 0.94},
}
# companies: names in the order they're said. logos: optional file paths, same order (else library/logos/<name>.png).
# at: one time per logo, so each pops on its word, e.g. [{"w": 40}, {"w": 42}, {"w": 45}] (default: every gap_at s).
# dark: indexes of tiles drawn black (a logo that's white on dark, like Uber's app icon).


def _logo(ctx, name, path):
    from engine import logos
    f = path or logos.cached(name)
    if not f:
        return None
    try:
        return ctx.image(str(f))
    except Exception:  # noqa: BLE001
        return None


def render(ctx):
    p, t = ctx.p, ctx.t
    names = list(p["companies"])
    n = len(names)
    if not n:
        return None
    per = max(1, min(int(p["max_per_row"]), n))
    rows = (n + per - 1) // per
    gap = 18
    maxw = int(ctx.W * p["width"])
    tw = min(int(p["tile"]), (maxw - gap * (per - 1)) // per)
    th = int(p["tile_h"] or tw * 0.62)
    head = 0
    ft = fa = fs = None
    if p["title"] or p["title_accent"]:
        ft = ctx.font(ctx.LOUD, 76)
        head += 96
    if p["sub"]:
        fs = ctx.font("Montserrat_700Bold", 40)
        head += 62
    W = maxw
    H = head + rows * th + (rows - 1) * gap + 30
    img = ctx.Image.new("RGBA", (W + 40, H + 40), (0, 0, 0, 0))
    d = ctx.ImageDraw.Draw(img)
    y = 20
    if ft:  # two-tone title: white words, then the accent words
        a, b = p["title"].strip(), p["title_accent"].strip()
        wa = ft.getlength(a + (" " if a and b else ""))
        tot = wa + ft.getlength(b)
        s = min(1.0, W / max(1, tot))
        if s < 1:
            ft = ctx.font(ctx.LOUD, int(76 * s))
            wa = ft.getlength(a + (" " if a and b else ""))
            tot = wa + ft.getlength(b)
        x = 20 + (W - tot) / 2
        txt = ctx.Image.new("RGBA", img.size, (0, 0, 0, 0))
        td = ctx.ImageDraw.Draw(txt)
        td.text((x, y + 40), a, font=ft, fill=ctx.rgba("#FFFFFF"), anchor="lm")
        td.text((x + wa, y + 40), b, font=ft, fill=ctx.rgba(p["accent"]), anchor="lm")
        img.alpha_composite(ctx.shadowed(txt, blur=5, offset=2, alpha=150).crop((18, 18, 18 + img.width, 18 + img.height)))
        y += 96
    if fs:
        sub = ctx.Image.new("RGBA", img.size, (0, 0, 0, 0))
        ctx.ImageDraw.Draw(sub).text((20 + W / 2, y + 26), p["sub"], font=fs, fill=ctx.rgba("#FFFFFF"), anchor="mm")
        img.alpha_composite(ctx.shadowed(sub, blur=4, offset=2, alpha=150).crop((18, 18, 18 + img.width, 18 + img.height)))
        y += 62
    times = list(p["at"]) if p["at"] else []
    paths = list(p["logos"])
    for i, name in enumerate(names):
        t0 = times[i] if i < len(times) and isinstance(times[i], (int, float)) else i * float(p["gap_at"])
        k = (t - t0) / 0.28
        if k <= 0:
            continue
        s = ctx.ease_back(min(1.0, k))  # pop: overshoot, then settle
        r, c = divmod(i, per)
        in_row = min(per, n - r * per)
        rx = 20 + (W - (in_row * tw + (in_row - 1) * gap)) / 2
        cx = rx + c * (tw + gap) + tw / 2
        cy = y + r * (th + gap) + th / 2
        dark = i in p["dark"]
        tile, pad = ctx.card(tw, th, radius=max(10, th // 7), fill="#111111" if dark else "#FFFFFF")
        lg = _logo(ctx, name, paths[i] if i < len(paths) else None)
        td = ctx.ImageDraw.Draw(tile)
        if lg is not None:
            lg = lg.convert("RGBA")
            px = [(r_, g_, b_) for r_, g_, b_, a_ in lg.resize((40, 40)).getdata() if a_ > 128]
            lum = sum(0.3 * r_ + 0.59 * g_ + 0.11 * b_ for r_, g_, b_ in px) / len(px) if px else 128
            if (dark and lum < 110) or (not dark and lum > 225):  # black logo on a black tile / white on white
                solid = ctx.Image.new("RGBA", lg.size, (255, 255, 255, 255) if dark else (17, 17, 17, 255))
                solid.putalpha(lg.getchannel("A"))
                lg = solid
            sc = min((tw * 0.78) / lg.width, (th * 0.62) / lg.height)
            lg = lg.resize((max(1, int(lg.width * sc)), max(1, int(lg.height * sc))), ctx.Image.LANCZOS)
            tile.alpha_composite(lg, (pad + (tw - lg.width) // 2, pad + (th - lg.height) // 2))
        else:  # no logo file: the name as a wordmark
            f = ctx.font(ctx.SANS_X, 44)
            if f.getlength(name) > tw * 0.84:
                f = ctx.font(ctx.SANS_X, max(18, int(44 * tw * 0.84 / f.getlength(name))))
            td.text((pad + tw / 2, pad + th / 2), name, font=f, fill=ctx.rgba("#FFFFFF" if dark else "#111111"), anchor="mm")
        if s < 0.999 or s > 1.001:
            tile = tile.resize((max(1, int(tile.width * s)), max(1, int(tile.height * s))), ctx.Image.LANCZOS)
        img.alpha_composite(tile, (int(cx - tile.width / 2), int(cy - tile.height / 2)))
    return img
