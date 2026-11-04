META = {
    "name": "Hook title",
    "description": "Big bold block text for the first seconds of the reel.",
    "group": "hook",
    "params": {"text": "Your hook here", "bg": "#FFE14D", "color": "#111111", "font": "Montserrat_900Black",
               "size": 78, "uppercase": True, "tilt": -2.5, "width": 0.84},
}


def render(ctx):
    p = ctx.p
    text = p["text"].upper() if p["uppercase"] else p["text"]
    f = ctx.font(p["font"], p["size"])
    lines = ctx.wrap(text, f, ctx.W * p["width"] - 60)
    lh = int(p["size"] * 1.22)
    widths = [f.getlength(l) for l in lines]
    W = int(max(widths) + 80)
    H = lh * len(lines) + 40
    img = ctx.Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ctx.ImageDraw.Draw(img)
    for i, (l, w) in enumerate(zip(lines, widths)):
        x0 = (W - w) / 2 - 22
        y0 = 20 + i * lh
        d.rounded_rectangle([x0, y0, x0 + w + 44, y0 + lh - 6], radius=14, fill=ctx.rgba(p["bg"]))
        d.text((W / 2, y0 + lh / 2 - 2), l, font=f, fill=ctx.rgba(p["color"]), anchor="mm")
    if p["tilt"]:
        img = img.rotate(p["tilt"], resample=ctx.Image.BICUBIC, expand=True)
    return img
