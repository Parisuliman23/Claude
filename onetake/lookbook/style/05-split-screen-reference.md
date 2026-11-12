# Reference · "Split-screen finance explainer" (the user's favourite structure)

Studied one frame per second from two finance explainers the user sent (1:44 and 1:33, both talking head at a desk,
finance topics). The user loves **everything about how they're edited except the filter and fonts**, so copy the
structure, pacing and graphics, and keep the user's own colours and type.

## The structure

| Time | What's on screen |
|---|---|
| 0–5 s | **Hook over a moving montage**: full-screen B-roll cut every ~1 s (newspaper reader, Wall Street, crowds), a two-line title that stays put (bold white, big) + a small line under it in brackets, and a big stat counting up above it ("54%" → "90%"). Or (ref 2) the title held at the top over the speaker, with proof popping in the lower third (a portfolio screenshot, a "RECESSION" photo, a news headline card). |
| body | Alternates every 1–3 s between the beats below. The speaker alone is never on screen for more than ~3–4 s. |
| end | CTA: big two-line "Comment 'ALERT'" at the top (yellow keyword), then "+follow" held to the end; a tiny disclaimer at the bottom. |

## The beats (and the One Take tool for each)

1. **Split screen** (the main beat, ~40% of the reel). Top half: stock footage that literally shows the words (a casino
   slot machine on "casino", a BUY button on "buy", red tickers on "selling", a skyline on "1%"). Bottom half: the
   speaker, eyes in view. **The top clip changes every 1.5–3 s while the speaker keeps talking**, so a sentence gets
   2–3 clips in a row. → several `add-broll … "layout": "split"` back to back, one per phrase (`broll-find "…"`).
2. **Small boxed captions on the seam**: 2–3 words, small white text in a dark rounded box, sitting on the line
   between the halves (and at chest height when it's just the speaker). → caption style `cinematic-pill` (in a split
   it moves to the seam by itself).
3. **Full-screen cut-aways** (1–3 s): a striking clip on a strong word ("FOMO", "panic"), caption over it.
   → `add-broll` with `"layout": "full"`.
4. **Documents and articles in the top half**, slowly pushing in, with the key line **highlighted in yellow**.
   → a split with the screenshot as `src` (`"push": true`), or `highlight_card`.
5. **Charts** in the top half on a light card (area/line chart that draws on). → split with a white panel
   (`"src": null`) + `line_chart` / `growth_chart` / `bar_chart` at y ~0.22.
6. **Card over a blurred background** (ref 2): a screenshot, table or chart on a rounded card, the speaker blurred
   and dimmed behind it, caption below. → `add-broll … "layout": "card"` with the screenshot as `src`.
7. **Graphics floating above the head** on the plain wall (no split): a numbered list where the coming items are
   blurred ("1. Anchor with ETF / 2. ▒▒▒ / 3. ▒▒▒") and un-blur as each is said; a progress ring ("45%"); a short
   line chart. → `checklist` with `"tease": true` (items timed with word cues), `progress_ring`, `line_chart`, placed
   at y 0.12–0.25 so they sit over the wall, never the face.
8. **People**: a full-screen photo of the person named, with a label "Current Fed Chair:" + the name, big.
   → full-screen `add-broll` with the photo + `lower_third` or `name_badge`. Use only real photos the user supplies.
9. **Companies**: logos pop up as they're named. → `logo_row` (each logo on its word; `logo-find NVIDIA AMD Intel`).
10. **Big number over a photo**: "20–25% Cash" over a money image. → full-screen image `add-broll` + `big_number`.
11. **Social proof / their own content**: two phone-shaped video cards side by side over a dark backdrop.
    → `add-broll` with a screenshot of the posts (`"layout": "card"`).

## Pace
- A new visual every **1–2 s** in the hook, every **2–3 s** after. Hard cuts, no fades.
- Speaker-only stretches: 2–4 s, usually right after a graphic so the viewer sees the face again.
- The last ~5 s: CTA only (no B-roll).

## Not copied
Their faces, names, channel graphics and exact images. Fonts and the colour grade don't matter to the user: keep
their own (no filter by default).
