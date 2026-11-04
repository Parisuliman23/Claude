# The editing style: design system

Built from 10 vertical talking-head reels (720×1280, 51–149 s, ~14.7 min total). See [`02-animation-breakdown.md`](02-animation-breakdown.md) for the moment-by-moment evidence behind every rule here.

---

## 1. The core idea in one sentence

**A single person talking to camera, where every noun, number and claim gets a visual receipt on the exact word it's spoken, and the edit stays out of the way when the moment is personal.**

Three things never change across all 10 videos:

1. **The talking head is the spine.** Graphics orbit the speaker. They don't replace them for long (except in the cinematic finance look).
2. **Visuals are triggered by words, not by time.** A name brings a face. A number brings a screenshot. A list brings a checklist. A feeling brings an emoji/meme. An ask brings an arrow.
3. **On-screen text paraphrases; it doesn't transcribe.** Headlines restate the *point* (`THE HUGE LAUNCHES ARE GETTING OUT OF HAND...`) while the speaker says something longer.

---

## 2. Three looks (same grammar, different skin)

The 10 videos fall into three families. They share the timing rules but use different type, color and density.

| | **A · Warm Creator (handwritten)** | **B · Editorial Serif** | **C · Cinematic Finance** |
|---|---|---|---|
| Videos | 01 Launch, 02 It-factor, 06 Marriage | 08 Reel breakdown, 09 Meta, (06 title) | 03 Top 1%, 04 3D world, 05 DCA, 07 Crash |
| Feel | Best friend spilling the tea | Magazine / strategist | Bloomberg-meets-Apple keynote |
| Shots | 1 take, 0–2 cuts, occasional punch-in | 1 take + PiP inserts | 15–67 full-frame changes (1.5–4 s per shot) |
| Headline font | Heavy geometric caps (Montserrat Black / Poppins ExtraBold) | High-contrast serif (Instrument Serif, Playfair, Bodoni Condensed) | SF Pro Display / Inter Bold, tight tracking |
| Secondary font | Thin handwritten pen (Nanum Pen Script-style) | Brush handwriting (Caveat Brush / Kalam Bold) | Clean serif for data labels (Tiempos/Georgia-like) |
| Captions | 1 word, tiny, handwritten or bold lowercase, **off to the side or on the chest** | 1 word, tiny **serif**, left of the speaker | 1–3 words, white on **dark translucent pill** or big bold with shadow, **center** |
| Graphic types | Emoji, meme clips, checklists, "KEYWORD =" formula cards, reel/revenue screenshots | Chapter header, PiP example clips, annotations with arrows, article highlights | Split screen, stock B-roll, charts that draw, counters, gauges, flowcharts |
| Color | White only on a warm, natural set | White only on a warm, golden set | White + one accent (royal blue / signal yellow / gauge green) |

Use **A** for personal, story, relationship and mindset content. Use **B** for teaching a framework or breaking something down. Use **C** for money, data and news.

Skit variant (10 · Money lies): A/C rules plus **red-box titles**, **B&W letterbox parody flashbacks**, speed lines, practical prop gags.

---

## 3. Composition

### Frame and subject
- **9:16, subject centered, eyes on the upper-third line** (≈ y 380–480 of 1280).
- Seated or desk-leaning, **chest-up to knees-up**. Wider for the warm/editorial looks (you see the chair, the room, the lamp); tighter for finance.
- **Symmetry** in the editorial and cinematic looks (centered chair, arched niches, seamless wall). Lived-in asymmetry in the warm look (shelves, frames, plants).
- **The mic is always visible** (handheld mini mic, stick mic, fuzzy windscreen, or lav). It's part of the creator look.

### The screen zones (720×1280 reference)

