# Three reference reels (Nov 17, 2026): the user's chosen style

Files: `library/references/ref-nov17-1.mp4` (stock crash / Fed chair, 93 s), `ref-nov17-2.mp4` (modified DCA, 71 s),
`ref-nov17-3.mp4` (what the top 1% do, 104 s). Sheets + transcripts in `lookbook/references/ref-nov17-*/`.
The user said: **use these as the reference for my style**. Same family as `05-split-screen-reference.md`, with more detail.

## Pace
- Cuts every **1.5 s (reel 3), 2.5 s (reel 1), 4 s (reel 2)**. The speaker is rarely alone on screen for more than ~4 s.
- ~4 words/s, every pause cut (1–2 pauses over 1/3 s in the whole reel).
- Music: a quiet bed under the voice in reel 1, none in 2 and 3. Sound effects barely noticeable.
- Camera: locked off; a slight slow push at most. No punch-ins.

## Hook (0–5 s)
- A **held two-line bold white title** (sentence case, e.g. "Why stocks will crash very soon", "The top 1% don't pick better
  stocks") with a **small bracketed line** under it ("(watch this before may 15 and prepare your portfolio)"), on screen
  from frame 1, in the top third.
- Under it, **quick visual cuts every ~1 s**: B-roll in the top half (reel 3), full-screen images (reel 1: the portfolio
  card, a "RECESSION" banknote, the person's photo), plus a **big number** ("54%", "90%") above the title.
- Proof by 2 s: the creator's own portfolio card ($304,952.95) low on the chest.

## Captions
- Small, clean sans (Inter/SF style), white. Reel 3: 1–3 words on a **small dark translucent box on the split seam**;
  reel 1: one word, bigger, white, no box, mid-frame; reel 2: 2–3 small white words on the chest.
- → One Take: `cinematic-pill` (small boxed, sits on the seam in split screens).

## Visual vocabulary (what they show, on the word)
| They say… | They show |
|---|---|
| a general claim, a metaphor, an emotion | **split-screen B-roll** in the top half that literally shows it (slot machine on "casino", "Buy Now" button on "FOMO", red tickers on "panic selling", sunset skyline on "the 1%") |
| a named person | their **photo full screen** + a big white name label with a small role line ("Current Fed Chair: / Jerome Powell") |
| a stat from research | the **article / report screenshot** full width, key phrase **highlighted yellow**, slow push; or the **chart** full screen |
| maths, a rule, a system | **white panel in the top half**, numbers built term by term in black + **blue** (#0444A4): "$12,000 / 12 Months = $1,000 Monthly", a split tree "$2,400 20% · $9,600 80%", "IF VIX > 30 → BUY +$800" (blue box) |
| a term / a strategy name | archival **trading-floor photo** full screen with the term in white ("Modified DCA", "Dollar Cost Averaging") |
| a number / % | **progress ring** ("45%"), a growth line ("Doubled your money every seven years"), big white number with a small sub line ("$2,400 (Dry Powder)") |
| "number one / two / three" | a **numbered list above the head**, the next items **blurred** until said; it accumulates and stays |
| a framework | a title on the chest ("3 Step Investing Framework") |
| their own proof | a small dark card low on the chest (portfolio value, brokerage numbers) |
| end | **"Comment 'ALERT'"** big yellow-white title, then **"+follow"** in yellow; a typed recap list (1. 2. 3.) on the chest; small profile badge |

## Colours & type
White text everywhere; yellow only for the CTA keyword and highlighter; blue #0444A4 for the "smart" numbers and
actions; red only for loss/"recession". One sans family (Inter-like) + the occasional serif for article titles.

## Mapping to One Take looks
`typed_title` (hook, sentence case is fine) · `add-broll layout split` (main beat, 1.5–3 s each) · `layout full` for full-screen
images/B-roll · `highlight_card` (article + highlight, `push`) · `equation` (IF → THEN, blue accent) · `big_number` /
`count_up` (numbers, money) · `progress_ring` · `line_chart` (growth) · `checklist` with `tease: true` above the head
(numbered list that accumulates) · `name_badge` / photo + label (people) · `cta_keyword` ("Comment 'WORD'") then a
`typed_title` "+follow" · `logo_row` (companies) · `stock_chart` (a real ticker).
