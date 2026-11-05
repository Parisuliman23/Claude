META = {
    "name": "Typed headline",
    "description": "Hook / audience call-out: heavy white caps that type on (~33 letters/s), then a handwritten line under it.",
    "group": "hook",
    "params": {"text": "THE HUGE LAUNCHES ARE GETTING OUT OF HAND...", "sub": "", "cps": 33, "sub_cps": 25,
               "size": 56, "sub_size": 62, "width": 0.82, "color": "#FFFFFF", "font": "Montserrat_900Black"},
}


def render(ctx):
    p = ctx.p
    title = ctx.write(p["text"], p["font"], p["size"], ctx.W * p["width"], chars=int(ctx.t * p["cps"]),
                      fill=p["color"], upper=True)
    sub = None
    if p["sub"]:
        start = len(p["text"]) / p["cps"]
        sub = ctx.write(p["sub"], ctx.HAND, p["sub_size"], ctx.W * p["width"],
                        chars=int(max(0, ctx.t - start) * p["sub_cps"]), fill=p["color"])
    return ctx.shadowed(ctx.stack([title, sub], gap=4))
