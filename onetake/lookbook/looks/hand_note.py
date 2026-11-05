META = {
    "name": "Handwritten note",
    "description": "A paraphrase or aside in handwriting that types on (~22 letters/s), optional curved arrow. _underline_ words; start/end with ... to carry a sentence across cards.",
    "params": {"text": "I can't speak to any of the other launches...", "cps": 22, "size": 64, "width": 0.7,
               "font": "NanumPenScript_400Regular", "color": "#FFFFFF", "cursor": True,
               "arrow": "none", "arrow_color": "#FFFFFF"},
}

ARROWS = {  # start, bend, end (fractions of a 300x260 box)
    "down": ((0.5, 0.0), (0.62, 0.5), (0.5, 1.0)),
    "down-left": ((0.8, 0.0), (0.75, 0.75), (0.15, 0.95)),
    "down-right": ((0.2, 0.0), (0.25, 0.75), (0.85, 0.95)),
    "up-right": ((0.1, 1.0), (0.2, 0.2), (0.9, 0.05)),
    "right": ((0.0, 0.6), (0.5, 0.1), (1.0, 0.5)),
}


def render(ctx):
    p = ctx.p
    note = ctx.write(p["text"], p["font"], p["size"], ctx.W * p["width"], chars=int(ctx.t * p["cps"]),
                     fill=p["color"], cursor=p["cursor"])
    arrow = None
    if p["arrow"] in ARROWS:
        aw, ah = 300, 260
        arrow = ctx.Image.new("RGBA", (aw, ah), (0, 0, 0, 0))
        d = ctx.ImageDraw.Draw(arrow)
        start = ctx.typed_done(p["text"], p["cps"])
        (a, b, c) = [(x * (aw - 30) + 15, y * (ah - 30) + 15) for x, y in ARROWS[p["arrow"]]]
        ctx.curve(d, a, b, c, ctx.ease(min(1, max(0, ctx.t - start) / 0.6)), width=7, fill=p["arrow_color"])
    return ctx.shadowed(ctx.stack([note, arrow], gap=0))
