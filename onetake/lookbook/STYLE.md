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

## ★ Look D · Notebook: MY PRIMARY STYLE (with Look E below; `style-pick` chooses)
Learned frame by frame from my favourite reference reel. Full breakdown: `lookbook/style/03-notebook-style.md`.
The talking head stays clean and natural; the story is told with **cream notebook cards** in the lower third, a
**one-word caption** on the chest, and **one yellow serif-italic keyword** per thought.

**Captions**: `set NAME caption_style --json '"notebook-word"'`. One word at a time, lowercase, Poppins ExtraBold
white with a soft shadow, centred on the chest (the import sets `caption_y` from the face: 0.555 when framed like
the reference, just above the head when the face is low), 2-frame dissolve between words. The ONE word that carries
each sentence (the payoff, a number, a contrast: "steal", "follows", "one", "choosing.") goes yellow serif italic:
`highlight NAME A-B` with that word's index from `show` (about one per sentence, never two in a row).

**Hook (frame 1 to ~3 s)**: `serif_hook` at y 0.185: `top` small white bold line, `mid` the big yellow serif-italic
phrase (the twist), `bottom` small white bold line, e.g. top "if you make your content", mid "the same day",
bottom "you post, we need to talk." It's on screen from the first frame (`anim_in` none) and hard-cuts off.

**Cards** (all `"anim_in": "rise"`, `"anim_out": "fade-quick"`, x ~0.47, **y = the `card_y` that `show` prints** (the import works it out from where the face is: ~0.70 when the
face is high like the reference, above the head when the face is low, e.g. in the car) so the face, the like/comment buttons and the
caption stay clear; one card at a time, each replaced when the thought changes, every ~3–6 s):
| They say… | Card |
|---|---|
| a question, a quote, a note to self, a list of examples | `notebook_note` (grey `label`, serif `title`, handwritten `lines` typed on; `tags` + `legend` to sort them) |
| a routine / "every day" / "the whole week" / a streak | `week_check` (checks land one day at a time; `filled` for today) |
| "step 1… step 6" (a process) | `step_tabs` at y 0.15 for the whole section, one overlay per step with the next `active` |
| 2–4 ideas, rules, types, jobs | `sticky_row` (notes fade in left to right, text fills in on cue; `focus` to dim the others) |
| "never do this", the old way, a blank page | `x_card` (crossed out, with a serif word + handwritten line beside it) |
| choosing between options / formats | `option_tiles` (`pick` turns the chosen one yellow) |
| "the more you do it…", growth, compounding | `growth_chart` (the curve draws itself to a yellow "you" dot) |
| a number, money, days, a result | `notebook_counter` (big serif number counts up on the word, yellow underline, handwritten note) |
| "follow me" | `follow_card` (my photo, name, @handle; the cursor clicks Follow) |
| "comment X" | `comment_cta` (yellow sticky: comment / KEYWORD / what they get), bottom-left, last 2–4 s |
**SYNC EVERYTHING TO MY WORDS (most important rule).** A card arrives on the word where I START talking about it
(`w0`) and leaves when the thought ends (`w1`). Everything INSIDE it happens on the exact word I say it: give any
timing param a word cue `{"w": <word index>}` (optionally `{"w": 57, "dt": 0.1}`) instead of seconds:
- `notebook_note`: `at` = one cue per line (the line types as I start saying it), `title_at`, `tags_at`, `legend_at`
- `week_check`: `checks_at` = one cue per day (the check lands on "Monday", "Tuesday"… or on each thing I list);
  `note_at`, `filled_at`
- `sticky_row`: `appear_at` (each note lands on its word) and `text_at` (its words fill in when I name it); `focus`
- `option_tiles`: `appear_at` per tile, `pick_at` on the one I choose, `under_at`
- `notebook_counter` / `count_up` / `big_number`: `count_at` on the number (it counts while I say it)
- `x_card`: `x_at` on "never"/"don't"/"stop"; `growth_chart`: `draw_at`; `follow_card`: `click_at` on "follow"
Only fall back to seconds when no word fits. Handwriting types at ~30 letters/s; things I list quickly can still
land 2 frames apart (0.067 s), like the reference.

