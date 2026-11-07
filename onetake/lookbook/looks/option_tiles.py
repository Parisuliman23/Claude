META = {
    "name": "Option tiles",
    "description": "A row of small white tiles hanging from a line (like a menu of choices), each with a line icon and a "
                   "bold label, appearing one after another. 'pick' turns one yellow. Optional handwritten line underneath.",
    "params": {"tiles": [{"icon": "smile", "label": "talking head"}, {"icon": "pages", "label": "carousel"},
                         {"icon": "mic", "label": "voiceover"}, {"icon": "film", "label": "B-roll"},
                         {"icon": "photos", "label": "photo dump"}],
               "appear_gap": 0.25, "appear_at": [], "pick": -1, "pick_at": 0.0, "under": "same idea → the format that fits it best",
               "under_at": 1.5, "width": 0.74},
}


def render(ctx):
    p, NB = ctx.p, ctx.NB
    tiles = list(p["tiles"])
    W = int(ctx.W * p["width"])
    gap, th, top = 14, 150, 40
    n = len(tiles)
    tw = (W - gap * (n - 1)) / n
    pad = 24
    under_h = 70 if p["under"] else 0
    img = ctx.Image.new("RGBA", (W + pad * 2, top + th + under_h + pad * 2), (0, 0, 0, 0))
    d = ctx.ImageDraw.Draw(img)
    ink = ctx.rgba(NB["ink"])
    y_line = pad + 8
    d.line([(pad + 6, y_line), (pad + W - 6, y_line)], fill=ink, width=3)  # the rail
    for ex in (pad + 6, pad + W - 6):
        d.ellipse([ex - 7, y_line - 7, ex + 7, y_line + 7], fill=ctx.rgba(NB["gold"]), outline=ink, width=2)
    for i, tile in enumerate(tiles):
        ap = list(p["appear_at"])
        a = ctx.appear(ap[i] if i < len(ap) and ap[i] is not None else i * p["appear_gap"], 0.12)
        if a <= 0:
            continue
        x = pad + i * (tw + gap)
        picked = i == p["pick"] and ctx.t >= p["pick_at"]
        layer = ctx.Image.new("RGBA", img.size, (0, 0, 0, 0))
        layer.alpha_composite(ctx.shadows(img.size, [(x, pad + top, x + tw, pad + top + th)], blur=6, alpha=70, dy=6))
        ld = ctx.ImageDraw.Draw(layer)
        ld.line([(x + tw / 2, y_line), (x + tw / 2, pad + top)], fill=ink, width=2)
        ld.rounded_rectangle([x, pad + top, x + tw, pad + top + th], radius=8, fill=ctx.rgba(NB["yellow"] if picked else NB["white"]))
        ld.ellipse([x + tw / 2 - 11, pad + top + 10, x + tw / 2 + 11, pad + top + 32], outline=ctx.rgba(NB["faint"]), width=2)
        if tile.get("icon"):  # one of ctx.ICONS (line icons), or an emoji code like "1f4b0"
            if tile["icon"] in ctx.ICONS:
                ctx.icon(ld, tile["icon"], x + tw / 2, pad + top + 72, 40)
            else:
                em = ctx.emoji(tile["icon"])
                if em is not None:
                    layer.alpha_composite(em.resize((52, 52)), (int(x + tw / 2 - 26), pad + top + 46))
        ld.text((x + tw / 2, pad + top + th - 22), tile.get("label", ""), font=ctx.font(ctx.NB_BOLD, 23), fill=ink, anchor="ms")
        img.alpha_composite(ctx.faded(layer, a))
    if p["under"] and ctx.t >= p["under_at"]:
        d = ctx.ImageDraw.Draw(img)
        ctx.hand(d, (pad + W / 2, pad + top + th + 56), p["under"], 32, chars=(ctx.t - p["under_at"]) * 30,
                 anchor="ms", fill=NB["ink"])
    return img
