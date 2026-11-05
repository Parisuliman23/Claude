# My editing style

Claude follows this on every edit. Full detail lives in `lookbook/style/01-style-guide.md` (design system)
and `lookbook/style/02-animation-breakdown.md` (every animation in my 10 reference reels, with timing).
Read this file every time; open those two when you need specifics.

## Core idea
A single person talking to camera. **Every noun, number and claim gets a visual receipt ON THE EXACT WORD
it's spoken.** The edit gets out of the way when the moment is personal.
1. The talking head is the spine. Graphics orbit the speaker.
2. Visuals are triggered by WORDS, not time: set `w0` to the word that triggers it.
3. On-screen text PARAPHRASES the point; it never transcribes it. No full-sentence titles.

## Pick ONE look per reel (same timing rules, different skin)
| Look | When | Captions (`caption_style`) | Fonts in looks | Rhythm |
|---|---|---|---|---|
| **A · Warm creator** | personal, story, mindset | `warm-chest` (tiny word on the chest) or `warm-hand` (handwritten word beside the face) | heavy caps (`typed_title`, `keyword_def`) + handwriting (`hand_note`, `checklist`) | a new visual every 2–4 s |
| **B · Editorial serif** | teaching a framework, a breakdown | `editorial-serif` (one serif word left of the speaker) | serif/brush: set `font` to `InstrumentSerif_400Regular` / `CaveatBrush_400Regular`; persistent `chapter_header` | every 2–4 s |
| **C · Cinematic finance** | money, data, news | `cinematic-pill` (1–3 words on a dark pill) or `cinematic-bold` | Inter (`Inter_700Bold`, `Inter_800ExtraBold`); `big_number`, `highlight_card`, `equation` | a new shot every 1.5–4 s: split screens and B-roll |

Debt / money / investing content → usually **C**. Personal story → **A**. Step-by-step lesson → **B**.

## Where things go (y = 0 top, 1 bottom)
- **Zone 1 · y 0.06–0.20** (center ~0.12): hook headline, chapter header, CTA keyword, emoji row, typed asides, numbered list.
- **Zone 2 · y 0.20–0.40** (~0.30), above the head: screenshots, memes, other people's content, charts.
- **Zone 3 · y 0.44–0.70** (~0.57), chest: captions, proof cards "held in hands", keyword slams, recap list.
- **Zone 4 · y 0.70–0.88** (~0.80), lap: picture-in-picture, profile cards (`name_badge`), headline cards.
- **NEVER cover the face.** If you must stack over it, set `"dim": 0.5` on the overlay.
- The speaker's OWN proof sits low (Zone 3/4). Proof about OTHERS sits high (Zone 2).
- Persistent structure (running checklist, chapter header) stays top-left/top-center for the whole section:
  one overlay spanning the section's words, `x` ~0.3 for top-left.
- Check every new look with `still NAME <seconds>`: the face must stay clear and captions must not cover the mouth.

## Color
- ~90% of overlay text is pure white. The set and wardrobe provide the color.
- Accents only with meaning, **max ONE on screen at a time**:
  highlighter yellow `#FCFC04` = "read this part" · CTA yellow `#FCF46C` = comment keyword ·
  signal red `#FC1404` = title/alarm/"wrong" · royal blue `#0444A4` = the smart number/action · green `#044C34` = growth.

## Typography
- Always ONE loud face + ONE human face (+ captions). Never more than 2 typefaces.
- Ellipsis bridges: end a card with "..." and start the next with "..." to carry a sentence across beats.
- Equation cards: `keyword_def` ("BE CLEAR =" + definition) and `equation` ("IF VIX > 30" → "BUY +$800").
- Emphasis by style switch inside a line: a CAPS word in handwriting (YOU), or _underline_ (write `_HABIT_`).
- Keywords/names in quotes: "MY NON-EXPERT LAUNCH".
- Write definitions in the VIEWER's inner voice ("i need to understand what you're trying to say to me").
- Asterisk honesty: fix overstatements on screen (Correlated*, 26x*).

## Motion (all built in)
- Cards, screenshots, emoji, memes: `"anim_in": "snap"` (40→100% in ~3 frames) or `"none"` (hard pop).
  Exit: `"anim_out": "none"` (hard cut on topic change). **No slow fades.**
