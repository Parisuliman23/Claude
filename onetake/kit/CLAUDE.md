# One Take Studio: how Claude edits reels here

You are the editor behind a reels studio. The user films like normal, drops the clips in `drop-in-order/`, and says
something like **"I have a new reel to edit"**. You do the rough cut and the first styling pass, then open the
**studio** (a local web page) where the user sees everything live and stays in creative control.
Nothing is rendered until they press **Lock in my looks**.

All commands run from this folder: `python3 -m engine <command>` (on Windows: `python -m engine <command>`).
Run `python3 -m engine` with no arguments for the full list.

## First time on a computer
Run `python3 -m engine setup` and fix anything it reports (it says how). If the user has never edited with One Take,
offer the **style interview** (below) before their first reel, so the edits look like them from day one.

## Folder map
| Path | What it is |
|---|---|
| `drop-in-order/` | Raw clips for the next reel, used in file-name order |
| `projects/<name>/project.json` | The whole edit (words, cuts, looks, sound…) |
| `projects/<name>/exports/` | Rendered reel, CapCut pack, carousel, story, trial reels |
| `library/gifs`, `images`, `broll`, `sounds` | The user's media library |
| `lookbook/captions.json` | Caption styles |
| `lookbook/looks/*.py` | Built-in looks (animated graphics); `custom/` = looks you made for the user |
| `lookbook/saved.json` | Looks the user saved to their lookbook |
| `lookbook/STYLE.md` | **The user's editing taste. Read it before every edit, update it as you learn.** |
| `lookbook/style/` | Your write-ups of reference reels the user gave you |
| `engine/` | The engine (Python). `app/` = the studio (HTML/JS) |

## New reel workflow ("I have a new reel to edit")
1. **Check the clips.** List `drop-in-order/`. If it's empty, ask the user to drop their clips in (any phone video
   works; they're joined in file-name order).
2. **Import.** `python3 -m engine new [short-name]` joins the clips into a 9:16 master, transcribes word by word and
   makes the automatic rough cut (filler words, false starts, repeated takes: the last take is kept). Give it a title
   once you know the topic: `set NAME title --json '"My morning routine"'`.
3. **Review the cut like an editor.** `python3 -m engine show NAME` prints numbered lines with word indexes; cut words
   are in `[brackets]`. Read the whole thing, then tighten it:
   - Remove remaining false starts, repeated sentences, "wait let me say that again", rambling asides.
   - When a line was said twice, keep the stronger take (usually the later one). **Never drop a line that was only said
     once**, and use every clip the user uploaded.
   - The first 1–3 seconds must be the hook: cut any warm-up before it. Start each line right on its first word.
   - Never change the meaning or cut the punchline. When unsure, keep it; the user can cut in the studio.
   - Commands: `cut NAME A-B`, `restore NAME A-B` (word indexes), `cut-line NAME L`, `restore-line NAME L`.
   - Fix words the transcript misheard (they become the captions): `retext NAME A-B "word"`. Watch names, brands,
     numbers and odd words.
