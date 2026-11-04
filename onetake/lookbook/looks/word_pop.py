import math

META = {
    "name": "Word pop",
    "description": "One big word on a colored sticker that wobbles gently.",
    "params": {"text": "WOW", "bg": "#FF5A8A", "color": "#FFFFFF", "font": "Montserrat_900Black", "size": 130,
               "wobble": 4},
}


def render(ctx):
    p = ctx.p
    text = p["text"].upper()
    size = p["size"]
    f = ctx.font(p["font"], size)
    while f.getlength(text) > ctx.W * 0.8 and size > 40:  # shrink long phrases to fit
        size -= 6
        f = ctx.font(p["font"], size)
    tw, th = ctx.text_size(text, f)
    w, h = int(tw + size * 0.85), int(size * 1.5)
    img = ctx.Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ctx.ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2, fill=ctx.rgba(p["bg"]))
    d.text((w / 2, h / 2), text, font=f, fill=ctx.rgba(p["color"]), anchor="mm")
    return img.rotate(math.sin(ctx.t * 5) * p["wobble"], resample=ctx.Image.BICUBIC, expand=True)
