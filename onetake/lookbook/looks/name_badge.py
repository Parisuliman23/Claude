META = {
    "name": "Name / logo badge",
    "description": "NAME a person, brand or account the moment it's said: white rounded badge with optional photo/logo (library image), name and a small line. Pops; repeat when said again.",
    "params": {"name": "Replit", "sub": "", "image": "", "verified": False, "size": 52},
}


def render(ctx):
    p = ctx.p
    f = ctx.font(ctx.SANS_X, p["size"])
    fs = ctx.font(ctx.SANS, int(p["size"] * 0.6))
    av = int(p["size"] * 1.9) if p["image"] else 0
    tw = max(f.getlength(p["name"]) + (p["size"] if p["verified"] else 0), fs.getlength(p["sub"]) if p["sub"] else 0)
    w = int(tw + av + (40 if av else 0) + 70)
    h = int(max(av, p["size"] * (2.2 if p["sub"] else 1.4)) + 36)
    card, pad = ctx.card(w, h, radius=min(30, h // 2))
    d = ctx.ImageDraw.Draw(card)
    x = pad + 30
    if p["image"]:
        im = ctx.image(p["image"])
        if im is not None:
            s = av
            im = im.copy()
            r = max(s / im.width, s / im.height)
            im = im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))))
            im = im.crop(((im.width - s) // 2, (im.height - s) // 2, (im.width - s) // 2 + s, (im.height - s) // 2 + s))
            mask = ctx.Image.new("L", (s, s), 0)
            ctx.ImageDraw.Draw(mask).ellipse([0, 0, s - 1, s - 1], fill=255)
            card.paste(im, (x, pad + (h - s) // 2), mask)
        x += av + 24
    cy = pad + h / 2
    if p["sub"]:
        d.text((x, cy - 4), p["name"], font=f, fill=(20, 20, 24, 255), anchor="ls")
        d.text((x, cy + 8), p["sub"], font=fs, fill=(110, 110, 120, 255), anchor="lt")
    else:
        d.text((x, cy), p["name"], font=f, fill=(20, 20, 24, 255), anchor="lm")
    if p["verified"]:
        vx = x + f.getlength(p["name"]) + p["size"] * 0.55
        vy = cy - (p["size"] * 0.4 if p["sub"] else 0)
        r = p["size"] * 0.32
        d.ellipse([vx - r, vy - r, vx + r, vy + r], fill=(30, 144, 255, 255))
        d.line([(vx - r * 0.45, vy), (vx - r * 0.1, vy + r * 0.35), (vx + r * 0.5, vy - r * 0.35)], fill=(255, 255, 255, 255), width=4)
    return card
