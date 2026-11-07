import math

META = {
    "name": "Line chart (draws up or down)",
    "description": "White data card: the line draws itself as the value counts up (or down), ending in a glowing dot. "
                   "Use 'down' for debt going to zero, 'up' for savings/investments growing.",
    "params": {"title": "my debt", "from": 50000, "to": 0, "prefix": "$", "suffix": "", "direction": "down",
               "points": [], "labels": ["Jan", "Dec"], "draw_at": 0.3, "draw_time": 1.6, "width": 0.76},
}
# points: optional list of values to plot (otherwise a smooth curve from `from` to `to`).


def render(ctx):
    p, MO = ctx.p, ctx.MO
    W, H = int(ctx.W * p["width"]), 440
    img, pad = ctx.card(W, H, radius=28, fill=MO["card"])
    d = ctx.ImageDraw.Draw(img)
    down = p["direction"] == "down"
    color = ctx.rgba(MO["down"] if down else MO["up"])
    ink, muted = ctx.rgba(MO["ink"]), ctx.rgba(MO["muted"])
    k = ctx.inout(ctx.prog(p["draw_at"], p["draw_time"]))
    val = p["from"] + (p["to"] - p["from"]) * k
    d.text((pad + 40, pad + 66), p["title"], font=ctx.font(ctx.MO_BOLD, 38), fill=muted, anchor="ls")
    d.text((pad + W - 40, pad + 80), f"{p['prefix']}{ctx.fmt_num(val)}{p['suffix']}", font=ctx.font(ctx.MO_BOLD, 72),
           fill=color, anchor="rs")
    x0, x1, y0, y1 = pad + 40, pad + W - 40, pad + 140, pad + H - 80
    for g in range(4):  # faint grid
        y = y0 + (y1 - y0) * g / 3
        d.line([(x0, y), (x1, y)], fill=ctx.rgba(MO["line"]), width=2)
    pts = [float(v) for v in p["points"]]
    if len(pts) < 2:
        a, b = float(p["from"]), float(p["to"])
        pts = [a + (b - a) * (1 / (1 + math.exp(-6 * (u / 30 - 0.5))) - 0.047) / 0.906 for u in range(31)]
    lo, hi = min(pts), max(pts)
    span = (hi - lo) or 1
    xy = [(x0 + (x1 - x0) * i / (len(pts) - 1), y1 - (y1 - y0) * (v - lo) / span) for i, v in enumerate(pts)]
    # resample along the path to draw up to k
    seg = []
    total = sum(math.dist(xy[i], xy[i + 1]) for i in range(len(xy) - 1))
    goal, run = total * k, 0.0
    seg.append(xy[0])
    for i in range(len(xy) - 1):
        L = math.dist(xy[i], xy[i + 1])
        if run + L >= goal:
            f = (goal - run) / L if L else 0
            seg.append((xy[i][0] + (xy[i + 1][0] - xy[i][0]) * f, xy[i][1] + (xy[i + 1][1] - xy[i][1]) * f))
            break
        seg.append(xy[i + 1])
        run += L
    if k > 0 and len(seg) > 1:
        fill = [(seg[0][0], y1)] + seg + [(seg[-1][0], y1)]  # soft area under the line
        area = ctx.Image.new("RGBA", img.size, (0, 0, 0, 0))
        ctx.ImageDraw.Draw(area).polygon(fill, fill=color[:3] + (38,))
        img.alpha_composite(area)
        d = ctx.ImageDraw.Draw(img)
        d.line(seg, fill=color, width=8, joint="curve")
        ex, ey = seg[-1]
        glow = 18 + 6 * math.sin(ctx.t * 6)
        d.ellipse([ex - glow, ey - glow, ex + glow, ey + glow], fill=color[:3] + (60,))
        d.ellipse([ex - 11, ey - 11, ex + 11, ey + 11], fill=color, outline=ctx.rgba("#FFFFFF"), width=4)
    lf = ctx.font(ctx.MO_SEMI, 26)
    if p["labels"]:
        d.text((x0, y1 + 44), str(p["labels"][0]), font=lf, fill=muted, anchor="ls")
        d.text((x1, y1 + 44), str(p["labels"][-1]), font=lf, fill=muted, anchor="rs")
    return img
