META = {
    "name": "Notebook note card",
    "description": "Cream ruled note card: a small grey label, an optional serif-italic headline, then handwritten lines "
                   "typed on one after another. Optional circled tags with a word on the right (e.g. T teach).",
    "params": {"label": "the question I get asked most:", "title": "how on earth...",
               "lines": ["content + 3 kids + a full-time job"],
               "title_at": 0.25, "at": [], "gap": 0.8, "cps": 30, "width": 0.74,
               "tags": [], "tags_at": [], "legend": [], "legend_at": [], "min_lines": 1, "size": 0},
}
# tags: a letter circled at the end of each line, e.g. ["T", "O", "S", "O"] (tags_at = when each appears);
# legend: the key in a right-hand column, e.g. ["T teach", "O opinion", "S story"] (legend_at = when).


def render(ctx):
    p, NB = ctx.p, ctx.NB
    W = int(ctx.W * p["width"])
    pad_x, label_h, title_h = 30, 50, 84 if p["title"] else 0
    size = int(p["size"]) or (36 if len(p["lines"]) <= 2 else 33)
    row = int(size * 1.55)
    lines = list(p["lines"])
    n = max(len(lines), int(p["min_lines"]))
    H = label_h + title_h + row * n + 16
    img, pad = ctx.paper(W, H, ruled=row, top=label_h + title_h - row + 6)
    d = ctx.ImageDraw.Draw(img)
    x0, y0 = pad + pad_x, pad
    d.text((x0, y0 + 36), p["label"], font=ctx.font(ctx.NB_LABEL, 25), fill=ctx.rgba(NB["gray"]), anchor="ls")
    t = ctx.t
    if p["title"]:
        n_ch = int(max(0.0, t - p["title_at"]) * p["cps"] * 0.8)
        d.text((x0 - 2, y0 + label_h + 62), p["title"][:n_ch], font=ctx.font(ctx.NB_SERIF, 64),
               fill=ctx.rgba(NB["ink"]), anchor="ls")
        start = p["title_at"] + len(p["title"]) / (p["cps"] * 0.8) + 0.2
    else:
        start = p["title_at"]
    at = list(p["at"]) + [None] * len(lines)
    tags = [str(x).strip() for x in p["tags"]] + [""] * len(lines)
    tags_at = list(p["tags_at"]) + [None] * len(lines)
    legend = [str(x).strip() for x in p["legend"]]
    legend_at = list(p["legend_at"]) + [None] * len(legend)
    side = bool(legend) or any(tags)
    col_x = pad + int(W * 0.79) if legend else pad + W - 70
    if side:  # keep the writing left of the circles
        room = (col_x - 62) - x0
        f = ctx.font(ctx.NB_HAND, size)
        widest = max((sum(f.getlength(c) + size * 0.05 for c in ln) for ln in lines), default=0)
        while size > 22 and widest > room:
            size -= 1
            f = ctx.font(ctx.NB_HAND, size)
            widest = max(sum(f.getlength(c) + size * 0.05 for c in ln) for ln in lines)
    ink = ctx.rgba(NB["ink"])

    def circle(cx, cy, letter, r=21):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ctx.rgba(NB["yellow"]), outline=ink, width=3)
        d.text((cx, cy + 1), letter.upper(), font=ctx.font(ctx.NB_BOLD, 23), fill=ink, anchor="mm")
    for i, line in enumerate(lines):
        s = at[i] if at[i] is not None else start + i * p["gap"]
        base = y0 + label_h + title_h + row * i + int(row * 0.68)
        if t >= s:
            ctx.hand(d, (x0, base + 3), line, size, chars=(t - s) * p["cps"], track=0.05 if side else 0.07)
        if tags[i]:
            ta = tags_at[i] if tags_at[i] is not None else s + len(line) / p["cps"] + 0.2
            if t >= ta:
                circle(col_x - 34, base - 9, tags[i][0])
    for k, item in enumerate(legend):  # the key on the right: (T) teach, (O) opinion...
        la = legend_at[k] if legend_at[k] is not None else start + k * p["gap"]
        if t >= la:
            letter, _, word = item.partition(" ")
            base = y0 + label_h + title_h + row * k + int(row * 0.68)
            circle(col_x + 34, base - 9, letter)
            d.text((col_x + 64, base - 8), word, font=ctx.font(ctx.NB_BOLD, 27), fill=ink, anchor="lm")
    if legend:  # the column line, like a notes app table
        d.line([(col_x, pad + 4), (col_x, pad + H - 4)], fill=ctx.rgba(NB["rule"]), width=2)
    return img
