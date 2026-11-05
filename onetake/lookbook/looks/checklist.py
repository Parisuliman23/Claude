META = {
    "name": "Running checklist",
    "description": "A list that builds item by item on the spoken words and stays up (never swaps items). Optional blurred 'coming up' items.",
    "params": {"title": "", "items": ["waitlist", "tech stack", "pricing"], "at": [], "gap": 1.0, "cps": 24,
               "style": "plain", "font": "NanumPenScript_400Regular", "size": 60, "width": 0.6,
               "tease": False, "color": "#FFFFFF", "align": "left"},
}


def render(ctx):
    p = ctx.p
    items = list(p["items"])
    at = list(p["at"]) + [None] * len(items)
    marks = {"plain": lambda i: "", "numbered": lambda i: f"{i + 1}. ", "plus": lambda i: "+ "}[p["style"]]
    parts = []
    if p["title"]:
        parts.append(ctx.write(p["title"], ctx.LOUD, int(p["size"] * 0.8), ctx.W * p["width"], fill=p["color"], upper=True,
                               align=p["align"]))
    for i, it in enumerate(items):
        start = at[i] if at[i] is not None else i * p["gap"]
        text = marks(i) + it
        if ctx.t >= start:
            parts.append(ctx.write(text, p["font"], p["size"], ctx.W * p["width"], chars=int((ctx.t - start) * p["cps"]),
                                   fill=p["color"], align=p["align"]))
        elif p["tease"]:  # visible but unreadable: you can see more is coming
            img = ctx.write(text, p["font"], p["size"], ctx.W * p["width"], fill=p["color"], align=p["align"])
            parts.append(img.filter(ctx.ImageFilter.GaussianBlur(p["size"] / 6)))
        else:  # keep the space so the list doesn't move as it grows
            img = ctx.write(text, p["font"], p["size"], ctx.W * p["width"], fill=p["color"], align=p["align"])
            parts.append(ctx.Image.new("RGBA", img.size, (0, 0, 0, 0)))
    return ctx.shadowed(ctx.stack(parts, gap=0, align="left" if p["align"] == "left" else "center"))