**Palette**: cream paper `#F1EDE3`, ink `#1D1912`, grey labels `#908B86`, tab/day yellow `#F2E07F`, sticky `#EBD56E`,
keyword gold `#EED98A`. Fonts: Poppins (labels/captions), Playfair Display Italic (titles, keywords),
Architects Daughter (handwriting).

**Sound**: sparse and soft. `sfx-auto` gives each card one quiet paper `tap` as it lands, a `paper-swish` when the
step tabs change, and a `click` on the Follow button. No typing sounds, no whooshes on captions. The reference has
no noticeable music: voice only (or a very quiet bed, volume ≤ 0.05).

**Pace & camera**: cut every pause (the reference has only 4 pauses over 1/3 s in 2 minutes, ~4 words/s). Static
camera: no push-ins or punch-ins (`set NAME camera --json '{"push_in":0,"punches":[]}'`). Filter: none (natural).

## ★ Look E · Motion graphics (animated charts, slams, intros, transitions)
Learned from the HyperFrames catalog (charts, kinetic type, title cards, lower thirds, call-outs, transitions).
Clean white data cards, bold sans type, ONE accent (gold `#F5C542`, green `#16A34A` for up, red `#DC2626` for down).
Captions: `motion-pill` (2–3 words, caps, the spoken word on a gold pill). Everything is timed to my words with
word cues, exactly like Look D.

| They say… | Look | Key timing params (use word cues) |
|---|---|---|
| a number, money, a result | `slot_number` (digits roll and land) or `notebook_counter` / `count_up` | `roll_at` / `count_at` on the number |
| growth or decline over time ("debt went to zero", "it compounded") | `line_chart` (`direction` up/down, counts while it draws) | `draw_at` |
| comparing amounts / months / options | `bar_chart` (bars grow one by one, `highlight` the winner) | `bars_at` (one per bar), `grow_at` |
| a percentage, progress, a goal | `progress_ring` | `fill_at` |
| a big claim / "STOP doing this" / a twist | `headline_slam` (lands with a 3-frame shake, whips out) | `land_at`; `accent_words` |
| a punchy phrase said word by word | `kinetic_build` | `words_at` (one per word) |
| this vs that, before/after, myth vs fact | `compare_split` | `left_at`, `right_at`, `verdict_at` |
| introducing myself / a guest / a source | `lower_third` (y ~0.82, x ~0.3) | `open_at` |
| pointing at something on screen | `callout_circle` (place it ON the thing) | `draw_at` |
| a win, "paid it off", "done" | `success_check` + `confetti` | `at` / `burst_at` |
| a DM, a client question, a conversation | `chat_bubbles` | `at` (one per message) |
| the opening of a series / a chapter title | `title_card` (calm intro lockup, first 2–3 s) | — |
**Transitions** (on the word, with `add-fx NAME --json '{"kind": "whip", "w": 57}'`): `whip` (topic change),
`zoom` (punch into the key line), `flash` (cut through white into a reveal), `shake` (impact, a shocking number),
`glitch` (a myth / "wrong"), `light_leak` (warm, emotional moment). Max one every ~5 s; `sfx-auto` adds their sounds.
Place motion cards in the space the face leaves free (`card_y` from `show`, or y ~0.28 above the head).

