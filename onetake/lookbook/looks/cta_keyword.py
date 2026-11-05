META = {
    "name": "CTA keyword",
    "description": "\"Comment KEYWORD\": the biggest type in the video, in CTA yellow, double-blinks on, with a curved arrow toward the comment button.",
    "group": "cta",
    "params": {"question": "WANT THE GUIDE?", "keyword": "DEBT", "line": "comment", "accent": "#FCF46C",
               "size": 130, "q_size": 56, "arrow": True, "color": "#FFFFFF"},
}


def render(ctx):
    p = ctx.p
    # double-blink: on 1 frame, off 3 frames, then on
    if 1 / 30 <= ctx.t < 4 / 30:
        return None
    q = ctx.write(p["question"], ctx.LOUD, p["q_size"], ctx.W * 0.8, fill=p["color"], upper=True) if p["question"] else None
    line = ctx.write(p["line"], ctx.HAND, 70, ctx.W * 0.8, fill=p["color"]) if p["line"] else None
    kw = ctx.write(f'"{p["keyword"].upper()}"', ctx.LOUD, p["size"], ctx.W * 0.9, fill=p["accent"])
    body = ctx.stack([q, line, kw], gap=0)
    if not p["arrow"]:
        return ctx.shadowed(body)
    out = ctx.Image.new("RGBA", (body.width + 170, body.height + 60), (0, 0, 0, 0))
    out.alpha_composite(body, (0, 60))
    d = ctx.ImageDraw.Draw(out)
    ctx.curve(d, (body.width - 30, body.height + 20), (body.width + 150, body.height * 0.6), (body.width + 110, 20),
              ctx.ease(min(1, ctx.t / 0.5)), width=8, fill=p["accent"])
    return ctx.shadowed(out)
