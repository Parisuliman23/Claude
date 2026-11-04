import math
import random

META = {
    "name": "Emoji burst",
    "description": "A handful of emoji float up and fade — for big moments.",
    "params": {"emoji": "1f389", "count": 9, "size": 150, "seed": 3},
}


def render(ctx):
    p = ctx.p
    W, H = 900, 1100
    img = ctx.Image.new("RGBA", (W, H), (0, 0, 0, 0))
    e = ctx.emoji(p["emoji"])
    rnd = random.Random(p["seed"])
    for i in range(p["count"]):
        delay = rnd.uniform(0, 0.6)
        t = ctx.t - delay
        if t < 0:
            continue
        life = 1.8
        k = (t % life) / life
        sz = int(p["size"] * rnd.uniform(0.7, 1.2))
        x = W / 2 + rnd.uniform(-W / 2.4, W / 2.4) + math.sin(t * 3 + i) * 30
        y = H - 80 - k * (H - 200)
        em = e.resize((sz, sz)).rotate(math.sin(t * 4 + i) * 15, expand=True)
        a = em.getchannel("A").point(lambda v: int(v * (1 - k ** 3)))
        em.putalpha(a)
        img.alpha_composite(em, (int(x - em.width / 2), int(y - em.height / 2)))
    return img
