META = {
    "name": "Class 'today's lesson' notebook",
    "description": "A black-and-white marbled composition notebook under a serif 'today's lesson:' line; the topic is "
                   "written on its label in purple handwriting with a collage of cut-out letters. Use right after the "
                   "intro, on 'today's lesson / topic'.",
    "params": {"kicker": "today's lesson:", "word": "investing", "topic": "How to automate investing", "write_at": 0.35,
               "size": 0.62},
}


def render(ctx):
    import math
    p, JS = ctx.p, ctx.JS
    W = int(ctx.W * p["size"])
    H = int(W * 1.3)
    out = ctx.Image.new("RGBA", (W + 120, H + 230), (0, 0, 0, 0))
    od = ctx.ImageDraw.Draw(out)
    od.text((out.width / 2, 92), p["kicker"], font=ctx.font(ctx.JS_SERIF_I, 76), fill=ctx.rgba("#FFFFFF"), anchor="ms")
    cover = ctx.Image.new("RGBA", (W, H), (20, 20, 20, 255))
    cd = ctx.ImageDraw.Draw(cover)
    for k in range(900):  # the marbled cover, seeded
        x = (math.sin(k * 12.9898) * 43758.5453) % 1 * W
        y = (math.sin(k * 78.233) * 12345.678) % 1 * H
        r = 3 + (k * 13) % 16
        cd.ellipse([x - r, y - r * 0.6, x + r, y + r * 0.6], fill=(235, 235, 235, 255) if k % 3 else (120, 120, 120, 255))
    lx0, ly0, lx1, ly1 = W * 0.12, H * 0.14, W * 0.88, H * 0.44
    cd.rounded_rectangle([lx0, ly0, lx1, ly1], radius=10, fill=ctx.rgba("#FFFFFF"), outline=ctx.rgba("#111111"), width=3)
    cd.text(((lx0 + lx1) / 2, ly0 + 46), "COMPOSITION BOOK", font=ctx.font(ctx.JS_RED, 30), fill=ctx.rgba("#111111"), anchor="ms")
    for k in range(3):
        cd.line([(lx0 + 20, ly0 + 90 + k * 46), (lx1 - 20, ly0 + 90 + k * 46)], fill=ctx.rgba("#9BB7D4"), width=2)
    t = ctx.t - p["write_at"]
    if t > 0:
        ctx.hand(cd, ((lx0 + lx1) / 2, ly0 + 128), p["topic"], 34, chars=t * 26, fill=JS["purple"], anchor="ms", track=0.02)
    # collage word: each letter cut from a different "magazine"
    word = p["word"]
    if t > 0.3 and word:
        fonts = [ctx.JS_RED, ctx.JS_SERIF_I, ctx.JS_CHALK, ctx.NB_HAND, "Montserrat_900Black"]
        pal = ["#E64FA8", "#F6C431", "#2E9E4F", "#6B3FD4", "#E04A3A", "#7FC3F0"]
        n = min(len(word), int((t - 0.3) * 14) + 1)
        x = W * 0.08
        for i, ch in enumerate(word[:n]):
            f = ctx.font(fonts[i % len(fonts)], int(W * 0.14))
            cw = f.getlength(ch) + 16
            tile = ctx.Image.new("RGBA", (int(cw), int(W * 0.19)), ctx.rgba(pal[(i + 2) % len(pal)]))
            ctx.ImageDraw.Draw(tile).text((8, W * 0.15), ch, font=f, fill=ctx.rgba(pal[i % len(pal)] if i % 2 else "#FFFFFF"), anchor="ls")
            tile = tile.rotate(((i * 37) % 13) - 6, expand=True, resample=ctx.Image.BICUBIC)
            cover.alpha_composite(tile, (int(x), int(H * 0.52 + ((i * 53) % 30))))
            x += cw * 0.88
    sh = ctx.shadows(out.size, [(60, 150, 60 + W, 150 + H)], radius=10, blur=12, alpha=120, dy=10)
    out.alpha_composite(sh)
    rot = cover.rotate(-3, expand=True, resample=ctx.Image.BICUBIC)
    out.alpha_composite(rot, (int(60 - (rot.width - W) / 2), 150))
    return out