```
┌──────────────────────────┐  0
│   SAFE TOP (UI)          │
│ ─────────────────────────│ ~60
│  ZONE 1 · TITLE / HEADER │  headline, chapter header, CTA keyword,
│  (y 60–260)              │  emoji row, typed asides, numbered list
│ ─────────────────────────│ ~260
│  ZONE 2 · ABOVE THE HEAD │  screenshots, meme clips, reel covers,
│  (y 260–520)             │  charts composited into the set
│        ( face )          │
│ ─────────────────────────│ ~560
│  ZONE 3 · CHEST          │  captions (one word), proof cards held
│  (y 560–900)             │  "in the hands", keyword slams, recap list
│ ─────────────────────────│ ~900
│  ZONE 4 · LAP / LOWER    │  PiP example clips, profile cards,
│  (y 900–1150)            │  headline cards sliding up, disclaimers
│ ─────────────────────────│ ~1150
│   SAFE BOTTOM (UI)       │
└──────────────────────────┘ 1280
```

Rules:
- **Never cover the face.** Graphics go above the head, on the chest, or at the lap. The one exception is the deliberate dim-and-stack in V09, where the background is darkened first.
- **Proof that belongs to the speaker sits low** (revenue dashboard, portfolio cards, their own posts) so it looks like they're holding it. **Proof about others sits high** (other creators' reels, news headlines, people photos).
- **Persistent structure lives top-left or top-center** (running checklist, `STRUCTURE:` header) and stays the whole section.
- **Captions avoid dead center in the warm/editorial looks** (to the left of the face, or on the chest), but **are dead center in the finance look**.
- **Split screen (C look):** top 50% = visual, bottom 50% = speaker framed head-to-desk, caption pill on the seam.

### Layering and depth
- **Cards** (screenshots, articles, charts) get a **white rounded rectangle, 12–20 px radius, soft shadow or white outer glow**.
- **Dim/blur the background** when stacking several receipts (V07, V09): about 40–60% darkness or a heavy Gaussian blur of the speaker behind.
- **Rotoscope the speaker in front of a collage** for a "wall of evidence" open (V08).
- **Composite data into the set** (V03): charts and gauges sit on the seamless wall above the head with no card, as if printed on the backdrop.

---

## 4. Color

### Palette principle
**The set gives the color; the graphics stay white.** About 90% of overlay text is pure white `#FFFFFF`. Color is used only to *mean* something.

### Set and wardrobe palettes (sampled medians)

| Video | Wall / set | Wardrobe | Mood |
|---|---|---|---|
| 01 Launch | taupe `#7A7061`, dark navy door, warm lamp | olive knit `#787A62` | earthy, cozy |
| 02 It-factor | peach wall `#B89A84` + orange sunset-lamp glow | black + white piping | golden hour |
| 03 Top 1% | sage/grey seamless `#796B5E`→`#9AA79C`, walnut desk | grey plaid | cinematic, cool-neutral |
| 05 DCA | white/grey minimalist `#959795` | black | Apple-clean |
| 06 Marriage | cream office | **cobalt** `#2C53AE` | bright, one bold color |
| 07 Crash | grey wall `#585A54`, window light | pale blue oxford | moody news |
| 08 Breakdown | cream arches `#BA9970`, warm lamps | **hot pink** `#D3668C` | editorial glam |
| 09 Meta | warm beige `#9E9582` + plant | charcoal tee | soft home |
| 10 Money lies | grey kitchen, wood board | white linen + **orange peppers** | bright, prop-driven |

Takeaways:
- **Warm, practical lighting** (lamps, sunset projector, window light) is in 8 of 10. Skin tones lean warm.
- **One saturated wardrobe/prop color** against a neutral set (cobalt, hot pink, orange peppers, olive) does the color work. Graphics don't compete with it.
- The cinematic look grades **slightly desaturated with lifted blacks**. B-roll is moody (teal-orange, dark trading screens).

### Accent colors (meaning-coded)

