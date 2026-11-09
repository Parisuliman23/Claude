META = {
    "name": "Week planner (checkmarks)",
    "description": "Cream card with a small label, a serif-italic note typed on the right, MON-SUN yellow day tabs over "
                   "white boxes; checkmarks land one day at a time, left to right.",
    "params": {"label": "my exact process", "note": "a full week ahead", "note_at": 0.2, "note_cps": 22,
               "days": ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"],
               "check_at": 1.0, "check_gap": 0.067, "checks": 7, "checks_at": [], "filled": [], "filled_at": 0.0,
               "width": 0.74},
}
# checks: how many days get a check (from the left). filled: day indexes shaded yellow (e.g. [0] for "today").
# checks_at: one time per day, so each check lands when that day is said, e.g. [{"w": 40}, {"w": 42}, ...].


def render(ctx):
    p, NB = ctx.p, ctx.NB
    days = list(p["days"])
    W = int(ctx.W * p["width"])
    head, box_h, tab_h, gap, side = 84, 126, 34, 12, 26
    H = head + tab_h + box_h + 26
    img, pad = ctx.paper(W, H)
    d = ctx.ImageDraw.Draw(img)
    ink = ctx.rgba(NB["ink"])
    t = ctx.t
    d.text((pad + side + 6, pad + 50), p["label"], font=ctx.font(ctx.NB_LABEL, 26), fill=ctx.rgba(NB["gray"]), anchor="ls")
    if p["note"]:
        n = int(max(0.0, t - p["note_at"]) * p["note_cps"])
        f = ctx.font(ctx.NB_SERIF, 54)
        full = f.getlength(p["note"])
        d.text((pad + W - side - full, pad + 60), p["note"][:n], font=f, fill=ink, anchor="ls")
    n = len(days)
    bw = (W - side * 2 - gap * (n - 1)) / n
    y0 = pad + head
    img.alpha_composite(ctx.shadows(img.size, [(pad + side + i * (bw + gap), y0, pad + side + i * (bw + gap) + bw,
                                                 y0 + tab_h + box_h) for i in range(n)], blur=5, alpha=60))
    d = ctx.ImageDraw.Draw(img)
    for i, day in enumerate(days):
        x = pad + side + i * (bw + gap)  # white box, yellow tab on top
        filled = i in p["filled"] and t >= p["filled_at"]
        d.rounded_rectangle([x, y0, x + bw, y0 + tab_h + box_h], radius=8,
                            fill=ctx.rgba("#F7EBB5" if filled else NB["white"]))
        d.rounded_rectangle([x, y0, x + bw, y0 + tab_h], radius=8, fill=ctx.rgba(NB["yellow"]))
        d.rectangle([x, y0 + tab_h - 8, x + bw, y0 + tab_h], fill=ctx.rgba(NB["yellow"]))
        d.text((x + bw / 2, y0 + tab_h / 2 + 1), day, font=ctx.font(ctx.NB_BOLD, 21), fill=ink, anchor="mm")
        if i < int(p["checks"]):
            per = list(p["checks_at"])
            ct = per[i] if i < len(per) and per[i] is not None else p["check_at"] + i * p["check_gap"]
            if t >= ct:  # each check lands in a single frame, like the reference
                ctx.check(d, x + bw / 2, y0 + tab_h + box_h / 2 + 2, bw * 0.6, width=6)
    return img
