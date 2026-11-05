META = {
    "name": "Chapter header",
    "description": "Persistent section header: small handwritten tag above heavy caps (e.g. STRUCTURE: STEP 2). Keep it up for the whole section.",
    "group": "structure",
    "params": {"tag": "", "header": "STRUCTURE:", "step": "", "size": 50, "color": "#FFFFFF", "width": 0.86},
}


def render(ctx):
    p = ctx.p
    tag = ctx.write(p["tag"], ctx.HAND, int(p["size"] * 1.1), ctx.W * p["width"], fill=p["color"]) if p["tag"] else None
    line = (p["header"] + (" " + p["step"] if p["step"] else "")).strip()
    head = ctx.write(line, ctx.LOUD, p["size"], ctx.W * p["width"], fill=p["color"], upper=True)
    return ctx.shadowed(ctx.stack([tag, head], gap=0))
