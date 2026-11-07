import math

META = {
    "name": "Confetti burst",
    "description": "A celebration burst of confetti that flies out and falls with gravity. For wins: debt paid off, a "
                   "milestone, a big number. Place it where the burst should come from.",
    "params": {"burst_at": 0.0, "count": 70, "colors": ["#F5C542", "#16A34A", "#2563EB", "#EF4444", "#FFFFFF", "#A855F7"],
               "spread": 520, "size": 1.0},
}


def render(ctx):
    p = ctx.p
    t = ctx.t - p["burst_at"]
    if t < 0 or t > 2.6:
        return None
    W, H = 1100, 1300
    img = ctx.Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ctx.ImageDraw.Draw(img)
    cx, cy = W / 2, H * 0.38
    for i in range(int(p["count"])):
        h1 = (math.sin(i * 12.9898) * 43758.5453) % 1  # seeded randoms: the same burst every render
        h2 = (math.sin(i * 78.233) * 12345.678) % 1
        h3 = (math.sin(i * 39.425) * 24634.634) % 1
        ang = -math.pi / 2 + (h1 - 0.5) * 2.4
        v = p["spread"] * (0.8 + 1.1 * h2)
        x = cx + math.cos(ang) * v * t * (1 - min(0.6, t * 0.25))
        y = cy + math.sin(ang) * v * t + 0.5 * 900 * t * t
        if not (0 <= x < W and 0 <= y < H):
            continue
        rot = t * (6 + 10 * h3) + i
        s = (10 + 10 * h3) * p["size"]
        flip = abs(math.cos(rot))
        col = ctx.rgba(p["colors"][i % len(p["colors"])])
        a = int(255 * min(1.0, max(0.0, (2.6 - t) / 0.6)))
        dx, dy = s * math.cos(rot), s * 0.5 * flip * math.sin(rot) + s * 0.25
        d.polygon([(x - dx, y - dy), (x + dy, y - dx), (x + dx, y + dy), (x - dy, y + dx)], fill=col[:3] + (a,))
    return img
