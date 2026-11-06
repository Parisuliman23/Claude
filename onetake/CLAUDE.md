# One Take Studio — how Claude edits reels here

You are the editor behind a reels studio. The user films like normal, drops the
clips in `drop-in-order/`, and says something like **"I have a new reel to edit"**.
You do the rough cut and first styling pass, then open the **studio** (a local web
page) where the user sees everything live and stays in creative control.
Nothing is rendered until they press **Lock in my looks**.

All commands run from this folder: `python3 -m engine <command>`.
Run `python3 -m engine` with no arguments for the full list.

## Folder map

| Path | What it is |
|---|---|
| `drop-in-order/` | Raw clips for the next reel, used in name order |
| `projects/<name>/project.json` | The whole edit (words, cuts, looks, sound…) |
| `projects/<name>/exports/` | Rendered reel, CapCut pack, carousel, story, trial reels |
| `library/gifs`, `images`, `broll`, `sounds` | The user's media library |
| `lookbook/captions.json` | Caption styles |
| `lookbook/looks/*.py` | Built-in looks (animated graphics); `custom/` = looks you made |
| `lookbook/saved.json` | Looks the user saved to their lookbook |
| `lookbook/STYLE.md` | **The user's editing taste. Read it before every edit, update it as you learn.** |
| `engine/` | The engine (Python). `app/` = the studio (HTML/JS) |

## New reel workflow ("I have a new reel to edit")

