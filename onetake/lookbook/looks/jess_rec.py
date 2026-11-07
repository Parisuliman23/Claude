META = {
    "name": "Camcorder frame (REC)",
    "description": "A camcorder viewfinder over the speaker: corner brackets, a blinking red REC dot and a battery icon. "
                   "Asides like 'but that's a video for another day' or 'I'll explain'.",
    "params": {"label": "REC", "width": 0.86, "height": 0.42},
}


def render(ctx):
    p = ctx.p
    W, H = int(ctx.W * p["width"]), int(ctx.H * p["height"])
    img = ctx.Image.new("RGBA", (W + 20, H + 20), (0, 0, 0, 0))
    d = ctx.ImageDraw.Draw(img)
    d.rectangle([10, 10, W + 10, H + 10], outline=(0, 0, 0, 230), width=26)  # the camera body edge
    L, w = 60, 7
    for x, y, dx, dy in ((40, 40, 1, 1), (W - 20, 40, -1, 1), (40, H - 20, 1, -1), (W - 20, H - 20, -1, -1)):
        d.line([(x, y), (x + dx * L, y)], fill=(255, 255, 255, 255), width=w)
        d.line([(x, y), (x, y + dy * L)], fill=(255, 255, 255, 255), width=w)
    if int(ctx.t * 2) % 2 == 0:
        d.ellipse([W - 150, 58, W - 122, 86], fill=ctx.rgba("#E52421"))
    d.text((W - 110, 82), p["label"], font=ctx.font("Inter_800ExtraBold", 30), fill=(255, 255, 255, 255), anchor="ls")
    d.rounded_rectangle([60, 58, 120, 86], radius=4, outline=(255, 255, 255, 255), width=4)
    d.rectangle([66, 64, 104, 80], fill=ctx.rgba("#47D16C"))
    return img
