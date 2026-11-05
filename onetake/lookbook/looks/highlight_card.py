META = {
    "name": "Receipt card + highlighter",
    "description": "A white article/quote card (proof). A yellow highlighter sweeps across the key phrase left→right (~0.75 s). Pair with push=true.",
    "params": {"text": "Investors with a net worth of $1M or more held their positions.", "highlight": "net worth of $1M or more",
               "source": "", "size": 46, "width": 0.78, "font": "Inter_700Bold", "highlighter": "#FCFC04",
               "sweep_at": 0.3, "sweep_time": 0.75},
}


def render(ctx):
    p = ctx.p
    f = ctx.font(p["font"], p["size"])
    fs = ctx.font("Inter_700Bold", int(p["size"] * 0.55))
    maxw = ctx.W * p["width"] - 80
    lines = ctx.wrap(p["text"], f, maxw)
    lh = int(p["size"] * 1.3)
    src_h = int(p["size"] * 0.9) if p["source"] else 0
    w = int(ctx.W * p["width"])
    h = lh * len(lines) + 70 + src_h
    card, pad = ctx.card(w, h, radius=18)
    d = ctx.ImageDraw.Draw(card)
    x0, y0 = pad + 40, pad + 35
    if p["source"]:
        d.text((x0, y0), p["source"].upper(), font=fs, fill=(120, 120, 130, 255), anchor="lt")
        y0 += src_h
    # where is the highlighted phrase?
    full = " ".join(lines)
    hs = full.lower().find(p["highlight"].lower()) if p["highlight"] else -1
    he = hs + len(p["highlight"]) if hs >= 0 else -1
    k = ctx.ease(min(1, max(0, ctx.t - p["sweep_at"]) / p["sweep_time"])) if hs >= 0 else 0
    pos = 0
    hl = ctx.rgba(p["highlighter"])
    total_hl = 0
    spans = []
    for i, line in enumerate(lines):
        a, b = max(hs, pos), min(he, pos + len(line))
        if hs >= 0 and a < b:
            xa = x0 + f.getlength(line[:a - pos])
            xb = x0 + f.getlength(line[:b - pos])
            spans.append((i, xa, xb))
            total_hl += xb - xa
        pos += len(line) + 1
    budget = total_hl * k
    for i, xa, xb in spans:  # one continuous left→right sweep across lines
        seg = min(budget, xb - xa)
        if seg > 0:
            y = y0 + i * lh
            d.rectangle([xa - 4, y + p["size"] * 0.05, xa + seg + 4, y + p["size"] * 1.15], fill=hl)
        budget -= xb - xa
    for i, line in enumerate(lines):
        d.text((x0, y0 + i * lh + p["size"] * 0.95), line, font=f, fill=(20, 20, 24, 255), anchor="ls")
    return card
