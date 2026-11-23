META = {
    "name": "Money pop (label + number pops on the word)",
    "description": "Learned from the user's favourite expense-breakdown reel: a highlighter tag names the topic "
                   "(MANAGEMENT, with a tiny handwritten note), the amount POPS from small to big exactly when it's said, "
                   "and a list types itself out in handwriting item by item as it's named. Separate from the captions.",
    "params": {"label": "MANAGEMENT", "sub": "(keeps 15%)", "label_at": 0.0,
               "amount": "$686.25", "amount_at": 0.6, "amount_size": 118,
               "items": [], "items_at": [], "items2": [], "items2_at": [],
               "marker": "#141418CC", "label_color": "#FFFFFF", "amount_color": "#FFFFFF", "item_color": "#FFFFFF",
               "item2_color": "#FFFFFF", "font": "Inter_800ExtraBold", "list_font": "Inter_700Bold", "cps": 30, "width": 760},
}
# Only the MOTION is copied from the reference (pop on the word, lists typing out). Colours and fonts follow the user's
# own reel (default: white text, dark pill like the cinematic-pill captions, Inter) — they don't want her yellow/handwriting.
# label_at / amount_at / items_at / items2_at: word cues, e.g. {"w": 57}, so each piece lands on its word.
# amount: leave "" for a tag-only pop (e.g. a list). Bigger money = bigger amount_size (e.g. 150 for $25,000).


def _pop(t, dur=0.22, over=1.12):
    """0 before it lands, then small -> overshoot -> settle (the 'pop' in the reference)."""
    if t < 0:
        return 0.0
    if t >= dur:
        return 1.0
    k = t / dur
    if k < 0.7:
        return 0.35 + (over - 0.35) * (k / 0.7)
    return over + (1.0 - over) * ((k - 0.7) / 0.3)


def _paste_scaled(canvas, piece, cx, cy, s):
    if s <= 0.02:
        return
    w, h = piece.size
    sw, sh = max(1, int(w * s)), max(1, int(h * s))
    sm = piece.resize((sw, sh))
    canvas.alpha_composite(sm, (int(cx - sw / 2), int(cy - sh / 2)))


def render(ctx):
    p, t = ctx.p, ctx.t
    Image, ImageDraw = ctx.Image, ctx.ImageDraw
    W = int(p["width"])
    loud = ctx.font(p["font"], 60)
    hand = ctx.font(p["list_font"], 34)
    big = ctx.font(p["font"], int(p["amount_size"]))
    ih = ctx.font(p["list_font"], 50)

    # --- the tag: black caps on a highlighter swipe, tiny handwritten note under it
    if not p["label"]:  # number only: no tag
        p = {**p, "sub": ""}
    lw = int(loud.getlength(p["label"])) + 50 if p["label"] else 0
    sub_w = int(hand.getlength(p["sub"])) if p["sub"] else 0
    tag_w, tag_h = (max(lw, sub_w + 30), 84 + (40 if p["sub"] else 0)) if p["label"] else (0, 0)
    tag = Image.new("RGBA", (tag_w + 10, tag_h + 10), (0, 0, 0, 0))
    if p["label"]:
        d = ImageDraw.Draw(tag)
        d.rounded_rectangle([5, 8, tag_w + 2, tag_h - 2], radius=26, fill=ctx.rgba(p["marker"]))
        d.text(((tag_w + 10) / 2, 46), p["label"], font=loud, fill=ctx.rgba(p["label_color"]), anchor="mm")
        if p["sub"]:
            d.text(((tag_w + 10) / 2, 100), p["sub"], font=hand, fill=ctx.rgba(p["label_color"]), anchor="mm")

    # --- the amount: bold yellow with a dark edge so it reads on any background
    amt = None
    if p["amount"]:
        aw, ah = int(big.getlength(p["amount"])) + 30, int(p["amount_size"] * 1.25)
        amt = Image.new("RGBA", (aw, ah), (0, 0, 0, 0))
        ImageDraw.Draw(amt).text((aw / 2, ah / 2), p["amount"], font=big, fill=ctx.rgba(p["amount_color"]), anchor="mm",
                                 stroke_width=4, stroke_fill=(0, 0, 0, 160))

    rows = max(len(p["items"]), len(p["items2"]))
    H = tag_h + 20 + (amt.size[1] if amt else 0) + rows * 66 + 40
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    if p["label"]:
        _paste_scaled(img, tag, W / 2, 10 + tag_h / 2, _pop(t - float(p["label_at"]), 0.18, 1.08))
    y = tag_h + 20 if p["label"] else 10
    if amt:
        _paste_scaled(img, amt, W / 2, y + amt.size[1] / 2, _pop(t - float(p["amount_at"])))
        if t >= float(p["amount_at"]):
            y += amt.size[1]

    # --- lists typed in handwriting as each item is named (left column white, right column yellow, tilted)
    d = ImageDraw.Draw(img)
    for col, key, color in ((0, "items", p["item_color"]), (1, "items2", p["item2_color"])):
        items, ats = p[key], list(p[key + "_at"]) + [None] * len(p[key])
        for i, txt in enumerate(items):
            at = ats[i] if ats[i] is not None else float(p["amount_at"]) + 0.5 * i
            n = int(max(0.0, t - float(at)) * float(p["cps"]))
            if n <= 0:
                continue
            x = W * (0.12 if col == 0 else 0.56)
            d.text((x, y + 8 + i * 66), txt[:n], font=ih, fill=ctx.rgba(color), stroke_width=3, stroke_fill=(0, 0, 0, 170))
    return img
