META = {
    "name": "Cut-out sticker",
    "description": "Any image as a cut-out sticker: thick white outline, soft shadow, pops in with a little overshoot "
                   "and tilt. Memes, reaction faces, objects (apples, coffee cups, a bell), illustrations. Transparent "
                   "PNGs get a true die-cut outline.",
    "params": {"src": "assets/placeholder.png", "size": 0.42, "rot": -6, "at": 0.0, "outline": 14},
}


def render(ctx):
    p = ctx.p
    k = ctx.prog(p["at"], 0.22)
    if k <= 0:
        return None
    img = ctx.image(p["src"])
    if img is None:
        return None
    W = int(ctx.W * p["size"])
    img = img.resize((W, max(1, int(img.height * W / img.width))))
    o = int(p["outline"])
    a = img.getchannel("A")
    if a.getextrema()[0] == 255:  # no transparency: a rounded white border instead
        canvas = ctx.Image.new("RGBA", (img.width + 2 * o, img.height + 2 * o), (0, 0, 0, 0))
        ctx.ImageDraw.Draw(canvas).rounded_rectangle([0, 0, canvas.width - 1, canvas.height - 1], radius=o * 2, fill=(255, 255, 255, 255))
        canvas.alpha_composite(img, (o, o))
    else:
        canvas = ctx.Image.new("RGBA", (img.width + 2 * o, img.height + 2 * o), (0, 0, 0, 0))
        big = ctx.Image.new("L", canvas.size, 0)
        big.paste(a, (o, o))
        halo = big.filter(ctx.ImageFilter.MaxFilter(o * 2 + 1 if o * 2 + 1 <= 31 else 31))
        white = ctx.Image.new("RGBA", canvas.size, (255, 255, 255, 255))
        white.putalpha(halo)
        canvas.alpha_composite(white)
        canvas.alpha_composite(img, (o, o))
    s = ctx.ease_back(k) if k < 1 else 1.0
    out = canvas.rotate(p["rot"] * (2 - s), expand=True, resample=ctx.Image.BICUBIC)
    if s != 1:
        out = out.resize((max(1, int(out.width * s)), max(1, int(out.height * s))))
    return ctx.shadowed(out, blur=10, offset=6, alpha=120)
