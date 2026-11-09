META = {
    "name": "Compare: this vs that",
    "description": "Two side-by-side cards with a VS badge: each side lands on its word, then the winner gets a green "
                   "check and the loser dims with a red cross. Before/after, option A vs B, myth vs fact.",
    "params": {"left_title": "Minimum payments", "left_value": "30 years", "right_title": "My method",
               "right_value": "2 years", "left_at": 0.0, "right_at": 0.6, "winner": "right", "verdict_at": 1.4,
               "width": 0.86},
}


def render(ctx):
    p, MO = ctx.p, ctx.MO
    W = int(ctx.W * p["width"])
    cw, ch, gap = (W - 40) / 2, 300, 40
    img = ctx.Image.new("RGBA", (W + 48, ch + 80), (0, 0, 0, 0))
    tf, vf = ctx.font(ctx.MO_SEMI, 32), ctx.font(ctx.MO_BOLD, 64)
    verdict = ctx.t >= p["verdict_at"] and p["winner"] in ("left", "right")
    for side, x in (("left", 24), ("right", 24 + cw + gap)):
        at = p[f"{side}_at"]
        k = ctx.p3(ctx.prog(at, 0.35))
        if k <= 0:
            continue
        lose = verdict and p["winner"] != side
        card, pad = ctx.card(cw, ch, radius=24, fill=MO["card"])
        d = ctx.ImageDraw.Draw(card)
        mid = pad + cw / 2
        for i, ln in enumerate(ctx.wrap(p[f"{side}_title"], tf, cw - 40)[:2]):
            d.text((mid, pad + 70 + i * 40), ln, font=tf, fill=ctx.rgba(MO["muted"]), anchor="ms")
        d.text((mid, pad + 200), p[f"{side}_value"], font=vf, fill=ctx.rgba(MO["ink"]), anchor="ms")
        if verdict:
            mark = ctx.ease_back(ctx.prog(p["verdict_at"], 0.3))
            bx, by, r = mid, pad + ch - 46, 26 * max(0.01, mark)
            win = not lose
            d.ellipse([bx - r, by - r, bx + r, by + r], fill=ctx.rgba(MO["up"] if win else MO["down"]))
            if win:
                ctx.check(d, bx, by + 2, r * 1.3, fill="#FFFFFF", width=5)
            else:
                d.line([(bx - r * .45, by - r * .45), (bx + r * .45, by + r * .45)], fill=ctx.rgba("#FFFFFF"), width=5)
                d.line([(bx + r * .45, by - r * .45), (bx - r * .45, by + r * .45)], fill=ctx.rgba("#FFFFFF"), width=5)
        a = k * (0.45 if lose else 1.0)
        img.alpha_composite(ctx.faded(card, a), (int(x - pad), int(40 - pad + (1 - k) * 30)))
    if ctx.t >= min(p["left_at"], p["right_at"]) + 0.2:  # VS badge in the middle
        d = ctx.ImageDraw.Draw(img)
        bx, by = 24 + cw + gap / 2, 40 + ch / 2
        d.ellipse([bx - 44, by - 44, bx + 44, by + 44], fill=ctx.rgba(MO["ink"]))
        d.text((bx, by + 2), "VS", font=ctx.font(ctx.MO_BLACK, 34), fill=ctx.rgba("#FFFFFF"), anchor="mm")
    return img