## ★ Look F · Class (Jess Inskip-style finance class): ALWAYS make one version in this style
Full breakdown: `lookbook/style/04-class-style.md`. Every video is an episode of MY series, with the same bookends.
Captions `class-serif` (small serif fragments typed on with an `_` cursor). Hook = `jess_title`.
| They say… | Look / move |
|---|---|
| the hook (0–2 s) | `jess_title` parts `[{"t": "before you pick an", "s": "serif"}, {"t": "ETF", "s": "red"}]`, `at` = word cues |
| a keyword / term | `jess_title` (red caps + white serif italic words beside it, e.g. MUTUAL *shared* FUND) |
| benefits, a list, steps | `jess_checklist` (ticks land on each item's word: `at`) |
| "class is in session" / "class dismissed" | `jess_title` with `"bell": true` |
| "today's lesson / topic" | `jess_composition` on a red page (`add-broll` `src: null, color: "#8E0C0E"`, `over_captions: true`) |
| a definition, a formula, the series title | `jess_chalkboard` (top half, edge to edge) |
| notes, takeaways, a summary | `jess_notes` (spiral notebook, `==highlight==` words) |
| showing a website / app / screenshot | `add-broll … "layout": "class"` (red page, window on top, me in a soft box below) |
| a joke, a reaction, a metaphor | `jess_sticker` with an image (`image-find`, library, or ask me) every 15–25 s |
| "that's a video for another day" | `jess_rec` |
| "thank you" / outro | `jess_apples` then `jess_title` "class DISMISSED." with the bell |
| a section change | `add-fx` `drip` |
Static camera (no punch-ins), music bed at volume ~0.2, sparse sounds (`sfx-auto`).

## Versions: every edit comes in at least two styles
The main edit is in the `style-pick` style; `python3 -m engine variants NAME` then makes the **class** (Look F)
version of the same cut as its own project (`variants NAME motion notebook` for more). Style each version fully.
I pick my favourite in the studio; the phone page shows all of them.

## Choosing the style for each video (do this first)
Run `python3 -m engine style-pick NAME`. It reads the transcript and picks:
- **notebook** (Look D): steps, routines, tips, lists, a calm story → cream notebook cards + `notebook-word` captions.
- **motion** (Look E): numbers, money, growth/decline, comparisons, results, high energy → charts, counters, slams,
  transitions + `motion-pill` captions.
- **mix**: notebook cards for the steps and motion graphics for the data moments, with `notebook-word` captions.
Follow the pick unless I asked for a specific style. It also prints the word indexes of numbers, trends, comparisons
and steps: put the graphics on those words.

## Pick ONE look per reel (same timing rules, different skin)
| Look | When | Captions (`caption_style`) | Fonts in looks | Rhythm |
|---|---|---|---|---|
| **A · Warm creator** | personal, story, mindset | `warm-chest` (tiny word on the chest) or `warm-hand` (handwritten word beside the face) | heavy caps (`typed_title`, `keyword_def`) + handwriting (`hand_note`, `checklist`) | a new visual every 2–4 s |
| **B · Editorial serif** | teaching a framework, a breakdown | `editorial-serif` (one serif word left of the speaker) | serif/brush: set `font` to `InstrumentSerif_400Regular` / `CaveatBrush_400Regular`; persistent `chapter_header` | every 2–4 s |
| **C · Cinematic finance** | money, data, news | `cinematic-pill` (1–3 words on a dark pill) or `cinematic-bold` | Inter (`Inter_700Bold`, `Inter_800ExtraBold`); `big_number`, `highlight_card`, `equation` | a new shot every 1.5–4 s: split screens and B-roll |

**Default: run `style-pick` and use Look D, Look E or a mix of both.** Only use A/B/C if I ask for that look by name.

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
- Colour: keep my footage looking like it does on my phone. No colour filter unless I ask (no faded/lifted looks).
- Split screen over covering my face: any big graphic (chalkboard, definition, list, chart, notes, screenshot) or B-roll
  goes in a SPLIT SCREEN: graphic/clip in the top half, me in the bottom half with my whole face in view. Graphic on a
  panel = `add-broll NAME --json '{"w0":A,"w1":B,"src":null,"color":"#FFFFFF","layout":"split"}'` + the look at y ~0.25;
  footage = `"src": "library/broll/x.mp4", "layout": "split"`. Never lay a large card or chalkboard over my face.
  Small things (captions, a word, an emoji off to the side) can stay on top.
- (Claude adds preferences here as it learns them.)
