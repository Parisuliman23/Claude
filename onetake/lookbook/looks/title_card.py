META = {
    "name": "Intro title card",
    "description": "A calm intro lockup over a dark wash: a small kicker fades up, the title settles in the centre with "
                   "one restrained move, a hairline rule draws left to right, and a label fades in beneath.",
    "params": {"kicker": "EPISODE 03", "title": "The Debt Reset", "label": "how I paid off $50k", "wash": 0.55,
               "accent": "#F5C542", "serif": True},
}


def render(ctx):
    p = ctx.p
    W, H = ctx.W, int(ctx.H * 0.5)
    img = ctx.Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if p["wash"]:  # soft dark band so the title reads over the video
        import numpy as np
        y = np.linspace(-1, 1, H)
        a = (np.clip(1 - y ** 2, 0, 1) * 255 * p["wash"] * min(1.0, ctx.t / 0.3)).astype("uint8")
        band = np.zeros((H, W, 4), "uint8")
        band[..., 3] = a[:, None]
        img = ctx.Image.fromarray(band, "RGBA")
    d = ctx.ImageDraw.Draw(img)
    white = ctx.rgba("#FFFFFF")
    cx, cy = W / 2, H / 2
    if p["kicker"]:
        k = ctx.p3(ctx.prog(0.0, 0.4))
        d.text((cx, cy - 120 + (1 - k) * 20), p["kicker"], font=ctx.font(ctx.MO_SEMI, 30),
               fill=ctx.rgba(p["accent"])[:3] + (int(255 * k),), anchor="ms")
    k = ctx.p3(ctx.prog(0.25, 0.6))
    tf = ctx.font(ctx.NB_SERIF if p["serif"] else ctx.MO_BLACK, 118 if p["serif"] else 104)
    title = ctx.Image.new("RGBA", (W, 200), (0, 0, 0, 0))
    ctx.ImageDraw.Draw(title).text((W / 2, 150), p["title"], font=tf, fill=white, anchor="ms")
    s = 1.06 - 0.06 * k
    title = title.resize((int(W * s), int(200 * s)))
    img.alpha_composite(ctx.faded(title, k), (int((W - title.width) / 2), int(cy - 120 - (title.height - 200) / 2)))
    r = ctx.inout(ctx.prog(0.7, 0.5))
    if r > 0:
        L = 360
        d.line([(cx - L / 2, cy + 52), (cx - L / 2 + L * r, cy + 52)], fill=ctx.rgba(p["accent"]), width=3)
    if p["label"]:
        k = ctx.p3(ctx.prog(1.0, 0.4))
        d.text((cx, cy + 110), p["label"], font=ctx.font(ctx.MO_SEMI, 36), fill=white[:3] + (int(255 * k),), anchor="ms")
    return img