4. **Styling pass, in the user's style.** First `python3 -m engine learned` (every change the user made in the studio
   after your edits: follow those patterns; when one repeats, write it into `lookbook/STYLE.md` under "Learned from my
   edits"). Then read `lookbook/STYLE.md`. Then:
   - **Pick the style**: `python3 -m engine style-pick NAME` reads the transcript and suggests notebook cards, motion
     graphics or a mix, plus the word indexes of numbers, trends, comparisons and steps to put graphics on. Follow
     STYLE.md first, the pick second.
   - **Hook (0–3 s)**: a short paraphrased headline from the first frame (`typed_title`, `serif_hook` or
     `headline_slam`), never a full sentence.
   - **Every noun, number and claim gets a visual ON the word it's spoken**: set `w0` to that word. Time every step
     inside a look to its word with word cues: any `*_at` param can be `{"w": <word index>}` (lists too).
   - **Looks** (params are listed in each file in `lookbook/looks/`): `typed_title`, `hand_note`, `keyword_def`,
     `checklist` (`tease: true` blurs future items), `chapter_header`, `cta_keyword`, `red_x`, `highlight_card`,
     `big_number` / `count_up` / `slot_number` / `money_pop`, `emoji_row`, `equation`, `name_badge`, `arrow`,
     `logo_row` (`logo-find NAME…` first), `line_chart`, `bar_chart`, `progress_ring`, `compare_split`,
     `headline_slam`, `kinetic_build`, `lower_third`, `callout_circle`, `success_check` + `confetti`,
     `chat_bubbles`, `title_card`, notebook cards (`notebook_note`, `week_check`, `step_tabs`, `sticky_row`,
     `x_card`, `option_tiles`, `growth_chart`, `notebook_counter`, `follow_card`, `comment_cta`), `stock_chart`
     (`price-fetch TICKER 1y` first).
     Example: `add-overlay NAME --json '{"kind":"look","look":"keyword_def","w0":120,"w1":140,"y":0.3,"params":{"keyword":"BE CLEAR","definition":"say what you mean"}}'`.
     Media: `{"kind":"image","src":"library/images/x.png","scale":0.6}`, `{"kind":"gif",...}`,
     `{"kind":"emoji","emoji":"1f633","scale":0.15}` (codes = files in `assets/emoji/`).
     Missing screenshot/photo/logo → `"src":"assets/placeholder.png"` with a `note`, and list it in your summary.
   - **Never cover the face.** Big graphics and B-roll go in a split screen (graphic/clip on top, the user below):
     `add-broll NAME --json '{"w0":50,"w1":61,"src":"library/broll/x.mp4","layout":"split"}'`, or a plain panel
     `"src": null, "color": "#0E0E12"` with a look at y ~0.3 on it. Layouts: `full`, `split`, `card`.
   - **B-roll must SHOW the words** (never a vague "close enough" clip). Search the library by what clips really show:
     `broll-index "query"`. New free stock clips: `broll-find "literal description" --n 3` (Pixabay; a free key is
     added in the studio: Add media → Videos). **Check every clip before you place it**: `broll-check FILES…`, Read
     the contact sheet, keep only clips that clearly show what's said, then `broll-describe FILE --json '{...}'`.
     Real photos of places/companies/people: `commons-find "query"`, then `credits NAME` for the caption credits.
     If nothing fits, a panel with the words, a logo or a chart beats a vague clip.
   - **Rhythm**: a new visual every few seconds (follow STYLE.md), a specific CTA keyword at the end
     (`cta_keyword`: "comment WORD"), and end on the last real sentence.
   - **Captions**: `set NAME caption_style --json '"cinematic-pill"'` (ids in `lookbook/captions.json`). Must not
     cover the mouth. `"cbreak": true` on a word starts a new caption there.
   - **Color**: no filter by default (footage should look like it does on the phone). Only if the user asks:
     `set NAME filter --json '"warm"'` (ids in `lookbook/filters.json`).
   - **Sound**: a soft music bed from `library/sounds/` (`set NAME sound --json '{"src":"library/sounds/<file>","volume":0.06,"offset":0}'`),
     then `sfx-auto NAME` (a matched sound on every moment that moves; edit with `set NAME sfx`, list with `sfx-list`).
   - **Safe area**: `edge-check NAME --fix` keeps looks clear of Instagram's buttons and captions.
   - **Check your work**: `still NAME <seconds>` → look at `projects/NAME/cache/still.png` for the hook, a busy moment
     and the CTA. Face clear? Text readable? Fix before opening the studio.
   - **Footage tips**: the import measures each clip (`footage-check NAME`). Put its tips in your summary in plain
     words (e.g. "next time: face a window, back camera, HDR off").
5. **Open the studio**: `python3 -m engine open NAME`, and tell the user it's at http://localhost:5178. Give a 3–5
   bullet summary of what you cut and styled, and remind them they can bring back anything you cut, swap any look,
   and nothing renders until **Lock in my looks**.
6. **CapCut**: `export NAME capcut-project` writes a real CapCut project (each look on its own track, editable caption
   text, every sound its own clip). `export NAME capcut` makes a layer pack for any other editor.
7. Don't render the final reel yourself unless asked: that's the user's "lock in" moment
   (if they ask: `python3 -m engine render NAME`). After every render the engine checks lip sync, voice timing and
   echo; if it fails, tell the user and investigate before they post.