1. **Check the clips.** List `drop-in-order/`. If it's empty, ask the user to drop their clips in
   (any phone video works; they're joined in file-name order).
   First time on this computer? Run `python3 -m engine setup` and fix anything it reports.
2. **Import.** `python3 -m engine new [short-name]` — joins clips into a 9:16 master,
   transcribes word by word, and makes the automatic rough cut (filler words, false starts,
   repeated takes — the last take is kept). Takes a minute or two. If you don't know the topic yet,
   leave the name out and give it a title once you've read it: `set NAME title --json '"Bye CapCut"'`.
3. **Review the cut like an editor.** `python3 -m engine show <name>` prints numbered lines with word
   indexes; cut words are in `[brackets]`. Read the whole thing, then tighten it:
   - Remove remaining false starts, repeated sentences, "wait let me say that again", rambling asides.
   - When a line was said twice, keep the stronger/cleaner take (usually the later one).
   - The first 1–3 seconds must be the hook — cut any warm-up before it.
   - Never change the meaning or cut the punchline. When unsure, keep it; the user can cut in the studio.
   - Commands: `cut NAME A-B`, `restore NAME A-B` (word indexes), `cut-line NAME L`, `restore-line NAME L`.
   - Fix words the transcript misheard (they become the captions): `retext NAME A-B "friend"`. Watch for
     names, brands, money amounts and odd words that don't fit the sentence. The user can also
     double-click a word in the studio to fix it.
4. **Styling pass: edit in the user's style.** Read `lookbook/STYLE.md` first (it's the rulebook; the
   full analysis of their 10 reference reels is in `lookbook/style/`). Then:
   - **Pick the look** (A warm creator / B editorial serif / C cinematic finance) from the content and set the
     matching caption style: `set NAME caption_style --json '"warm-chest"'` (ids in `lookbook/captions.json`).
   - **Hook (0–5 s)**: the import adds a `typed_title` hook. Rewrite it as a PARAPHRASED claim (not the
     transcript), all caps, ≤ 8 words, plus an identity/urgency `sub` line:
     `overlay NAME <hook-id> --json '{"params": {"text": "...", "sub": "..."}}'`. Add a proof visual by 2 s.
   - **Walk the transcript word by word with the decision engine** in STYLE.md: every noun, number and claim
     gets a visual ON the word it's spoken (`w0` = that word). Built-in looks for this style:
     `typed_title` (headline / audience call-out), `hand_note` (handwritten aside, optional arrow),
     `keyword_def` ("KEYWORD =" + definition), `checklist` (running list; `at` = seconds per item, `tease`),
     `chapter_header`, `cta_keyword` ("comment KEYWORD"), `red_x` (wrong), `highlight_card` (receipt with
     highlighter), `big_number` / `count_up` (counters), `emoji_row`, `equation` (IF → THEN), `name_badge`
     (person/brand/profile), `arrow`. Run `python3 -m engine` for every command; params are listed in each
     look's file in `lookbook/looks/`.
     Example: `add-overlay NAME --json '{"kind":"look","look":"keyword_def","w0":120,"w1":140,"y":0.13,"params":{"keyword":"BE CLEAR","definition":"i need to understand what you are saying"}}'`.
     Media: `{"kind":"image","src":"library/images/x.png","scale":0.6,"push":true}`, `{"kind":"gif",...}`,
     `{"kind":"emoji","emoji":"1f633","scale":0.15}` (codes = files in `assets/emoji/`).
     Missing screenshot/photo/logo → `"src":"assets/placeholder.png"` with a `note`, and list it in your summary.
   - **Placement**: zones and the never-cover-the-face rule are in STYLE.md (x, y = 0–1 fractions; `scale` =
     width fraction, looks: 1 = natural size). Their own proof low, others' proof high. `"dim": 0.5` when stacking.
   - **Motion**: `"anim_in": "snap"` or `"none"`, `"anim_out": "none"` (hard cuts; no fades); `"slide-up"` for
     headline cards; `"push": true` on static screenshots.
   - **Camera**: the hook push-in is on by default. Add a punch-in at each thought change:
     `set NAME camera --json '{"push_in":7,"push_amount":0.08,"punch_scale":1.12,"punches":[42,97,160]}'`
     (word indexes where a new thought starts).
   - **B-roll**: when a moment needs footage (a metaphor like "casino", an emotion like "panic selling", or
     look C's 1.5–4 s shot rhythm), check `library/broll/` first; if nothing fits, download free stock clips:
     `python3 -m engine broll-find "slot machine casino" --n 3` (Pixabay, free to use). If it says the
     key is missing, tell the user to add their free Pixabay key (studio: Add media → Videos) and carry on with
     white panels/graphics instead. Name searches by what's literally on screen ("red stock ticker falling").
   - **Look C** cut-aways / split screens: `add-broll NAME --json '{"w0":50,"w1":61,"src":"library/broll/x.mp4","layout":"split"}'`
     (`"src": null, "color": "#FFFFFF"` = white panel; put an `equation`/`highlight_card` look at y ~0.25 on it).
     Optional: `"trans": "fade"` (cross-dissolve in/out; default is a hard cut, which suits this style) and
     `"audio": "under"` (the clip's own sound plays quietly under the voice; default muted).
   - **Rhythm check**: a new visual every 2–4 s (A/B) or 1.5–2 s (C), a meme/emoji every 15–20 s, an audience
     call-out, a specific CTA keyword, and the **last 3–5 s clean**. Use `show NAME` to check coverage.
   - Color: `set NAME filter --json '"moody-finance"'` (ids in `lookbook/filters.json`: warm, moody-finance,
     bright-clean, punchy, cool, bw). Look C usually suits `moody-finance`.
   - Caption breaks: put `"cbreak": true` on a word to start a new caption there (e.g. to land a punchline alone).
   - Captions: must not cover the mouth/chin (side/chest styles avoid this). If needed: `set NAME caption_y --json 0.62`.
   - **Captions already in the video** (e.g. a CapCut export): the import detects them and paints them out
     (`burned_captions.remove`), then ours replace them. If it missed some (text in a `still`): `remove-captions NAME`.
   - Sound: pick a music bed from `library/sounds/` that fits the energy:
     `set NAME sound --json '{"src":"library/sounds/<file>","volume":0.12,"offset":0}'`.
   - **Sound effects** (every moment that moves has a sound): once the looks are placed, run
     `python3 -m engine sfx-auto NAME`. It matches each look/cut-away/punch-in to an effect (pop on a snap, whoosh
     on a slide or punch-in, typing under typed text, riser + ka-ching on money counters, ding on the CTA). To
     change one, edit `sfx` with `set NAME sfx --json '[…]'` (each: `src`, `anchor` {"ov": id} / {"broll": id} /
     {"w": word}, `offset` s, `volume`, `muted`); `sfx-list` shows every effect. Keep the last 3–5 s quiet too.
   - **Safe area**: `python3 -m engine edge-check NAME` lists looks hidden under Instagram's top bar, caption/username
     area or right-side buttons, or running off the frame; `--fix` moves them in. Run it before opening the studio.
   - **Check your work**: `still NAME <seconds>` → look at `projects/NAME/cache/still.png` for the hook, a busy
     moment and the CTA. Face clear? One accent color? Text readable? Fix before opening the studio.
5. **Open the studio** in the background: `python3 -m engine open NAME` and tell the user it's at
   http://localhost:5178 (on a Chromebook: http://penguin.linux.test:5178, which the command prints). Give a 3–5 bullet summary of what you cut and styled, and remind them:
   they can bring back anything you cut, swap any look, and nothing renders until **Lock in my looks**.
6. **CapCut**: if the user wants to keep editing in CapCut, `python3 -m engine export NAME capcut-project` writes a real
   CapCut project (cut on the original footage, each look on its own track, editable caption text, every sound its own
   clip). On a computer with CapCut desktop it lands straight in CapCut's projects; otherwise it's a zip with one-click
   installers (Windows/Mac). `export NAME capcut` makes a layer pack for any other editor.
7. Don't render the final reel yourself unless asked — that's the user's "lock in" moment.
   (If they ask: `python3 -m engine render NAME`.)

## Studio requests

The studio sends requests to you ("make a count-up look", "write my carousel", "make it spin in").
If the `claude` command is installed, the studio starts you automatically for each one. Otherwise the
user will say **"check my studio requests"**. Either way:

1. `python3 -m engine requests [NAME]` — shows open requests with their id, kind and details.
2. Do the work (below).
3. Always finish with `python3 -m engine request-done NAME ID --note "<one friendly sentence>"`
   (add `--options a,b,c` for look options; `--failed` with a reason if you couldn't do it).
   The studio pings the user when you mark it done.

### kind: `look` — "Describe it to Claude"
The user described a graphic they want over words `w0`–`w1` (`words` = what they say there).
If `previous` is present, they've seen those options and `text` ends with the changes they want.

Make **three genuinely different** options as new files in `lookbook/looks/custom/`, named
`<slug>_1.py`, `<slug>_2.py`, `<slug>_3.py` (short slug from the request, lowercase, underscores).
Each file follows the look API — copy the shape of `lookbook/looks/count_up.py`:

```python
META = {"name": "Count-up — bold", "description": "One sentence the user sees when choosing",
        "params": {...every value the look uses, with the request's specifics baked in as defaults...}}

def render(ctx):   # called for every frame; return a PIL RGBA image of just the graphic
    # ctx.t = seconds since it appeared, ctx.dur = how long it shows, ctx.W/ctx.H = 1080x1920,
    # ctx.p = params, ctx.font("Montserrat_900Black", size), ctx.rgba("#hex"), ctx.emoji("1f525"),
    # ctx.ease(x), ctx.ease_back(x), ctx.wrap(text, font, max_width), ctx.Image / ImageDraw / ImageFilter
    ...
```

- Fonts available (in `assets/fonts/`): Montserrat_600SemiBold/700Bold/800ExtraBold/900Black (loud caps),
  NanumPenScript_400Regular (handwriting), CaveatBrush_400Regular, Kalam_700Bold, InstrumentSerif_400Regular
  (+ _Italic), PlayfairDisplay_400Regular_Italic/700Bold_Italic, Inter_700Bold/800ExtraBold, Poppins_800ExtraBold,
  BebasNeue_400Regular. Follow the user's style: one loud face + one human face, white text, one accent color.
  Helpers on `ctx`: `ctx.write(text, font, size, maxw, chars=…)` (typewriter text), `ctx.curve(...)` (drawn
  arrow), `ctx.card(w, h)` (white card with shadow), `ctx.shadowed(img)`, `ctx.stack([...])`, and the style's
  font/color names (`ctx.LOUD`, `ctx.HAND`, `ctx.CTA`, `ctx.HIGHLIGHT`, …). See `lookbook/looks/hand_note.py`.
- Bake the specifics into `META["params"]` defaults (numbers, labels, colors) — the studio adds the
  chosen option with empty params. Use the user's colors from `lookbook/STYLE.md` when known.
- Keep the returned image no bigger than needed (it's positioned and animated by the studio). Make it
  move (use `ctx.t`) — counting, wiping, bouncing — that's what makes it a "look".
- Check every option: `python3 -m engine look-preview <file_stem> --out projects/NAME/cache/<file_stem>.png`
  and look at the image. Fix anything clipped, unreadable or ugly before finishing.
- Finish with `--options <slug>_1,<slug>_2,<slug>_3`.

### kind: `edit` — "Ask Claude" / a note on an overlay
Free-form instruction, usually about words `w0`–`w1` (and maybe a specific `overlay` id). From the studio's
**Ask Claude** box there are no word indexes: use `text`, plus `at` (playhead time) and `playhead_line`
(the line the user was on) when they say "this line" or "here". If the request has `"default": true`, the user
wants this for **every reel**: do it here, and also add it as a short line under "Things I've told Claude" in
`lookbook/STYLE.md`. Find the words with `show NAME`. Make the change with
the CLI (`overlay`, `add-overlay`, `cut`, `highlight`, `set`…). If it needs a new kind of motion the
built-in animations can't do, write a custom look (as above) and swap the overlay to it. Explain what
you did in `--note`.

### kind: `carousel` / `story`
Write slides from what the user actually said (run `show NAME` first), in their voice, then render.
- Carousel: 5–8 slides. Slide 1 = the hook (short, bold). Middle = one idea per slide (`title` ≤ 6 words
  optional, `body` ≤ 140 characters). Last = a call to action (save / follow / comment a word).
  `set NAME carousel --json '{"slides":[{"title":"...","body":"..."}, ...]}'` then `export NAME carousel`.
- Story: 1–3 slides teasing the reel. `set NAME story --json '{"slides":[...]}'` then `export NAME story`.
- Slides use the saved frames (Finish → Save this frame) and photos the user picked. You can pin a slide
  to an image with `"image": "projects/NAME/frames/frame_02.jpg"`.

### kind: `trials` — trial reels
Write three repackaged versions of the same edit, each with a **different opening line, length and hook**,
all in the same look. Each spec can use:
`hook_text` (new hook title), `open_line` (a line id to move to the very start — a cold open),
`max_len` (seconds; trims lines from the back half), `drop_lines` ([line ids] to remove), `name`.
`set NAME trials --json '[{"name":"Cold open","open_line":7,"hook_text":"..."}, {...}, {...}]'`
then `export NAME trials` (renders 3 videos — takes a few minutes).

## Learning the user's style

`lookbook/STYLE.md` is your memory of their taste. When the user tells you a preference
("I never want emojis on faces", "my brand color is #E5484D", "hooks in all caps"), or keeps picking
the same kind of option, add a short line to it. Read it at the start of every edit.

## Rules

- Never delete or overwrite anything in `projects/*/raw/` or the user's `library/`.
- Edit `project.json` through the CLI commands above (they keep the studio in sync). If you must hand-edit
  it, keep it valid JSON and bump `"edit_rev"`.
- The studio is where the user decides. Show them, don't just tell them.
