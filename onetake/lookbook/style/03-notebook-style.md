# Look D · Notebook: frame-by-frame breakdown

Measured from the reference reel (2:02, 720×1280, 30 fps). Sizes below are converted to One Take's 1080×1920.
Each element has a matching One Take look (in brackets).

## Rhythm
- Speech ~4.2 words/s, cut tight: only 4 gaps longer than 1/3 s in two minutes.
- A new card every ~3–6 s; a new section every ~15–20 s.
- Static camera, natural colour, no zooms, no B-roll. Everything happens in the lower third and the caption.

## Captions [caption style `notebook-word`]
- One word at a time, lowercase, centred, baseline ~55% down the frame (on the chest, under the mic).
- Poppins ExtraBold ~102 px, white, soft dark shadow (no outline, no box).
- Keyword in each thought: Playfair Display Italic, ~1.3× bigger, gold `#EED98A`.
  Examples: "steal", "follows", "one", "choosing.", "coworker", "opinion", "confident", "template".
- Word change: 1–2 frame cross-dissolve (old fades out while the new fades in). No pop, no bounce.

## Hook, 0:00–0:03 [`serif_hook`]
- Three stacked lines centred at y ≈ 0.19: small Poppins Bold white (~48 px) / big Playfair Italic gold (~110 px) /
  small Poppins Bold white. On screen from frame 1, gone when the first card arrives.

## Cards
All cards: cream `#F1EDE3`, radius ~10 px, soft shadow, ~76–82% of the frame width, centred, top edge at ~y 0.63.
**Enter**: fade in while rising ~1.5% of the frame over 6 frames (0.2 s) [`rise`]. **Exit**: fade out over 3 frames (0.1 s)
[`fade-quick`]. A card often appears empty first and fills in as it's talked about.

| Moment | Look | Details |
|---|---|---|
| 0:03 "the question I get asked most" | `notebook_note` | grey Poppins label; serif-italic title types ~24 letters/s; handwriting lines type ~30 letters/s; ruled lines every ~56 px |
| 0:09 "my exact process… a full week ahead" | `week_check` | 7 white day boxes with yellow MON–SUN tabs; serif note types at the top right; checks land **one per 2 frames**, left to right |
| 0:13 "by the end you'll know" | `notebook_note` | label + 2 handwritten lines, the second ends with a drawn → |
| 0:17 "step one" | `step_tabs` | 6 tabs at y ≈ 0.15 for the rest of the reel; the current one yellow, raised 4 px, bold; others cream with grey text |
| 0:19 "never sit down and come up with an idea" | `x_card` | small white "untitled" card, ghost text, crossed out; serif "never" + handwriting beside it |
| 0:23 "all week long, my notes app" | `notebook_note` | 4 handwritten lines added as they're said; circled letters (T/O/S) appear per line, the key fills a right-hand column |
| 0:39 "blank page → a menu to choose from" | `x_card` + sticky grid | crossed-out page, an arrow, a grid of small sticky notes |
| 0:43 "every Sunday night" | `week_check` variant / `notebook_note` | SUN tab + moon, "one batch session" in serif |
| 0:52 "each post has a job" | `sticky_row` | 4 yellow notes fade in 2 frames apart; serif numbers; icon + bold title + handwritten body fill in one by one; later the others dim (`focus`) |
| 1:13 "four, format" | `option_tiles` | 5 white tiles hanging from a rail with line icons; one turns yellow when picked; handwritten line underneath |
| 1:20 "five, film" | clapperboard + `notebook_note` | "why I batch film" with handwritten ✓ lines |
| 1:28 "confident + energetic… the more you do it" | `growth_chart` | grid paper, axes, an S-curve drawing itself, yellow dot + handwritten "you" |
| 1:31 "six, board" | kanban board | columns ideas / filming / editing / scheduled with yellow tags moving across |
| 1:40 two options | 2× `notebook_note` side by side | the chosen one turns yellow with a round "me" stamp |
| 1:57 "follow" | `follow_card` | dark navy profile card; the cursor clicks Follow → Following |
| 1:59 "comment BOARD" | `comment_cta` | yellow sticky: "comment" / BOARD (big serif italic) / "for my board template" |

## Sound
- Sparse. A ~30 ms bright paper tap as some cards land (e.g. 0:03.1); a ~90 ms airy swish as the step tabs appear (0:16.9);
  quick soft taps as the sticky notes land (0:52.2–0:52.4). No typing sounds. No noticeable music.
- One Take: `sfx-auto` uses `tap`, `paper-swish` and `click` for these looks.

## Not yet a one-click look
The kanban board (1:31) and the clapperboard (1:20). Build them from `notebook_note` / `sticky_row`, or ask Claude for a
custom look ("Describe it to Claude").
