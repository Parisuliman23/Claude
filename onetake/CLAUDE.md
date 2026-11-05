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
4. **First styling pass** — follow `lookbook/STYLE.md`:
   - Caption style: `set NAME caption_style --json '"bold-pop"'` (ids in `lookbook/captions.json`).
   - **Captions already in the video** (e.g. a CapCut export): the user wants *ours*, not theirs. The import
     detects them automatically ("found captions in N% of the video") and sets `burned_captions.remove`, which
     paints them out in the render, and moves our captions to the same height to cover any trace. Keep our
     captions ON. If the import didn't catch them (you see text in a `still`), run `remove-captions NAME`.
     Check a still before and after: the old text should be gone. (Studio: Visuals → "Video's own captions".)
     Check a still: captions must not cover the mouth or chin. Move them for this reel with
     `set NAME caption_y --json 0.82` (0 = top, 1 = bottom; stay above ~0.85 to clear Instagram's UI).
   - Hook: the import adds a hook title on the first line. Rewrite its text to a punchy ≤ 8-word hook:
     `overlay NAME <hook-id> --json '{"params": {"text": "..."}}'`.
   - Highlight 1–2 key words per sentence or two (numbers, money, emotional words): `highlight NAME A-B`.
   - Add a look where it clearly fits (e.g. a count-up card when they say a big number):
     `add-overlay NAME --json '{"kind":"look","look":"count_up","w0":120,"w1":131,"params":{"to":800,"label":"people in my community"}}'`.
     Media from the library: `{"kind":"gif","src":"library/gifs/x.gif",...}`, `{"kind":"image",...}`,
     `{"kind":"emoji","emoji":"1f525","scale":0.2}` (codes = files in `assets/emoji/`).
     Animations: `none pop fade slide-left slide-right slide-up slide-down spin zoom` (`anim_in`, `anim_out`).
     Position: `x`, `y` are 0–1 fractions of the frame; `scale` = width fraction (looks: 1 = natural size).
     `w0`/`w1` = the words it's shown over.
   - Sound: pick a track from `library/sounds/` that fits the energy:
     `set NAME sound --json '{"src":"library/sounds/<file>","volume":0.12,"offset":0}'`.
   - Keep it tasteful: a few strong moments beat constant stickers.
   - Check a moment visually any time: `still NAME <seconds>` → look at `projects/NAME/cache/still.png`.
5. **Open the studio** in the background: `python3 -m engine open NAME` and tell the user it's at
   http://localhost:5178. Give a 3–5 bullet summary of what you cut and styled, and remind them:
   they can bring back anything you cut, swap any look, and nothing renders until **Lock in my looks**.
6. Don't render the final reel yourself unless asked — that's the user's "lock in" moment.
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

- Fonts available (in `assets/fonts/`): Montserrat_600SemiBold, Montserrat_700Bold, Montserrat_800ExtraBold,
  Montserrat_900Black, PlayfairDisplay_400Regular_Italic, PlayfairDisplay_700Bold_Italic, BebasNeue_400Regular.
- Bake the specifics into `META["params"]` defaults (numbers, labels, colors) — the studio adds the
  chosen option with empty params. Use the user's colors from `lookbook/STYLE.md` when known.
- Keep the returned image no bigger than needed (it's positioned and animated by the studio). Make it
  move (use `ctx.t`) — counting, wiping, bouncing — that's what makes it a "look".
- Check every option: `python3 -m engine look-preview <file_stem> --out projects/NAME/cache/<file_stem>.png`
  and look at the image. Fix anything clipped, unreadable or ugly before finishing.
- Finish with `--options <slug>_1,<slug>_2,<slug>_3`.

### kind: `edit` — "Ask Claude" / a note on an overlay
Free-form instruction about words `w0`–`w1` (and maybe a specific `overlay` id). Make the change with
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