| Color | Hex (sampled) | Meaning | Where |
|---|---|---|---|
| Highlighter yellow | `#FCFC04` / `#DCDC64` | "Read *this* part of the receipt" | Article/number highlights (03, 07, 09) |
| CTA yellow | `#FCF46C` | The keyword you must comment | `'ALERT'`, `+follow` (07) |
| Signal red | `#FC1404` | Title / alarm / "wrong" | Red-box titles, `WRONG ✗`, RECESSION, losses (07, 10) |
| Royal blue | `#0444A4` | The "smart" number / the action | `$2,400`, `/`, `=`, `BUY +$800` buttons (05) |
| Gauge green | `#044C34` (+ market green) | Growth, allocation, buy zone | Radial gauge, demand-zone box (03, 09) |
| Magenta + blue | chart defaults | Data series | Area charts (03) |

**Never more than one accent on screen at a time.**

---

## 5. Typography

### The pairing rule
**One loud face + one human face.** Always a contrast pair:

| Role | Warm look | Editorial look | Finance look |
|---|---|---|---|
| **Headline / keyword** | Heavy geometric ALL CAPS: Montserrat Black, Poppins ExtraBold, Archivo Black. Tracking 0 to +2% | High-contrast serif: Instrument Serif, Playfair Display, condensed Bodoni (`STRUCTURE:`). Title case or caps | SF Pro Display / Inter Bold, **tracking −3 to −5%**, sentence case. Extra-wide heavy caps (Druk Wide / Clash Display style) for one-word slams |
| **Human voice** (asides, lists, definitions, CTAs) | Thin handwritten pen print, lowercase, uneven baseline (Nanum Pen Script / Reenie Beanie style) | Brush handwriting, bold (Caveat Brush / Kalam Bold) | Small serif in parentheses: `(watch this before may 15…)`, `(They just do this one thing differently)` |
| **Captions** | 1 word, handwritten or bold lowercase sans, ~22–28 px | 1 word, serif (Times-like), ~22 px | 1–3 words, Inter/SF Semibold 26–34 px on pill, or **Bold 44–56 px with shadow** |
| **Data** | n/a | Inter in cards | Inter / SF Pro numerals. Serif for chart titles |

### Type behaviours that repeat
- **Ellipsis bridges** `...` at the end of a card and the start of the next carry one sentence across two beats.
- **Equation cards**: `BE CLEAR =` / `SURPRISE ME =` / `A. B. C. D = Successful Launch` / `IF VIX > 30 → BUY +$800`. The `=` and `→` act as a teaching device.
- **Emphasis by switching style inside a line**: `YOU` caps inside lowercase handwriting, `HABIT` italic + underline, `what` underlined, `NEVER` caps.
- **Quotes around names and keywords**: `"MY NON-EXPERT LAUNCH"`, `'ALERT'`, `'DESK'`, `comment "WORLD"`.
- **Viewer's inner voice**: definitions are written as what the *audience* thinks (`i need to understand what you're trying to say to me`, `monotone or too predictable = i'm scrolling`).
- **Asterisk honesty**: `Correlated*`, `26x*`. Fix overstatements on screen instead of re-recording.
- **Numbered lists use `1.` with a space, lowercase items** in the handwritten look, Title Case in the finance look.

---

## 6. Objects and asset library

What actually gets put on screen, ranked by how often it appears:

1. **Screenshots as proof** (all 10): revenue dashboards, brokerage balances, IG posts and engagement bars, profile cards, Discord alerts, captions, app UIs.
2. **News/article snippets with highlights** (03, 07, 09): headline cards, paragraph crops, data tables.
3. **Charts that draw** (03, 05, 07, 09): line charts, area charts, dot plots, radial gauges, tree diagrams, flowcharts.
4. **Text-only structure** (all): titles, chapter headers, running checklists, formula cards.
5. **Emoji** (01, 02, 08): 🤯😳🧩☕😎👇🅱️. Single or in rows of 2–3, above the head.
6. **Meme / reaction clips** (02, 08): famous-meme GIFs in a rectangle, often with a handwritten label.
7. **Personal photos/clips** (06, 08): couple photos, family PiP, stage photo.
8. **Stock and archival B-roll** (03, 05, 07): NYSE, Wall St bull, trading floors (B&W archival for gravitas), slot machines, neon tickers, data centers.
9. **Hand-drawn marks**: curved arrows, straight draw-down arrows, red ✗, green draw-around boxes, underlines.
10. **Cross-promo thumbnails** (05, 07, 09): the creator's own past videos as small vertical cards.
11. **Practical props** (10): food as a metaphor (pepper = money), wigs as characters, a pet for the warm close.

