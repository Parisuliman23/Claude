# Look F · "Class" (studied from Jess Inskip's reels)

Studied second by second from 5 of her reels (1:27–2:33 each): the 4-week series opener, "What is an ETF?",
"How to use an ETF screener", "How to automate ETF investing", and "The two axemen" (a story).

## The format: a finance class you can follow
Every video is an **episode of a series** with the same bookends, so viewers binge it in order:

| Time | Beat | On screen (One Take look) |
|---|---|---|
| 0–2 s | **Hook**: what you need to know / do first ("Before you pick an ETF, you need to know how to use an ETF screener") | two-tone title, typed on the words: white serif italic + big red caps (`jess_title`) |
| 2–4 s | **Promise / proof**: the payoff in one line | a checklist card ticking on each benefit (`jess_checklist`), or a screenshot |
| ~4 s | "**Class is in session**" | `jess_title` with `bell: true` (yellow school bell rings) + bell `ding` |
| ~5 s | "**Hi! I'm Jess**, welcome to another episode of…" | `jess_title` serif ("Hi! I'm:" small serif + name big serif) |
| ~6 s | **Series title** "I want to start investing / I don't know where to start / someone tell me what to do" | `jess_chalkboard` (title + handwritten + caps lines) |
| ~8 s | "**Today's lesson / topic:**" | `jess_composition` (marbled composition notebook, topic in purple handwriting, collage word) on a red page |
| body | **Teach**: a definition, then the steps, shown live | `class` layout (red page, screenshot/screen recording in a window, speaker in a soft-edged box below), `jess_chalkboard` for definitions and formulas, `jess_notes` (spiral notebook with marker highlights) for notes, kinetic keywords (`jess_title`: "MUTUAL *shared* FUND") |
| every 15–25 s | **A gag**: a meme / reaction face / object as a cut-out sticker | `jess_sticker` (Biggie with a crown, a shocked cat, Elmo, RuPaul, coffee cups…) |
| asides | "but that's a video for another day" | `jess_rec` (camcorder frame) |
| end | "**On the next LESSON…**" teaser + "leave me an apple for extra credit" + "**Class dismissed**" | `jess_title` ("on the next" serif + "LESSON…" red), `jess_apples`, `jess_title` with `bell` |

## Captions (`class-serif`)
Small white serif (DM Serif Display), 3–6 word fragments in the words she says, a soft shadow, **typed on with an
underscore cursor** (`gonna say more prob_`). In wide shots they sit just above the head; on a `class` page they sit
on the seam between the window and the speaker. Keywords get the big red caps treatment as a separate title, not
inside the caption.

## Type and colour
- Red caps: Rubik Black, red `#B41A1D`. Serif: DM Serif Display (italic for the soft words). Chalk: Cabin Sketch +
  handwriting in chalk white / yellow `#E9D86A` / pink `#E64FA8` / blue.
- The deep red page `#8E0C0E` behind screenshots, notes and the "today's lesson" notebook.
- Chalkboard green `#2E4636` with a wood ledge, white cards with soft shadows, green ticks `#2E9E4F`.

## Pace, camera and sound
- ~4.2 words/s, every pause cut. A new visual every 3–6 s (shot-change average 3.1–6.7 s across the 5 reels).
- Static camera: no punch-ins. Movement comes from the graphics: typing, ticking, pages, stickers popping.
- **Music bed sits right under the voice** (pauses are almost as loud as speech): volume ~0.2. Sound effects are
  sparse: the bell `ding` on "class is in session/dismissed", a `pop` on stickers, a paper swish on notes/boards.
- Section changes: the red **drip** (`add-fx` kind `drip`) or a hard cut.

## Where her information comes from (do the same)
- **The broker's own website, shown live**: she screen-records Fidelity (News & Research → ETF screener, a fund's
  detailed quote, Recurring investments) and talks through each click. Ask the user for a screen recording or
  screenshots of their broker/app for "how to" videos; put them in a `class` layout cut-away
  (`add-broll … "layout": "class", "src": "library/broll/screen.mp4"`). Missing → `src: null` (empty red page) +
  a `jess_notes` card listing the steps, and note what screenshot to add.
- **Primary sources** for facts: fund prospectus / fact sheet (investment objective, benchmark, holdings, sector
  exposure, expense ratio), the provider's site (e.g. the MIT history page for the first mutual fund), S&P/index pages.
  When the user states a fact, Claude checks it against these and writes the definition in plain words.
- **Her own notes** turned into graphics: definitions on the chalkboard, takeaways in the spiral notebook.
- **Visuals**: memes and reaction faces as cut-out stickers; simple illustrations (axemen, coffee cups, apples, a
  bell) that she generates or finds. In One Take: `image-find "coffee cup" --json '{"type": "vector"}'` (free
  Pixabay images, transparent PNGs come out as true die-cut stickers), the user's own `library/images`, or ask the
  user for the meme they want. Never use a real person's photo without the user's say-so.

## Not copied
Her face, name, series name and exact graphics belong to her. One Take reproduces the *style* (layout, timing, type
treatment, pacing) for the user's own series: name the series after them (e.g. "Debt-free class").
