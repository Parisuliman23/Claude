META = {
    "name": "Chat bubbles",
    "description": "A message thread that builds up: grey bubbles on the left (them), blue on the right (me). A typing "
                   "indicator shows before each one. Put each message on its word with at. A DM, a client question, "
                   "a conversation you're retelling.",
    "params": {"messages": [{"from": "them", "text": "how did you pay off $50k so fast??"},
                            {"from": "me", "text": "one boring habit. I'll show you"}],
               "at": [], "gap": 1.2, "width": 0.78, "typing": 0.45},
}


def render(ctx):
    p = ctx.p
    msgs = list(p["messages"])
    W = int(ctx.W * p["width"])
    f = ctx.font("Inter_700Bold", 38)
    maxw = W * 0.72
    at = list(p["at"])
    times = [at[i] if i < len(at) and at[i] is not None else i * p["gap"] for i in range(len(msgs))]
    blocks, y = [], 0
    for i, m in enumerate(msgs):
        lines = ctx.wrap(m["text"], f, maxw - 60)
        bw = max(f.getlength(l) for l in lines) + 60
        bh = 50 * len(lines) + 34
        blocks.append((m, lines, bw, bh, y))
        y += bh + 22
    H = max(1, y)
    img = ctx.Image.new("RGBA", (W + 40, H + 40), (0, 0, 0, 0))
    d = ctx.ImageDraw.Draw(img)
    for i, (m, lines, bw, bh, by) in enumerate(blocks):
        t0 = times[i]
        if ctx.t < t0:
            break
        me = m.get("from") == "me"
        x = 20 + (W - bw if me else 0)
        typing = ctx.t < t0 + p["typing"] and p["typing"] > 0
        bg = ctx.rgba("#2F6BFF" if me else "#E9E9EB")
        fg = ctx.rgba("#FFFFFF" if me else "#111111")
        k = ctx.ease_back(ctx.prog(t0, 0.22))
        if typing:  # three bouncing dots in a small bubble
            tw = 130
            tx = 20 + (W - tw if me else 0)
            d.rounded_rectangle([tx, 20 + by, tx + tw, 20 + by + 70], radius=35, fill=bg)
            for j in range(3):
                jy = 20 + by + 35 - 8 * max(0.0, __import__("math").sin((ctx.t - t0) * 9 - j * 0.9))
                d.ellipse([tx + 32 + j * 26 - 9, jy - 9, tx + 32 + j * 26 + 9, jy + 9], fill=fg[:3] + (170,))
            continue
        k = ctx.ease_back(ctx.prog(t0 + p["typing"], 0.22))
        bub = ctx.Image.new("RGBA", (int(bw), int(bh)), (0, 0, 0, 0))
        bd = ctx.ImageDraw.Draw(bub)
        bd.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=32, fill=bg)
        for j, ln in enumerate(lines):
            bd.text((30, 17 + 50 * j + 38), ln, font=f, fill=fg, anchor="ls")
        s = max(0.05, k)
        if s != 1:
            bub = bub.resize((max(1, int(bw * s)), max(1, int(bh * s))))
        img.alpha_composite(bub, (int(x + (bw - bub.width) * (1 if me else 0)), int(20 + by + (bh - bub.height))))
    return ctx.shadowed(img, blur=6, offset=3, alpha=90)
