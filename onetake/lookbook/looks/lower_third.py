META = {
    "name": "Lower third",
    "description": "A name/title bar that wipes in — good for introducing yourself or a topic.",
    "params": {"title": "Your Name", "subtitle": "what you do", "accent": "#5B4BDB", "bg": "#FFFFFF",
               "color": "#1B1B1F"},
}


def render(ctx):
    p = ctx.p
    ft = ctx.font("Montserrat_900Black", 64)
    fs = ctx.font("Montserrat_600SemiBold", 40)
    w = int(max(ft.getlength(p["title"]), fs.getlength(p["subtitle"])) + 110)
    h = 190
    k = ctx.ease(min(1.0, ctx.t / 0.5))
    img = ctx.Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ctx.ImageDraw.Draw(img)
    vis = int(w * k)
    d.rounded_rectangle([0, 0, max(30, vis), h - 1], radius=24, fill=ctx.rgba(p["bg"]))
    d.rectangle([0, 0, 18, h - 1], fill=ctx.rgba(p["accent"]))
    if k > 0.6:
        d.text((50, 70), p["title"], font=ft, fill=ctx.rgba(p["color"]), anchor="lm")
        d.text((52, 140), p["subtitle"], font=fs, fill=ctx.rgba(p["accent"]), anchor="lm")
    return img