- Headlines: `typed_title` types at ~33 letters/s, starting on the first spoken word.
- Handwritten asides and list items: `hand_note` / `checklist` type at ~20–25 letters/s (cursor optional).
- Arrows, boxes, ✗: `arrow`, `red_x`, the arrow inside `hand_note` all draw on (0.3–1.0 s, ease-out).
- Counters: `big_number` / `count_up` count with ease-out over ~1.25 s.
- Highlighter: `highlight_card` sweeps left→right over ~0.75 s.
- Any static screenshot/article: `"push": true` (slow push-in the whole time it's on screen).
- News headline cards: `"anim_in": "slide-up"` (0.2 s).
- Receipt stack: several cards with `"dim": 0.5`, one per phrase, all ending on the same word (they clear together).
- CTA keyword: `cta_keyword` double-blinks on, ON the spoken keyword.
- Camera: a slow push-in through the hook (`camera.push_in` 5–10 s, on by default) and a **punch-in (112%) at
  each thought change**: add the word index to `camera.punches` (they toggle in/out).
- Lists ACCUMULATE (never swap items) and clear all at once at the section end.
- **Last 3–5 s: clean**, no graphics (or only the CTA).
- Speech is fast (~185–265 wpm): keep cuts tight.

## Decision engine: what to show for what's said
| They say… | Show (One Take tool) | Where |
|---|---|---|
| A person's name | their photo/reel cover (library image, or `assets/placeholder.png`) or `name_badge` with their photo; TV-style name super for public figures | Zone 2, snap on the name |
| A brand/tool | `name_badge` (logo image if in the library). Repeat it when they say it again | Zone 3 |
| A number they earned/own | their dashboard screenshot (placeholder if missing), or `big_number` | Zone 3 (chest) |
| A number from research | `highlight_card` (article text + highlighted phrase, `push: true`) or `big_number`/`count_up` | Zone 2 |
| "From this… to this" | two cards side by side (x 0.3 and 0.7), each snapping on its "this" | Zone 3 |
| A process/formula | `equation` built term by term (`right_at` = when the result is said) or a `checklist` | Zone 1–2 |
| A list ("first… next… lastly") | `checklist` with `at` = seconds from its start for each item; `tease: true` blurs future items | Zone 1 |
| A section change | `chapter_header`, or an audience call-out with `typed_title` ("IF YOU'RE A…") | Zone 1 |
| A definition/principle | `keyword_def` ("KEYWORD =" + definition in the viewer's voice) | Zone 1 |
| A metaphor (casino, puzzle) | the literal image: emoji (`emoji_row`) or a library image/B-roll | Zone 2 |
| Emotion/reaction | `emoji_row`, or a meme clip/GIF + `hand_note` label | above the head |
| A personal detail | `hand_note` with an `arrow` pointing at it, or a personal photo | beside the face |
| Their past video | its vertical thumbnail (library image) | Zone 4 |
| Contrarian "Wrong." | `red_x` (2 strokes) | Zone 2 |
| An overstatement | a `hand_note` with the asterisk correction | Zone 3 |
| CTA "comment X" | `cta_keyword` (keyword in quotes, biggest type, CTA yellow, + arrow); say what they'll get in `question` | Zone 1 |
| A sincere close | NOTHING. A clean frame | — |
| Look C B-roll/graphic beats | `add-broll` with `"layout": "split"`: top half = clip/image or a white panel (`"src": null, "color": "#FFFFFF"`) with a graphic on it (place the look at y ~0.25); captions sit on the seam automatically | split |

**Missing an asset** (a screenshot, dashboard, photo or logo they mention)? Add an image overlay with
`"src": "assets/placeholder.png"` at the right word and zone, put what's needed in its `note`, and list them in
your summary. The user taps it in the studio → Swap.

## Beat sheet (~60–90 s reel)
1. **Hook 0–5 s**: a paraphrased headline from frame 1 (`typed_title`, Zone 1) + an identity/urgency `sub` line + a proof visual by 2 s.
2. **Credibility 5–20 s**: stacked receipts, name supers, a profile card.
3. **Promise/map ~20–40 s**: a typed paraphrase of the promise + a checklist preview.
4. **Body**: section headers, formula cards, one visual per claim, a meme/emoji every 15–20 s.
5. **Audience call-out**: "IF YOU'RE A… / OR IF YOU'RE A…".
6. **CTA** (at the end, or mid-video at peak attention).
7. **Clean close**: last 3–5 s with no graphics.

## Don'ts
No covering the face. No slow fade-outs. No more than one accent color. No more than 2 typefaces + captions.
No full-sentence titles. Captions never become the main graphic (looks A/B). No generic CTAs: always a
specific keyword in quotes.

## Things I've told Claude
- (Claude adds preferences here as it learns them.)
