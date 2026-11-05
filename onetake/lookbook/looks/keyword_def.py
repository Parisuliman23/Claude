META = {
    "name": "Keyword = definition",
    "description": "\"BE CLEAR =\" in heavy caps (pops), then the definition types on in handwriting, in the viewer's inner voice.",
    "params": {"keyword": "BE CLEAR", "definition": "i need to understand what you're trying to say to me",
               "size": 54, "def_size": 62, "cps": 24, "width": 0.78, "color": "#FFFFFF"},
}


def render(ctx):
    p = ctx.p
    head = ctx.write(p["keyword"].rstrip(" =") + " =", ctx.LOUD, p["size"], ctx.W * p["width"], fill=p["color"], upper=True)
    body = ctx.write(p["definition"], ctx.HAND, p["def_size"], ctx.W * p["width"],
                     chars=int(max(0, ctx.t - 0.25) * p["cps"]), fill=p["color"])
    return ctx.shadowed(ctx.stack([head, body], gap=2))
