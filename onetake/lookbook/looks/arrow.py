META = {
    "name": "Hand-drawn arrow",
    "description": "A curved arrow that draws on (~0.6 s, ease-out) to lead the eye: down, down-left, down-right, up-right, right.",
    "params": {"dir": "down", "size": 300, "width": 9, "color": "#FFFFFF", "draw_time": 0.6},
}

PATHS = {
    "down": ((0.5, 0.0), (0.62, 0.5), (0.5, 1.0)),
    "down-left": ((0.85, 0.0), (0.8, 0.8), (0.1, 0.95)),
    "down-right": ((0.15, 0.0), (0.2, 0.8), (0.9, 0.95)),
    "up-right": ((0.1, 1.0), (0.2, 0.2), (0.9, 0.05)),
    "right": ((0.0, 0.6), (0.5, 0.1), (1.0, 0.5)),
}


def render(ctx):
    p = ctx.p
    S = p["size"]
    img = ctx.Image.new("RGBA", (S, S), (0, 0, 0, 0))
    a, b, c = [(x * (S - 40) + 20, y * (S - 40) + 20) for x, y in PATHS.get(p["dir"], PATHS["down"])]
    ctx.curve(ctx.ImageDraw.Draw(img), a, b, c, ctx.ease(min(1, ctx.t / p["draw_time"])), width=p["width"], fill=p["color"])
    return ctx.shadowed(img)
