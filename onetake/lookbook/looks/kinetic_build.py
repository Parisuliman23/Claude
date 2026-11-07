META = {
    "name": "Kinetic word build",
    "description": "Words fly in from the right one by one, pushing the phrase left until it locks centred. Put each "
                   "word on the moment it's said with words_at. Bold white, the last word in the accent.",
    "params": {"text": "spend less save more", "words_at": [], "gap": 0.22, "size": 96, "color": "#FFFFFF",
               "accent": "#F5C542", "accent_last": True, "upper": False},
}


def render(ctx):
    p = ctx.p
    words = str(p["text"]).split()
    if p["upper"]:
        words = [w.upper() for w in words]
    f = ctx.font(ctx.MO_BOLD, int(p["size"]))
    at = list(p["words_at"])
    times = [at[i] if i < len(at) and at[i] is not None else i * p["gap"] for i in range(len(words))]
    space = f.getlength(" ")
    full = sum(f.getlength(w) for w in words) + space * (len(words) - 1)
    W, H = int(full + 400), int(p["size"] * 1.6)
    img = ctx.Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ctx.ImageDraw.Draw(img)
    shown = [i for i, tt in enumerate(times) if ctx.t >= tt]
    if not shown:
        return None
    MOVE = 0.32
    # width of the phrase so far (each word eases in), centred on the canvas
    def width_upto(n, k_last):
        ws = [f.getlength(words[i]) for i in range(n)]
        return sum(ws[:-1]) + space * (n - 1) + ws[-1] * k_last if n else 0
    last = shown[-1]
    k = ctx.p3(ctx.prog(times[last], MOVE))
    cur = width_upto(last + 1, k) if last else f.getlength(words[0])
    x = W / 2 - cur / 2
    for i in shown:
        ww = f.getlength(words[i])
        wx = x
        alpha = 255
        if i == last:
            wx = x + (1 - k) * 260  # slides in from the right
            alpha = int(255 * min(1.0, ctx.prog(times[last], MOVE * 0.6)))
        col = ctx.rgba(p["accent"] if (p["accent_last"] and i == len(words) - 1) else p["color"])
        d.text((wx, H * 0.72), words[i], font=f, fill=col[:3] + (alpha,), anchor="ls")
        x += ww + space
    return ctx.shadowed(img, blur=8, offset=4, alpha=160)
