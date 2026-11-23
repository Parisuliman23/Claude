# Reference: numbers & lists that pop as they're said (Nov 22 2026)

File: `library/references/ref-popups-1.mp4` (a creator's "what I actually kept" expense breakdown, 1:50). The user:
"when she says $34,000, the $34,000 pops up… when she lists things on her fingers they type out, not part of the caption.
I don't care about the caption type, just the way it pops up as she talks about it."

## What happens (measured frame by frame)
- **Topic tag** the moment a topic is named: black heavy caps on a yellow-green highlighter swipe ("MANAGEMENT",
  "SUBSCRIPTIONS", "STRIPE FEE", "QUARTERLY TAXES", "TOTAL EXPENSES", "WHAT I ACTUALLY KEPT"), with a tiny handwritten
  note under it ("(keeps 15%)", "(the biggest expense)"). On the chest, under the caption.
- **The amount pops ON the word** ($686.25 at 21.54 s): ~0.1 s small, then zooms to full size with a slight overshoot,
  settles in ~0.2 s. Bright yellow, dark edge. Bigger money = bigger number ($25,000 is the largest).
- **Lists type themselves out in handwriting** one item per spoken name (URL Genius → Stan Store → Meta), left column
  white; extra items in a tilted yellow handwriting column on the right.
- **A running tally** in handwriting near the head (686.25 / 393.69 / 1,037.25 / 25,000.00) before the total pops.
- Everything for a topic stays until the next topic starts, then clears at once. Percentages are yellow in the caption.

## In One Take
`money_pop` look (lookbook/looks/money_pop.py): `label`, `sub`, `label_at`, `amount`, `amount_at`, `amount_size`, `items`
+ `items_at`, `items2` + `items2_at` — all `*_at` as word cues. Number only: `"label": ""`. Place it on the chest
(y ~0.6 in full-frame, or in the top half of a split screen), one per topic, w0 = topic word, w1 = last word of the topic.