---

## 7. Motion language

| Element | Entry | Duration | Easing | Exit |
|---|---|---|---|---|
| Screenshot / card / emoji / meme | **Hard pop** (0–1 frame) or **scale pop** 40→100% | ≤ 3 frames | none / quick ease-out | Hard cut on the next topic |
| Headline (heavy caps) | **Typewriter** ~30–35 chars/s, or static from frame 1 in the hook | 0.5–0.8 s | linear | Hard cut |
| Handwritten aside / list item | **Typewriter** ~20–25 chars/s, sometimes with a visible cursor | 0.5–1.5 s | linear | Stays until the section ends |
| Arrow / box / ✗ | **Stroke draw-on** | 0.3–1.0 s | ease-out | Hard cut |
| Counter / gauge / chart line | **Count-up + draw** together | 1.2–1.3 s | **ease-out** (fast start, slow settle) | Hard cut |
| Highlighter | Left→right sweep | ~0.75 s | linear | Stays |
| Article / chart / UI | **Slow push-in or pan** the whole time it's on screen | continuous | linear | Hard cut |
| Headline card (news) | **Slide up from the bottom** | ~0.2 s | ease-out | Hard cut |
| Receipt stack | Background dims, cards **dissolve/slide in** one per phrase | 0.2–0.3 s each | ease-out | All clear together |
| Keyword CTA | **Double-blink** (on 1 f / off 3 f / on) or scale pop | 0.15 s | — | Stays until the end |
| Punch-in | 100 → ~110–115% digital zoom on a cut | instant | — | Next punch |
| Hook push-in | Slow zoom through the first 5–10 s | continuous | ease-in-out | — |
| Parody flashback | Cut to **B&W + letterbox bars**, label scale-pops | instant | — | Practical gag / whip back to color |

**Rhythm:** a new visual event every **2–4 seconds** in the warm and editorial looks, every **1.5–2 seconds** in the finance look. Speakers talk at **185–265 wpm (median ~228)**, so captions swap 3–4 times per second.

---

## 8. The decision engine: what to show for what's said

Run every sentence of the script through this:

| If the speaker says… | Show… | Where | How |
|---|---|---|---|
| A **person's name** | Their photo / reel cover / profile card. TV-style name super for public figures | Above head (others) / lower third (self) | Hard pop on the name |
| A **brand or tool** | White rounded logo badge (`Replit`) | Chest or over B-roll | Pop. Repeat when it's said again |
| A **number they earned or own** | Their dashboard/balance screenshot | Chest/hands | Hard pop on the number |
| A **number from research** | Article crop + yellow highlight on the number, or a counter/gauge | Top or split | Highlight sweep / count-up |
| A **comparison** ("from this to this") | Two cards side by side | Hands | Pop on each "this" |
| A **process / formula** | Equation or flowchart (`$12,000 / 12 = $1,000`, `IF → THEN`) | Top panel or split | Build term by term as it's spoken |
| A **list** ("first, second, next, lastly") | Running numbered checklist that accumulates. Optionally blur future items | Top-left / top-center | Type each item on its number |
| A **section change** | Chapter header (`STRUCTURE:` + step) or heavy-caps audience call-out (`IF YOU'RE A…`) | Top | Typewriter |
| A **definition / principle** | `KEYWORD =` + handwritten definition in the viewer's voice | Top | Caps pop, definition types |
| A **metaphor** (casino, puzzle, magnetic) | The literal image (slot machine, 🧩, cat pouncing) | Above head / split | Pop |
| An **emotion / reaction** | Emoji row or meme clip with handwritten label | Above head | Pop |
| **Something personal** (pregnant, husband, son) | Handwritten note + curved arrow pointing at it / personal photo or PiP | Next to the body | Pop |
| A **past video / episode** | Vertical thumbnail(s) of that video | Lower center | Pop |
| A **contrarian claim** ("Wrong.", "False.") | Red ✗ / `WRONG` / B&W parody of the old belief | Chest | Draw-on ✗ |
| An **overstatement** | Asterisk correction (`Correlated*`) | Chest | Pop |
| The **CTA** ("comment X") | Keyword in quotes, biggest type in the video, + arrow or what they'll get | Top | Double-blink / scale pop, on the keyword |
| A **sincere close** ("thank you for being here") | **Nothing.** Clean frame, maybe a punch-in | — | — |

