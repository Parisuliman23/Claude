META = {
    "name": "Stock chart (real prices)",
    "description": "A real share-price chart that draws itself on: company logo + ticker, the price counting to today's, "
                   "the % change (green up / red down) and the time range. Prices come from "
                   "`python3 -m engine price-fetch NVDA 1y` (saved, so the reel always shows the same numbers).",
    "params": {"ticker": "NVDA", "range": "1y", "title": "", "draw": 1.4, "width": 0.9, "height": 0.3,
               "theme": "light", "show_logo": True, "label": ""},
}
# range: 5d 1mo 3mo 6mo ytd 1y 2y 5y 10y max. title: optional line above (e.g. "NVIDIA this year").
# theme: "light" (white card) or "dark". label: replaces the range text (e.g. "since I bought").

RANGE_TEXT = {"5d": "past 5 days", "1mo": "past month", "3mo": "past 3 months", "6mo": "past 6 months",
              "ytd": "this year", "1y": "past year", "2y": "past 2 years", "5y": "past 5 years", "10y": "past 10 years",
              "max": "all time"}


def render(ctx):
    from engine import logos, prices
    p, t = ctx.p, ctx.t
    data = prices.cached(p["ticker"], p["range"])
    W, H = int(ctx.W * p["width"]), int(ctx.H * p["height"])
    dark = p["theme"] == "dark"
    card, pad = ctx.card(W, H, radius=28, fill="#111418" if dark else "#FFFFFF")
    d = ctx.ImageDraw.Draw(card)
    ink = ctx.rgba("#FFFFFF" if dark else "#14161A")
    soft = ctx.rgba("#8A9099")
    x0, y0 = pad + 36, pad + 30
    # header: logo + ticker / name
    lx = x0
    if p["show_logo"]:
        f = logos.best(p["ticker"], "icon") or logos.best(p["ticker"])
        if f:
            lg = ctx.image(str(f)).convert("RGBA")
            s = 64 / max(lg.width, lg.height)
            lg = lg.resize((max(1, int(lg.width * s)), max(1, int(lg.height * s))), ctx.Image.LANCZOS)
            card.alpha_composite(lg, (lx, y0 + (64 - lg.height) // 2))
            lx += lg.width + 18
    d.text((lx, y0 + 4), p["ticker"].upper().lstrip("$"), font=ctx.font(ctx.SANS_X, 40), fill=ink, anchor="lt")
    sub = p["title"] or (data or {}).get("name", "")
    if sub:
        d.text((lx, y0 + 50), sub[:34], font=ctx.font(ctx.SANS, 24), fill=soft, anchor="lt")
    if not data:
        d.text((pad + W / 2, pad + H / 2), f"Run: price-fetch {p['ticker']} {p['range']}", font=ctx.font(ctx.SANS, 30),
               fill=soft, anchor="mm")
        return card
    c = data["c"]
    k = ctx.p3(min(1.0, t / max(0.2, float(p["draw"]))))  # how much of the line is drawn
    n = max(2, int(2 + (len(c) - 2) * k))
    first, now = c[0], c[n - 1]
    chg = (now - first) / first * 100 if first else 0
    col = ctx.rgba("#16A34A" if now >= first else "#DC2626")  # green while it's up so far, red while it's down
    # price (counts along with the line) + change
    cur = "$" if data.get("currency") == "USD" else ""
    fp = ctx.font(ctx.SANS_X, 64)
    price = f"{cur}{now:,.2f}"
    d.text((pad + W - 36, y0 - 2), price, font=fp, fill=ink, anchor="rt")
    arrow = "▲" if chg >= 0 else "▼"
    fc = ctx.font(ctx.SANS_X, 30)
    ct = f"{arrow} {abs(chg):.1f}%  {p['label'] or RANGE_TEXT.get(p['range'], p['range'])}"
    d.text((pad + W - 36, y0 + 70), ct, font=fc, fill=ctx.rgba("#16A34A" if chg >= 0 else "#DC2626"), anchor="rt")
    # chart area
    cx0, cy0, cx1, cy1 = pad + 36, pad + 150, pad + W - 36, pad + H - 34
    lo, hi = min(c), max(c)
    span = (hi - lo) or 1
    pts = [(cx0 + (cx1 - cx0) * i / (len(c) - 1), cy1 - (cy1 - cy0) * (v - lo) / span) for i, v in enumerate(c)]
    shown = pts[:n]
    # soft fill under the line
    fill = ctx.Image.new("RGBA", card.size, (0, 0, 0, 0))
    fd = ctx.ImageDraw.Draw(fill)
    fd.polygon(shown + [(shown[-1][0], cy1), (shown[0][0], cy1)], fill=col[:3] + (46,))
    card.alpha_composite(fill)
    d = ctx.ImageDraw.Draw(card)
    d.line([(cx0, cy1), (cx1, cy1)], fill=ctx.rgba("#2A2F36" if dark else "#E6E8EB"), width=2)
    d.line(shown, fill=col, width=7, joint="curve")
    ex, ey = shown[-1]
    d.ellipse([ex - 11, ey - 11, ex + 11, ey + 11], fill=col)
    d.ellipse([ex - 5, ey - 5, ex + 5, ey + 5], fill=ctx.rgba("#FFFFFF"))
    return card
