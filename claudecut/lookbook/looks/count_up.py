META = {
    "name": "Count-up card",
    "description": "A number that counts up, with a label underneath (e.g. 800+ members).",
    "params": {"to": 800, "from": 0, "prefix": "", "suffix": "+", "label": "people in my community",
               "accent": "#5B4BDB", "card": "#FFFFFF", "text_color": "#1B1B1F", "count_time": 1.4, "commas": True},
}


def render(ctx):
    p = ctx.p
    k = ctx.ease(min(1.0, ctx.t / max(0.1, min(p["count_time"], ctx.dur * 0.7))))
    n = int(round(p["from"] + (p["to"] - p["from"]) * k))
    num = f"{n:,}" if p["commas"] else str(n)
    num = f"{p['prefix']}{num}{p['suffix'] if k >= 1 else ''}"
    full = f"{p['prefix']}{p['to']:,}{p['suffix']}" if p["commas"] else f"{p['prefix']}{p['to']}{p['suffix']}"
    fn = ctx.font("Montserrat_900Black", 190)
    fl = ctx.font("Montserrat_700Bold", 46)
    label_lines = ctx.wrap(p["label"], fl, 640)
    w = int(max(fn.getlength(full), max((fl.getlength(l) for l in label_lines), default=0)) + 120)
    h = 250 + 58 * len(label_lines) + 50
    img = ctx.Image.new("RGBA", (w + 30, h + 30), (0, 0, 0, 0))
    d = ctx.ImageDraw.Draw(img)
    d.rounded_rectangle([18, 22, w + 18, h + 22], radius=42, fill=(0, 0, 0, 70))
    d.rounded_rectangle([6, 6, w, h], radius=42, fill=ctx.rgba(p["card"]))
    # a little pop each time the count lands
    d.text((w / 2 + 3, 150), num, font=fn, fill=ctx.rgba(p["accent"]), anchor="mm")
    for i, l in enumerate(label_lines):
        d.text((w / 2 + 3, 280 + i * 58), l, font=fl, fill=ctx.rgba(p["text_color"]), anchor="mm")
    return img
