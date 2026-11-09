META = {
    "name": "Notebook counter",
    "description": "Cream notebook card: a small grey label, a big serif-italic number that counts up the moment it's "
                   "said (count_at), and a handwritten note typed underneath. Money, days, followers, percentages.",
    "params": {"label": "paid off in one year", "to": 50000, "from": 0, "prefix": "$", "suffix": "", "commas": True,
               "count_at": 0.2, "count_time": 1.3, "note": "", "note_at": None, "width": 0.56},
}


def render(ctx):
    p, NB = ctx.p, ctx.NB
    W = int(ctx.W * p["width"])
    has_note = bool(p["note"])
    H = 64 + 128 + (62 if has_note else 0) + 18
    img, pad = ctx.paper(W, H)
    d = ctx.ImageDraw.Draw(img)
    ink = ctx.rgba(NB["ink"])
    d.text((pad + 30, pad + 46), p["label"], font=ctx.font(ctx.NB_LABEL, 26), fill=ctx.rgba(NB["gray"]), anchor="ls")
    k = ctx.ease(min(1.0, max(0.0, ctx.t - p["count_at"]) / max(0.1, p["count_time"])))
    n = p["from"] + (p["to"] - p["from"]) * k
    n = int(round(n)) if float(p["to"]).is_integer() else round(n, 1)
    num = f"{n:,}" if p["commas"] else str(n)
    text = f"{p['prefix']}{num}{p['suffix'] if k >= 1 else ''}"
    f = ctx.font(ctx.NB_SERIF, 118)
    if ctx.t >= p["count_at"]:  # the card waits empty until the number is said, then counts
        d.text((pad + 26, pad + 64 + 104), text, font=f, fill=ink, anchor="ls")
    if k >= 1:  # a yellow underline swipes in when the count lands
        u = min(1.0, (ctx.t - p["count_at"] - p["count_time"]) / 0.25)
        full = f.getlength(text)
        if u > 0:
            d.rounded_rectangle([pad + 26, pad + 64 + 116, pad + 26 + full * u, pad + 64 + 126], radius=4,
                                fill=ctx.rgba(NB["yellow"]))
    if has_note:
        na = p["note_at"] if p["note_at"] is not None else p["count_at"] + p["count_time"] + 0.2
        if ctx.t >= na:
            ctx.hand(d, (pad + 30, pad + H - 30), p["note"], 34, chars=(ctx.t - na) * 30)
    return img
