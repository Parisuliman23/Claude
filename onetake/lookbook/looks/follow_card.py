META = {
    "name": "Follow card (CTA)",
    "description": "A dark profile card with your photo, name and @handle; a cursor glides in and clicks Follow, which "
                   "turns into Following. Put your own photo in library/images and set 'photo'.",
    "params": {"name": "Your Name", "handle": "@yourhandle", "photo": "", "click_at": 0.8, "width": 0.6},
}


def render(ctx):
    p, NB = ctx.p, ctx.NB
    W, H = int(ctx.W * p["width"]), 150
    img, pad = ctx.card(W, H, radius=16, fill=NB["navy"])
    d = ctx.ImageDraw.Draw(img)
    cx, cy, r = pad + 80, pad + H / 2, 52
    ring = ctx.Image.new("RGBA", img.size, (0, 0, 0, 0))
    rd = ctx.ImageDraw.Draw(ring)
    for k, col in enumerate(("#F58529", "#DD2A7B", "#8134AF")):  # story ring
        rd.arc([cx - r - 6, cy - r - 6, cx + r + 6, cy + r + 6], 120 * k - 90, 120 * k + 30, fill=col, width=6)
    img.alpha_composite(ring)
    photo = ctx.image(p["photo"]) if p["photo"] else None
    if photo is not None:
        s = min(photo.size)
        ph = photo.crop(((photo.width - s) // 2, (photo.height - s) // 2, (photo.width + s) // 2, (photo.height + s) // 2)).resize((2 * r, 2 * r))
        mask = ctx.Image.new("L", ph.size, 0)
        ctx.ImageDraw.Draw(mask).ellipse([0, 0, 2 * r - 1, 2 * r - 1], fill=255)
        img.paste(ph, (int(cx - r), int(cy - r)), mask)
    else:
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ctx.rgba("#3A4A63"))
        d.text((cx, cy), (p["name"][:1] or "?").upper(), font=ctx.font(ctx.NB_BOLD, 48), fill=ctx.rgba("#FFFFFF"), anchor="mm")
    bw, bh = 190, 52
    bx, by = pad + W - bw - 24, cy - bh / 2
    room = bx - (cx + r + 24) - 16  # name and handle shrink to fit left of the button
    fn, fh = ctx.font(ctx.NB_SEMI, 30), ctx.font(ctx.NB_LABEL, 23)
    while max(fn.getlength(p["name"]), fh.getlength(p["handle"])) > room and fh.size > 14:
        fn, fh = ctx.font(ctx.NB_SEMI, fn.size - 1), ctx.font(ctx.NB_LABEL, fh.size - 1)
    d.text((cx + r + 24, cy - 4), p["name"], font=fn, fill=ctx.rgba("#FFFFFF"), anchor="ls")
    d.text((cx + r + 24, cy + 30), p["handle"], font=fh, fill=ctx.rgba("#9AA3B2"), anchor="ls")
    clicked = ctx.t >= p["click_at"]
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=10, fill=ctx.rgba("#2D3A52" if clicked else "#3B82F6"))
    d.text((bx + bw / 2, cy + 1), "Following" if clicked else "Follow", font=ctx.font(ctx.NB_SEMI, 25),
           fill=ctx.rgba("#FFFFFF"), anchor="mm")
    # the cursor glides from the lower right onto the button, presses, and stays
    k = ctx.ease(max(0.0, min(1.0, (ctx.t - (p["click_at"] - 0.5)) / 0.45)))
    if ctx.t >= p["click_at"] - 0.5:
        tx, ty = bx + bw * 0.62, cy + 6
        mx, my = tx + (1 - k) * 160, ty + (1 - k) * 120
        s = 0.9 if p["click_at"] <= ctx.t < p["click_at"] + 0.12 else 1.0
        arrow = [(0, 0), (0, 42), (11, 32), (19, 50), (27, 46), (19, 29), (33, 29)]
        pts = [(mx + x * s, my + y * s) for x, y in arrow]
        d.polygon(pts, fill=ctx.rgba("#FFFFFF"), outline=ctx.rgba("#111111"), width=3)
    return img