---

## 9. Video structure template (beat sheet)

Every reel follows roughly this shape. Times are for a ~90 s piece.

| Beat | Time | Edit treatment |
|---|---|---|
| **1. Hook** | 0–5 s | Headline on screen from frame 1 (paraphrased claim) + subline (identity or urgency). Proof visual within the first 2 s (dashboard, chart, wall of thumbnails). Slow push-in or rapid B-roll underneath |
| **2. Credibility** | 5–20 s | Proof screenshots stacking, name supers, profile card, "I told you so" receipts |
| **3. Promise / map** | ~20–40 s | Typed paraphrase of the promise ("…but I can show you everything I did"). A checklist or numbered list previews the content (blur unrevealed items) |
| **4. Body** | 40–80% | Section headers + formula cards + one visual per claim. Running checklist keeps the place. A meme/emoji every ~15–20 s for relief |
| **5. Audience call-out** | late body | `IF YOU'RE A … / OR IF YOU'RE A …` caps cards |
| **6. CTA** | last 10–15 s (or mid-video at peak attention) | Keyword in quotes, largest type, accent color, arrow. Show what they'll receive (Discord card, portfolio, app) |
| **7. Clean close** | last 3–5 s | Graphics off. Warm sign-off or humble note (`all that to say… we're still a work in progress`) |

---

## 10. Do / Don't

**Do**
- Put the visual on the exact syllable of the noun or number.
- Paraphrase the headline into a punchier claim than the spoken line.
- Keep a running list or chapter header on screen through multi-part content.
- Show receipts (screenshots, articles, dashboards) for every claim of fact or money.
- Use one saturated color in wardrobe/props and keep graphics white.
- Let the most personal moments breathe with no graphics.
- Push in slowly on any static screenshot or article so it never sits dead.

**Don't**
- Don't cover the face (dim the background first if you must stack over it).
- Don't fade out slowly. Cut graphics off on the topic change.
- Don't use more than one accent color at once, or more than two typefaces plus captions.
- Don't transcribe whole sentences as titles.
- Don't let captions become the main graphic (keep them small in the warm/editorial looks).
- Don't make the CTA generic. It's always a specific keyword in quotes.

---

## 11. Build recipe (CapCut / Premiere / After Effects)

1. **Transcript first.** Auto-caption, then go line by line through the decision engine (§8) and mark each noun, number, list, emotion and CTA.
2. **Captions:** pick the family (A/B/C). Set to 1 word (A/B) or 2–3 words (C). Position per §3.
3. **Hook layer:** headline + subline from frame 1, plus a proof asset by 2 s. Add a 5–10 s slow zoom (A/B) or 0.5 s B-roll swaps (C).
4. **Proof layer:** drop screenshots on their words. White card, 16 px radius, soft shadow or 6 px white glow. Hard pop in, hard cut out.
5. **Structure layer:** the running list or chapter header on its own track, typewriter in, held for the section.
6. **Feel layer:** emoji/meme every 15–20 s, never over the face.
7. **Motion polish:** slow push on every static image. Ease-out for counters, arrows and draw-ons. Punch-ins (110–115%) at thought changes.
8. **CTA:** quoted keyword, the biggest type in the piece, accent color, double-blink on the spoken keyword.
9. **Clean out:** last 3–5 s with no graphics.
10. **Check:** pause on any random frame. There should be exactly one obvious thing to look at.