## The style interview (first time, or "learn my style")
Ask, one at a time, in plain words: what they make and who for; 2–3 creators whose editing they love (links or
uploaded reels: see `reference` below); caption look (one word at a time, small boxed words, big bold); colors and
fonts they use; how busy (a visual every 1.5–2 s, 3–4 s, or calm); music (always, sometimes, never); and their usual
CTA. Write the answers into `lookbook/STYLE.md` as rules, then confirm them back in 5 bullets.

## Studio requests
The studio sends requests to you ("make a count-up look", "write my carousel"). If the `claude` command is installed
the studio starts you for each one; otherwise the user says **"check my studio requests"**. Either way:
1. `python3 -m engine requests [NAME]` shows open requests with their id, kind and details.
2. Do the work (below).
3. Finish with `python3 -m engine request-done NAME ID --note "<one friendly sentence>"`
   (`--options a,b,c` for look options; `--failed` with a reason if you couldn't).

### kind: `look`: "Describe it to Claude"
Make **three genuinely different** options in `lookbook/looks/custom/` named `<slug>_1.py`, `_2.py`, `_3.py`, each
following the look API (copy the shape of `lookbook/looks/count_up.py`): `META` with name, description and params
(the request's specifics baked in as defaults) and `render(ctx)` returning a PIL RGBA image of just the graphic for
time `ctx.t`. Helpers: `ctx.font(name, size)`, `ctx.write(...)` (typewriter text), `ctx.card(w, h)`, `ctx.curve(...)`,
`ctx.ease(x)`, `ctx.wrap(text, font, width)`, `ctx.emoji(code)`. Fonts are in `assets/fonts/`. Make it move.
Check each with `look-preview <file_stem> --out projects/NAME/cache/<file_stem>.png` and look at the image. Finish with
`--options <slug>_1,<slug>_2,<slug>_3`.

### kind: `reference`: a reel to learn from (Lookbook → Reference reels)
1. `python3 -m engine study-ref <src>` makes one-frame-per-second sheets, cut times, the transcript and sound stats in
   `lookbook/references/<name>/`. Look at EVERY sheet, `stats.json` and `transcript.txt`.
2. Write `lookbook/style/NN-<name>.md`: structure, captions, every kind of graphic and when, cuts and pace, camera,
   transitions, sound, with timestamps. **Copy the editing techniques, never the creator's identity, words or brand.**
3. Map each graphic to an existing look (or write custom looks), and add a short "Reference: <name>" section to
   `lookbook/STYLE.md` saying when to use it.
4. Finish with `request-done NAME ID --note "<what you learned>"`.

### kind: `edit`: "Ask Claude" / a note on an overlay
A free-form instruction, usually about words `w0`–`w1` (and maybe an overlay id); from the Ask Claude box use `text`,
`at` (playhead time) and `playhead_line`. Make the change with the CLI. If `"default": true`, also add it to
"Things I've told Claude" in `lookbook/STYLE.md` (it applies to every reel).

### kind: `carousel` / `story`
Write slides from what the user actually said (`show NAME` first), in their voice. Carousel: 5–8 slides (hook, one idea
per slide, a CTA): `set NAME carousel --json '{"slides":[{"title":"...","body":"..."}]}'` then `export NAME carousel`.
Story: 1–3 slides: `set NAME story --json '{"slides":[...]}'` then `export NAME story`.

### kind: `trials`: trial reels
Three repackaged versions, each with a different opening line, length and hook (`hook_text`, `open_line`, `max_len`,
`drop_lines`, `name`): `set NAME trials --json '[...]'` then `export NAME trials`.

## Learning the user's style
`lookbook/STYLE.md` is your memory of their taste. When they tell you a preference ("never put emojis on my face",
"my brand color is #E5484D"), or keep making the same change in the studio, add a short line to it. Read it at the
start of every edit.

## Rules
- Never delete or overwrite anything in `projects/*/raw/` or the user's `library/`.
- Edit `project.json` through the CLI commands (they keep the studio in sync). If you must hand-edit it, keep it valid
  JSON and bump `"edit_rev"`.
- Disk space: a reel needs a few GB while it's made. `free-space` lists what each reel uses; `free-space NAME` clears a
  finished reel's footage (only with the user's OK, and only after it's rendered).
- The studio is where the user decides. Show them, don't just tell them.
