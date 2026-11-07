META = {
    "name": "Lower third (name bar)",
    "description": "A clean name bar: a white block slides open, the name and role fade in, and an accent underline "
                   "draws beneath. For introducing yourself, a guest, a company or a source.",
    "params": {"name": "Your Name", "role": "Debt-free coach", "accent": "#F5C542", "open_at": 0.0, "dark": False},
}


def render(ctx):
    p, MO = ctx.p, ctx.MO
    nf, rf = ctx.font(ctx.MO_BOLD, 46), ctx.font(ctx.MO_SEMI, 30)
    W = int(max(nf.getlength(p["name"]), rf.getlength(p["role"])) + 80)
    H = 150
    img = ctx.Image.new("RGBA", (W + 40, H + 40), (0, 0, 0, 0))
    k = ctx.p3(ctx.prog(p["open_at"], 0.4))
    if k <= 0:
        return None
    bg = "#111827" if p["dark"] else "#FFFFFF"
    ink = "#FFFFFF" if p["dark"] else MO["ink"]
    sh = ctx.shadows(img.size, [(20, 20, 20 + W * k, 20 + H - 14)], radius=10, blur=8, alpha=70)
    img.alpha_composite(sh)
    d = ctx.ImageDraw.Draw(img)
    d.rounded_rectangle([20, 20, 20 + W * k, 20 + H - 14], radius=10, fill=ctx.rgba(bg))
    t = ctx.p3(ctx.prog(p["open_at"] + 0.25, 0.35))
    if t > 0:
        d.text((52, 84), p["name"], font=nf, fill=ctx.rgba(ink)[:3] + (int(255 * t),), anchor="ls")
        d.text((52, 126), p["role"], font=rf, fill=ctx.rgba(MO["muted"] if not p["dark"] else "#CBD5E1")[:3] + (int(255 * t),), anchor="ls")
    u = ctx.inout(ctx.prog(p["open_at"] + 0.35, 0.45))
    if u > 0:
        d.rectangle([20, 20 + H - 14, 20 + W * u, 20 + H - 6], fill=ctx.rgba(p["accent"]))
    return img
