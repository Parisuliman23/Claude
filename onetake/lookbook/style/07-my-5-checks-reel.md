# My reel: "5 checks before you buy a stock" (Nov 2026)

The user's own finished reel (1:11 after cuts from 9:35 filmed), deleted from the Chromebook on Nov 17, 2026 to free
space. They asked Claude to **remember its editing style**. The full edit (every overlay with its params) is saved in
`lookbook/references/my-5-checks-reel/project.json`: copy params from there when a reel fits this format.

## When to use it
A teaching reel with a numbered list ("5 things…", "3 rules…"), a money story as the hook, and a personal angle.
Style-pick said **mix**; the edit is Look A/C-style typed graphics, not notebook cards.

## Settings
- Captions: `cinematic-pill` at `caption_y` 0.65 (chest, below the chin).
- Camera: hook push-in (7 s, 0.08) + **punch-ins (1.12) at every thought change**: 12 punches in 71 s, roughly
  one at the start of each numbered point and on every turn ("Here it is", "2.", "3.", "4.", "And five").
- Filter: the user picked **`soft-skin`** (Soft skin, less orange) on this reel. Still no filter by default; offer it
  for warm/orange indoor footage.
- No music bed. 10 sound effects (pop, whoosh, ding, ka-ching, riser, boom, buzz) at sfx volume 0.7.
- Also had a carousel and a story.

## Structure and graphics (word-timed)
1. **Hook (0–5 s)**: `typed_title` y 0.12 "THIS STOCK ALMOST COST ME $80K" + sub "check these 5 things before you buy";
   on "$80,000" a red `big_number` counter "-$80,000" (#FC1404, label "what i would have lost") low at y 0.745;
   a split-screen B-roll flash of the stock market on "almost bought this stock".
2. **Promise**: a teased `checklist` of all 5 checks at the top (y 0.177, `tease: true`) when the 5 things are first
   mentioned. Split B-roll beats: trading on a phone, a **casino slot machine on "investing or gambling"**.
3. **Audience aside**: `hand_note` quoting the bad reasons ("mama said buy"… "cousin said buy"…), a `red_x` labelled
   "even me", then `keyword_def` "CHECKLIST FIRST = then maybe i think about buying".
4. **The 5 checks**: the same `checklist` re-placed top-left (x 0.34, y 0.167) for each point, one overlay per point,
   so the list stays on screen and ticks forward. Under each point, low (y ~0.75):
   - an `equation` rule card in red: "CAN'T EXPLAIN IT → DON'T BUY IT", "NO CLEAR MONEY → DON'T BUY IT";
   - `hand_note` paraphrases: "revenue... profit... margins...", "patents. brand. tech. = the _moat_";
   - an `emoji_row` off to the right (x 0.8, y 0.32): 💰🤔, 📈, 🐻.
5. **Check 5 (bear case)**: `keyword_def` "BEAR CASE = what could make this company go downhill?" + a white-panel
   split screen with a `checklist` (plus style, Inter) of risks: valuation, debt, competition, geopolitics. Then
   `red_x` "being right" and `hand_note` "...it is about protecting _yourself_".
6. **Plan**: `equation` in blue (#0444A4) "IT DROPS → ADD OR EXIT" (split B-roll of the market), `hand_note`
   "no panic. a _plan_."
7. **CTA**: `cta_keyword` "save this" / "5 CHECKS" / "before your next buy", then a `hand_note` teaser
   "tomorrow: the stocks i own..." (series hook).

## What made it work
Every number, rule and list item got a graphic on its word; the running checklist gave the reel a spine; red only
for loss/"don't", blue for the plan; emojis beside the face, never on it; quotes and paraphrases, never full sentences.
