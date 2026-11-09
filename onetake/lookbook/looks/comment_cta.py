META = {
    "name": "Comment keyword card",
    "description": "A yellow sticky card: small 'comment', the KEYWORD huge in serif italic, and what they get underneath.",
    "params": {"top": "comment", "keyword": "BOARD", "sub": "for my board template", "width": 0.37},
}


def render(ctx):
    p, NB = ctx.p, ctx.NB
    W = int(ctx.W * p["width"])
    f = ctx.font(ctx.NB_SERIF, 112)
    while f.getlength(p["keyword"]) > W - 40 and f.size > 40:
        f = ctx.font(ctx.NB_SERIF, f.size - 4)
    H = 64 + f.size + 50
    img, pad = ctx.card(W, H, radius=4, fill=NB["sticky"])
    d = ctx.ImageDraw.Draw(img)
    ink = ctx.rgba(NB["ink"])
    d.text((pad + W / 2, pad + 44), p["top"], font=ctx.font(ctx.NB_BOLD, 28), fill=ink, anchor="ms")
    d.text((pad + W / 2, pad + 44 + f.size * 0.95), p["keyword"], font=f, fill=ink, anchor="ms")
    d.text((pad + W / 2, pad + H - 20), p["sub"], font=ctx.font(ctx.NB_SEMI, 21), fill=ink, anchor="ms")
    return img
